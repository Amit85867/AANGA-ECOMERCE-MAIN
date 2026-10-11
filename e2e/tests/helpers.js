import fs from 'node:fs'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, request } from '@playwright/test'

const here = path.dirname(fileURLToPath(import.meta.url))
export const authFile = (name) => path.join(here, '..', '.auth', `${name}.json`)
export const people = () => JSON.parse(fs.readFileSync(authFile('people'), 'utf8'))

/**
 * Watch a page for the things that must never happen on any screen: an
 * uncaught error, a console error, or the API answering with a server error.
 * Call `problems.check()` at the end of the test.
 *
 * `allow` lists URL fragments whose failures the test causes on purpose.
 */
export function watch(page, { allow = [] } = {}) {
  const found = []
  const allowed = (text) => allow.some((fragment) => text.includes(fragment))
  page.on('pageerror', (error) => found.push(`uncaught: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    const text = message.text()
    // A 401 from the session check of a signed-out visitor is expected, and
    // the browser logs every failed request as a console error.
    if (/status of 401/.test(text) || allowed(text) || allowed(message.location().url || '')) return
    found.push(`console: ${text}`)
  })
  page.on('response', (response) => {
    const url = response.url()
    if (url.includes('/api/') && response.status() >= 500 && !allowed(url)) found.push(`${response.status()} ${url}`)
  })
  return { found, check: () => expect(found, 'console errors / server errors').toEqual([]) }
}

/** The page must never scroll sideways, at any width. */
export async function noSidewaysScroll(page) {
  // Polled: a toast or a dialog sliding in is briefly off the edge of the screen.
  await expect.poll(
    () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
    { message: 'page is wider than the screen', timeout: 3000 },
  ).toBeLessThanOrEqual(1)
}

/** Product prices on the page, in order, as numbers. */
export async function cardPrices(page) {
  return page.locator('main a[href^="/product/"]').evaluateAll((cards) => cards.map((card) => {
    const match = card.innerText.match(/₹([\d,]+)/)
    return match ? Number(match[1].replace(/,/g, '')) : null
  }))
}

/**
 * An API client acting as one of the saved users (for setting a test up).
 * It uses the saved session rather than signing in again: sign-ins are rate
 * limited, and a test run would use the allowance up.
 */
export async function apiAs(baseURL, role) {
  const admin = ['owner', 'manager', 'staff'].includes(role)
  const context = await request.newContext({ baseURL, storageState: authFile(role) })
  const state = await context.storageState()
  const csrf = state.cookies.find((c) => c.name === (admin ? 'csrf_admin_refresh' : 'csrf_refresh_token'))?.value
  const response = await context.post(admin ? '/api/admin/auth/refresh' : '/api/auth/refresh', {
    headers: csrf ? { 'X-CSRF-TOKEN': decodeURIComponent(csrf) } : {},
  })
  if (!response.ok()) throw new Error(`apiAs(${role}) could not renew the session: ${response.status()}`)
  const token = (await response.json()).access_token
  const headers = { Authorization: `Bearer ${token}`, ...(admin ? { 'X-Demo-Content': '1' } : {}) }
  return {
    get: (url) => context.get(url, { headers }),
    post: (url, data) => context.post(url, { headers, data }),
    put: (url, data) => context.put(url, { headers, data }),
    patch: (url, data) => context.patch(url, { headers, data }),
    delete: (url) => context.delete(url, { headers }),
    dispose: () => context.dispose(),
  }
}

/**
 * Clear the rate-limit counters. The suite reloads the dashboard several
 * hundred times in a few minutes as one person, which is more than any admin
 * is allowed (300 session renewals an hour); the groups that do the most
 * reloading start from zero.
 */
export function resetLimits() {
  const root = path.resolve(here, '..', '..')
  const env = fs.readFileSync(path.join(root, '.prodlocal', 'env'), 'utf8')
  const password = env.split('\n').find((l) => l.startsWith('POSTGRES_PASSWORD='))?.slice('POSTGRES_PASSWORD='.length).trim()
  execSync('docker compose -f scripts/prod_local/docker-compose.yml exec -T redis redis-cli FLUSHALL', {
    cwd: root, stdio: 'ignore', env: { ...process.env, POSTGRES_PASSWORD: password },
  })
}

/** Is this the phone / tablet layout (menus behind a button)? */
export const isNarrow = (page) => (page.viewportSize()?.width || 0) < 1024

/** A name that is unique to this test run and this width. */
export const unique = (testInfo, base) => `${base} ${testInfo.project.name} ${Date.now().toString(36).slice(-4)}`
