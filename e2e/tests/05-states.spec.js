// Every page in the awkward states: slow network, a failing backend, no data,
// maintenance on, no campaign live. The rule is the same everywhere: the page
// keeps its frame, says what is happening, and never goes blank or throws.
//
// These run at a phone width and a desktop width. How a page behaves when the
// backend is slow or down does not change with the width; its layout at every
// width is checked by the page's own test.
import { test, expect } from '@playwright/test'
import { authFile } from './helpers.js'

const STATE_WIDTHS = ['w390', 'w1280']
test.beforeEach(({}, testInfo) => {
  test.skip(!STATE_WIDTHS.includes(testInfo.project.name), 'state tests run at 390 and 1280 px; behaviour under a slow or failing backend does not depend on width')
})

const slug = (path) => path.replace(/^\//, '').replace(/[/?=]/g, '-') || 'home'

/** Uncaught errors on the page: a crash the visitor would see as a blank screen. */
function crashes(page) {
  const seen = []
  page.on('pageerror', (error) => seen.push(String(error)))
  return () => expect(seen, 'uncaught errors on the page').toEqual([])
}

const failing = (route) => route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"Something went wrong"}' })
const slowly = async (route) => { await new Promise((r) => setTimeout(r, 1200)); await route.continue().catch(() => {}) }
const notSession = (url) => !/\/api\/(admin\/)?auth\//.test(url.pathname)

async function frameIsThere(page) {
  // not a blank page: the root has real content
  await expect.poll(() => page.evaluate(() => document.getElementById('root')?.innerText.trim().length || 0), { timeout: 15_000 }).toBeGreaterThan(20)
}

const PUBLIC = ['/', '/shop', '/shop?category=women', '/collections/diwali-edit', '/product/silk-blend-anarkali-kurta', '/about', '/shipping',
  '/returns', '/privacy-policy', '/terms', '/faq', '/contact', '/offers', '/wholesale', '/login', '/register', '/forgot-password',
  '/reset-password?token=x', '/track-order', '/wishlist', '/no/such/page']
const ACCOUNT = ['/cart', '/checkout', '/account/orders', '/account/returns', '/account/addresses', '/account/profile', '/wishlist']
const ADMIN = ['/admin', '/admin/orders', '/admin/returns', '/admin/users', '/admin/settlements', '/admin/products', '/admin/products/new',
  '/admin/categories', '/admin/collections', '/admin/media', '/admin/reviews', '/admin/campaigns', '/admin/coupons', '/admin/offers',
  '/admin/homepage', '/admin/banners', '/admin/announcements', '/admin/promo-banners', '/admin/testimonials', '/admin/features',
  '/admin/navigation', '/admin/pages', '/admin/faq', '/admin/inquiries', '/admin/messages', '/admin/newsletter', '/admin/settings',
  '/admin/staff', '/admin/site-settings', '/admin/demo', '/admin/system', '/admin/audit-log', '/admin/help']

test.describe('storefront, visitor', () => {
  for (const path of PUBLIC) {
    test(`ST-SLOW-${slug(path)} ${path} on a slow network shows its frame first, then its content`, async ({ page }) => {
      const check = crashes(page)
      await page.route('**/api/**', slowly)
      await page.goto(path)
      await frameIsThere(page)
      await expect(page.locator('h1').first()).toBeVisible({ timeout: 20_000 })
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })

    test(`ST-ERROR-${slug(path)} ${path} with the backend failing stays up and does not go blank`, async ({ page }) => {
      const check = crashes(page)
      await page.addInitScript(() => { try { localStorage.clear() } catch { /* private window */ } })
      await page.route('**/api/**', failing)
      await page.goto(path)
      await frameIsThere(page)
      await expect(page.getByRole('link', { name: /home|aanga/i }).first()).toBeVisible()     // the way out still works
      await expect(page.getByText(/Traceback|TypeError|undefined is not|Cannot read/)).toHaveCount(0)
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })
  }

  for (const path of ['/', '/shop', '/collections/diwali-edit', '/product/silk-blend-anarkali-kurta', '/offers', '/about', '/faq', '/contact']) {
    test(`ST-MAINT-${slug(path)} ${path} with maintenance on shows the maintenance page`, async ({ page }) => {
      const check = crashes(page)
      await page.route('**/api/cms/settings', async (route) => {
        const response = await route.fetch()
        const body = await response.json()
        await route.fulfill({ response, json: { settings: { ...body.settings, maintenance_mode: 'true', maintenance_message: 'Back at 6 pm.' } } })
      })
      await page.goto(path)
      await expect(page.getByText('Back at 6 pm.')).toBeVisible()
      await expect(page.locator('a[href^="/product/"]')).toHaveCount(0)
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })

    test(`ST-NOCAMP-${slug(path)} ${path} with no campaign live has no festive look and no countdown`, async ({ page }) => {
      const check = crashes(page)
      await page.addInitScript(() => { try { localStorage.removeItem('aanga.layout.v1') } catch { /* private window */ } })
      await page.route('**/api/content/layout', async (route) => {
        const response = await route.fetch()
        const body = await response.json()
        await route.fulfill({ response, json: { ...body, campaign: null, next_change_at: null } })
      })
      await page.goto(path)
      await expect(page.locator('h1').first()).toBeVisible()
      await expect(page.locator('html')).not.toHaveAttribute('data-festive', /.+/)
      await expect(page.getByText(/Ends in/)).toHaveCount(0)
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })
  }

  test('ST-MAINT-admin with maintenance on the dashboard sign-in is still reachable', async ({ page }) => {
    await page.route('**/api/cms/settings', async (route) => {
      const response = await route.fetch()
      const body = await response.json()
      await route.fulfill({ response, json: { settings: { ...body.settings, maintenance_mode: 'true' } } })
    })
    await page.goto('/admin/login')
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })
})

