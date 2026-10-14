#!/usr/bin/env node
/**
 * Write sitemap.xml and robots.txt into the storefront build.
 *
 * The storefront is static on Hostinger and the API is on another host, so
 * https://<domain>/sitemap.xml has to be a real file in public_html. This
 * fetches the live catalogue from the API and writes both files into dist/.
 *
 *   SITE_URL=https://example.com API_BASE_URL=https://api.example.com \
 *     node scripts/generate_seo_files.mjs
 *
 * Run it after `vite build` (it writes into dist/), and again on a schedule so
 * new products appear without a code change.
 *
 * It will not invent an indexable site: the API decides whether indexing is on
 * (environment floor AND the owner's toggle), and when it is off this writes a
 * disallow-all robots.txt. If the API cannot be reached it also writes
 * disallow-all, because the alternative -- guessing "yes" -- risks indexing a
 * site that was deliberately closed.
 */
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const SITE_URL = (process.env.SITE_URL || '').replace(/\/+$/, '')
const API_BASE_URL = (process.env.API_BASE_URL || '').replace(/\/+$/, '')
const OUT_DIR = process.env.OUT_DIR || path.join(process.cwd(), 'frontend', 'dist')

if (!SITE_URL) {
  console.error('SITE_URL is required, e.g. https://example.com')
  process.exit(2)
}

const api = (p) => `${API_BASE_URL || SITE_URL}/api${p}`

// Routes that exist regardless of the catalogue. Checkout, cart, account and
// admin are deliberately absent: they are private or transient.
const STATIC_ROUTES = [
  ['/', 1.0, 'daily'],
  ['/shop', 0.9, 'daily'],
  ['/offers', 0.7, 'daily'],
  ['/about', 0.5, 'monthly'],
  ['/contact', 0.5, 'monthly'],
  ['/faq', 0.5, 'monthly'],
  ['/wholesale', 0.5, 'monthly'],
  ['/returns', 0.3, 'yearly'],
  ['/privacy', 0.3, 'yearly'],
  ['/terms', 0.3, 'yearly'],
]

const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;')

async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.json()
}

async function indexingEnabled() {
  const { settings } = await getJson(api('/cms/settings'))
  return settings?.seo_indexing_effective === 'true'
}

async function allProducts() {
  const out = []
  for (let page = 1; page <= 50; page += 1) {
    const data = await getJson(api(`/products?per_page=100&page=${page}`))
    const items = data.products || []
    out.push(...items)
    if (page >= (data.pages || 1) || items.length === 0) break
  }
  return out
}

async function allCategories() {
  const data = await getJson(api('/categories'))
  const flat = []
  const walk = (nodes) =>
    (nodes || []).forEach((c) => {
      flat.push(c)
      walk(c.children)
    })
  walk(data.categories || data)
  return flat
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true })

  let allowed = false
  let products = []
  let categories = []
  let reachable = true
  try {
    allowed = await indexingEnabled()
    ;[products, categories] = await Promise.all([allProducts(), allCategories()])
  } catch (err) {
    reachable = false
    console.error(`API not reachable (${err.message}); writing a closed robots.txt.`)
  }

  const urls = [
    ...STATIC_ROUTES.map(([loc, priority, changefreq]) => ({ loc, priority, changefreq })),
    ...categories.map((c) => ({
      loc: `/shop?category=${encodeURIComponent(c.slug)}`,
      priority: 0.7,
      changefreq: 'weekly',
    })),
    ...products.map((p) => ({
      loc: `/product/${p.slug}`,
      priority: 0.8,
      changefreq: 'weekly',
      lastmod: p.updated_at || p.created_at,
    })),
  ]

  const body = urls
    .map(({ loc, priority, changefreq, lastmod }) => {
      const when = lastmod ? `\n    <lastmod>${String(lastmod).slice(0, 10)}</lastmod>` : ''
      return `  <url>\n    <loc>${esc(SITE_URL + loc)}</loc>${when}\n` +
        `    <changefreq>${changefreq}</changefreq>\n    <priority>${priority}</priority>\n  </url>`
    })
    .join('\n')

  const sitemap =
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    `${body}\n</urlset>\n`
  await writeFile(path.join(OUT_DIR, 'sitemap.xml'), sitemap, 'utf8')

  const robots = allowed
    ? [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin',
        'Disallow: /account',
        'Disallow: /checkout',
        'Disallow: /cart',
        '',
        `Sitemap: ${SITE_URL}/sitemap.xml`,
        '',
      ].join('\n')
    : [
        '# Indexing is switched off for this site.',
        reachable
          ? '# Turn it on with INDEXING=true on the API and the toggle in Admin -> Store settings.'
          : '# The API could not be reached when this was generated, so indexing is closed by default.',
        'User-agent: *',
        'Disallow: /',
        '',
      ].join('\n')
  await writeFile(path.join(OUT_DIR, 'robots.txt'), robots, 'utf8')

  console.log(`sitemap.xml : ${urls.length} URLs (${products.length} products, ${categories.length} categories)`)
  console.log(`robots.txt  : ${allowed ? 'INDEXING ON — crawling allowed' : 'INDEXING OFF — disallow all'}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
