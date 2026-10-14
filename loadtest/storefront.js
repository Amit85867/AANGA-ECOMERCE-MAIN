// k6 load test for the AANGA storefront API. Staging only — see docs/LOAD_TEST.md.
//
//   k6 run -e BASE_URL=https://staging.example.com -e TARGET_ENV=staging loadtest/storefront.js
//
// What it does
//   browse  anonymous visitors: home page data, product listing with filters,
//           product pages with reviews. This is nearly all real traffic.
//   cart    (optional) signed-in shoppers reading the cart and adding / changing /
//           removing a line. Needs LOADTEST_EMAIL and LOADTEST_PASSWORD.
//
// What it deliberately never does
//   place an order, call /api/payments/*, call /api/shipping/serviceability
//   (that one reaches Shiprocket), register accounts, or touch /api/admin/*.
//   Nothing it does costs money, sends email or leaves an order behind.
import http from 'k6/http'
import { check, fail, group, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const BASE_URL = (__ENV.BASE_URL || '').replace(/\/+$/, '')
const PROFILE = __ENV.PROFILE || 'smoke'
const EMAIL = __ENV.LOADTEST_EMAIL || ''
const PASSWORD = __ENV.LOADTEST_PASSWORD || ''

// VUs are concurrent visitors, each pausing 1-4 s between pages like a person.
// 50 VUs is roughly 15-20 API requests a second.
const PROFILES = {
  // Does it work at all? One visitor, one minute.
  smoke: { browse: [['30s', 1], ['30s', 1]], cart: 1 },
  // A busy day. Hold long enough for memory and the connection pool to settle.
  load: { browse: [['2m', 50], ['5m', 50], ['1m', 0]], cart: 5 },
  // Find the knee: keep climbing until latency or errors give way.
  stress: { browse: [['2m', 50], ['2m', 100], ['2m', 200], ['2m', 300], ['1m', 0]], cart: 10 },
  // A sale announcement: nothing, then everyone at once.
  spike: { browse: [['20s', 10], ['10s', 250], ['2m', 250], ['30s', 10], ['1m', 10]], cart: 5 },
}
const profile = PROFILES[PROFILE] || fail(`Unknown PROFILE "${PROFILE}". Use: ${Object.keys(PROFILES).join(', ')}`)

const scenarios = {
  browse: {
    executor: 'ramping-vus',
    exec: 'browse',
    startVUs: 0,
    stages: profile.browse.map(([duration, target]) => ({ duration, target })),
    gracefulRampDown: '15s',
  },
}
if (EMAIL && PASSWORD) {
  scenarios.cart = {
    executor: 'constant-vus',
    exec: 'cart',
    vus: profile.cart,
    // An access token lasts 15 minutes and the test signs in once, so the
    // cart scenario always ends before that.
    duration: '8m',
    startTime: '30s',
  }
}

const rateLimited = new Rate('rate_limited')
const pageTime = new Trend('page_data_time', true)

export const options = {
  scenarios,
  thresholds: {
    // Pass / fail. Stress and spike are expected to break these — the point
    // there is to see where.
    http_req_failed: ['rate<0.01'],
    'http_req_duration{kind:catalogue}': ['p(95)<800', 'p(99)<2000'],
    'http_req_duration{kind:cms}': ['p(95)<500'],
    'http_req_duration{kind:cart}': ['p(95)<1000'],
    page_data_time: ['p(95)<2500'],
    // A 429 on these routes means the limiter is misconfigured for real
    // traffic (or the test is hitting something it should not).
    rate_limited: ['rate<0.001'],
    checks: ['rate>0.99'],
  },
  // 429 is counted separately above rather than as a generic failure.
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  userAgent: 'aanga-k6-loadtest',
}

const pick = (list) => list[Math.floor(Math.random() * list.length)]
const think = () => sleep(1 + Math.random() * 3)

function get(path, kind, params = {}) {
  const res = http.get(`${BASE_URL}${path}`, { ...params, tags: { kind, ...(params.tags || {}) } })
  rateLimited.add(res.status === 429)
  check(res, { [`${kind} 200`]: (r) => r.status === 200 })
  return res
}

// ── Setup: refuse anything that is not clearly a staging run ──

export function setup() {
  if (!BASE_URL) fail('Set BASE_URL, e.g. -e BASE_URL=https://staging.example.com')
  if (__ENV.TARGET_ENV !== 'staging') {
    fail('This test is for the staging environment. Pass -e TARGET_ENV=staging to confirm that is where BASE_URL points.')
  }
  if (/localhost|127\.0\.0\.1/.test(BASE_URL) && __ENV.ALLOW_LOCAL !== 'yes') {
    fail('A laptop is not a useful target: the numbers say nothing about Render. (-e ALLOW_LOCAL=yes only to debug the script.)')
  }

  const health = http.get(`${BASE_URL}/api/health`)
  if (health.status !== 200) fail(`${BASE_URL}/api/health answered ${health.status}; not starting.`)

  // Real slugs and categories from the target, so every request is one a
  // visitor could make.
  const listing = http.get(`${BASE_URL}/api/products?per_page=48&sort=newest&page=1`).json()
  const products = (listing.products || []).map((p) => ({ slug: p.slug, id: p.id }))
  if (products.length === 0) fail('The catalogue is empty. Seed staging first (backend/db/seed_catalogue.py).')
  const tree = http.get(`${BASE_URL}/api/categories`).json()
  const categories = []
  const walk = (nodes) => (nodes || []).forEach((c) => { categories.push(c.slug); walk(c.children) })
  walk(tree.categories || tree)

  let token = null
  let variants = []
  if (EMAIL && PASSWORD) {
    // One sign-in for the whole run: sign-in is limited to 10 per 15 minutes
    // per address, so signing in per virtual user would only test the limiter.
    const login = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({ email: EMAIL, password: PASSWORD }), {
      headers: { 'Content-Type': 'application/json' },
    })
    if (login.status !== 200) fail(`Sign-in as ${EMAIL} answered ${login.status}. Create the account on staging first.`)
    token = login.json('access_token')
    for (const p of products.slice(0, 5)) {
      const detail = http.get(`${BASE_URL}/api/products/${p.slug}`).json()
      variants = variants.concat((detail.variants || []).filter((v) => v.stock_qty > 5).map((v) => v.id))
    }
    if (variants.length === 0) fail('No variant with stock to put in the cart.')
  }

  return { products, categories, pages: Math.max(1, Math.min(listing.pages || 1, 4)), token, variants }
}