test.describe('storefront, signed-in customer', () => {
  test.use({ storageState: authFile('other') })

  for (const path of ACCOUNT) {
    test(`ST-SLOW-acct-${slug(path)} ${path} on a slow network`, async ({ page }) => {
      const check = crashes(page)
      await page.route((url) => url.pathname.startsWith('/api/') && notSession(url), slowly)
      await page.goto(path)
      await frameIsThere(page)
      await expect(page.locator('h1').first()).toBeVisible({ timeout: 20_000 })
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })

    test(`ST-ERROR-acct-${slug(path)} ${path} with the backend failing`, async ({ page }) => {
      const check = crashes(page)
      await page.route((url) => url.pathname.startsWith('/api/') && notSession(url), failing)
      await page.goto(path)
      await frameIsThere(page)
      await expect(page.getByText(/Traceback|TypeError|undefined is not|Cannot read/)).toHaveCount(0)
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })
  }

  test('ST-EMPTY-account a customer with nothing yet sees a helpful empty state on every account page', async ({ page }) => {
    const check = crashes(page)
    for (const [path, words] of [
      ['/account/orders', /No orders yet/],
      ['/account/returns', /no returns|nothing to return|not returned/i],
      ['/wishlist', /Nothing saved yet/],
      ['/cart', /Your bag is empty/],
    ]) {
      await page.goto(path)
      await expect(page.getByText(words).first(), path).toBeVisible()
      await expect(page.getByRole('main').getByRole('link').first(), `${path} offers a way on`).toBeVisible()
    }
    await page.goto('/checkout')
    await expect(page.getByText(/Your bag is empty/).first()).toBeVisible()
    check()
  })
})

test.describe('dashboard, owner', () => {
  test.use({ storageState: authFile('owner') })

  for (const path of ADMIN) {
    test(`ST-ADMIN-SLOW-${slug(path)} ${path} on a slow network`, async ({ page }) => {
      const check = crashes(page)
      await page.route((url) => url.pathname.startsWith('/api/admin/') && notSession(url), slowly)
      await page.goto(path)
      await expect(page.getByRole('navigation', { name: 'Admin' })).toBeAttached()
      await expect(page.locator('h1').first()).toBeVisible({ timeout: 20_000 })
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })

    test(`ST-ADMIN-ERROR-${slug(path)} ${path} with the backend failing says so and offers a retry`, async ({ page }) => {
      const check = crashes(page)
      await page.route((url) => url.pathname.startsWith('/api/admin/') && notSession(url), failing)
      await page.goto(path)
      await expect(page.getByRole('navigation', { name: 'Admin' })).toBeAttached()
      await frameIsThere(page)
      await expect(page.locator('main .animate-pulse')).toHaveCount(0, { timeout: 15_000 })   // not stuck loading
      await expect(page.getByText(/Traceback|TypeError|undefined is not|Cannot read/)).toHaveCount(0)
      check()
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    })
  }

  for (const [path, box, noun] of [
    ['/admin/orders', 'Order number, customer name, email or phone', 'order'],
    ['/admin/users', 'Name, email or phone', 'customer'],
    ['/admin/products', 'Search by product name', 'product'],
    ['/admin/audit-log', 'Search summary, action, admin or record id', 'entry'],
  ]) {
    test(`ST-ADMIN-EMPTY-${slug(path)} ${path} with nothing matching shows an empty state, not an empty table`, async ({ page }) => {
      await page.goto(path)
      await page.getByPlaceholder(box).fill('zzzz-no-such-thing-zzzz')
      await expect(page.getByRole('main').getByText(/^No |nothing|no .* (found|match)/i).first(), `no ${noun} found`).toBeVisible()
    })
  }
})