// ── Scenario: anonymous browsing ──

export function browse(data) {
  group('home', () => {
    const started = Date.now()
    // What the home page asks for on load, in parallel as a browser would.
    const responses = http.batch([
      ['GET', `${BASE_URL}/api/cms/banners`, null, { tags: { kind: 'cms' } }],
      ['GET', `${BASE_URL}/api/cms/announcements`, null, { tags: { kind: 'cms' } }],
      ['GET', `${BASE_URL}/api/cms/settings`, null, { tags: { kind: 'cms' } }],
      ['GET', `${BASE_URL}/api/cms/features`, null, { tags: { kind: 'cms' } }],
      ['GET', `${BASE_URL}/api/cms/promo-banners`, null, { tags: { kind: 'cms' } }],
      ['GET', `${BASE_URL}/api/cms/testimonials`, null, { tags: { kind: 'cms' } }],
      ['GET', `${BASE_URL}/api/categories`, null, { tags: { kind: 'catalogue' } }],
      ['GET', `${BASE_URL}/api/products?per_page=8&featured=true`, null, { tags: { kind: 'catalogue' } }],
    ])
    responses.forEach((r) => {
      rateLimited.add(r.status === 429)
      check(r, { 'home 200': (res) => res.status === 200 })
    })
    pageTime.add(Date.now() - started, { page: 'home' })
  })
  think()

  group('listing', () => {
    const started = Date.now()
    get('/api/products/facets', 'catalogue')
    // Mostly the default listing (cached), sometimes a filter, sort or search
    // that has to be computed.
    const roll = Math.random()
    let query = `per_page=12&sort=newest&page=${1 + Math.floor(Math.random() * data.pages)}`
    if (roll > 0.85) query = `per_page=12&q=${pick(['shirt', 'jeans', 'dress', 'shoes', 'kurta'])}`
    else if (roll > 0.7) query = `per_page=12&sort=${pick(['price_asc', 'price_desc'])}&in_stock=true`
    else if (roll > 0.4 && data.categories.length) query = `per_page=12&category=${pick(data.categories)}`
    get(`/api/products?${query}`, 'catalogue')
    pageTime.add(Date.now() - started, { page: 'listing' })
  })
  think()

  // Two or three product pages per visit.
  const views = 2 + Math.floor(Math.random() * 2)
  for (let i = 0; i < views; i++) {
    group('product', () => {
      const started = Date.now()
      const product = pick(data.products)
      get(`/api/products/${product.slug}`, 'catalogue', { tags: { name: '/api/products/:slug' } })
      get(`/api/reviews/product/${product.id}?page=1&per_page=5`, 'catalogue', { tags: { name: '/api/reviews/product/:id' } })
      pageTime.add(Date.now() - started, { page: 'product' })
    })
    think()
  }
}

// ── Scenario: signed-in cart (optional) ──

export function cart(data) {
  const headers = { Authorization: `Bearer ${data.token}`, 'Content-Type': 'application/json' }
  const tagged = (name) => ({ headers, tags: { kind: 'cart', name } })

  group('cart', () => {
    const view = http.get(`${BASE_URL}/api/cart`, tagged('GET /api/cart'))
    check(view, { 'cart 200': (r) => r.status === 200 })
    think()

    // Every virtual user shares one account, so they share one cart. Lines
    // are added and removed by id and a missing line (another user removed
    // it first) is a normal outcome here, not a failure.
    const added = http.post(
      `${BASE_URL}/api/cart/items`,
      JSON.stringify({ variant_id: pick(data.variants), quantity: 1 }),
      // 409 = "insufficient stock": the shared line reached the stock or the
      // per-line maximum. The server answering correctly, not a failure.
      { ...tagged('POST /api/cart/items'), responseCallback: http.expectedStatuses(200, 201, 409) },
    )
    rateLimited.add(added.status === 429)
    check(added, { 'add to cart ok': (r) => [200, 201, 409].includes(r.status) })
    think()

    const items = (http.get(`${BASE_URL}/api/cart`, tagged('GET /api/cart')).json('items')) || []
    if (items.length) {
      const line = pick(items)
      const removed = http.del(`${BASE_URL}/api/cart/items/${line.id}`, null, {
        ...tagged('DELETE /api/cart/items/:id'),
        responseCallback: http.expectedStatuses(200, 204, 404),
      })
      check(removed, { 'remove line ok': (r) => [200, 204, 404].includes(r.status) })
    }
  })
  think()
}

// ── Teardown: leave the test account's cart empty ──

export function teardown(data) {
  if (!data.token) return
  const headers = { Authorization: `Bearer ${data.token}` }
  const items = (http.get(`${BASE_URL}/api/cart`, { headers }).json('items')) || []
  items.forEach((line) => http.del(`${BASE_URL}/api/cart/items/${line.id}`, null, {
    headers, responseCallback: http.expectedStatuses(200, 204, 404),
  }))
}
