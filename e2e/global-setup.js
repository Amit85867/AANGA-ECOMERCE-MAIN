// Runs once before the tests: signs each kind of user in and saves the
// browser state, so the tests themselves do not sign in over and over (the
// store limits sign-ins, and five admin sign-ins in fifteen minutes is the
// cap).
//
// Credentials come from backend/.env (the owner) and .e2e/demo_logins.json
// (the demo manager / staff / shopper, written by scripts/e2e.sh). Neither
// file is in this repository and nothing here is printed.
import fs from 'node:fs'
import path from 'node:path'
import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { request } from '@playwright/test'

const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, '..')
const authDir = path.join(here, '.auth')

function envFile() {
  const text = fs.readFileSync(path.join(root, 'backend', '.env'), 'utf8')
  return Object.fromEntries(text.split('\n').filter((l) => l && !l.startsWith('#') && l.includes('=')).map((l) => {
    const i = l.indexOf('=')
    return [l.slice(0, i), l.slice(i + 1).trim()]
  }))
}

async function signIn(baseURL, url, credentials, file) {
  const context = await request.newContext({ baseURL })
  const response = await context.post(url, { data: credentials })
  if (!response.ok()) throw new Error(`Sign-in to ${url} as ${credentials.email} answered ${response.status()}`)
  await context.storageState({ path: path.join(authDir, file) })
  const body = await response.json()
  await context.dispose()
  return body
}

export default async function globalSetup(config) {
  const baseURL = config.projects[0].use.baseURL
  if (!fs.existsSync(path.join(root, 'backend', '.env'))) {
    throw new Error('backend/.env is missing. See docs/DATABASE.md, then run scripts/e2e.sh')
  }
  if (!fs.existsSync(path.join(root, '.e2e', 'demo_logins.json'))) {
    throw new Error('Demo logins are missing. Run scripts/e2e.sh, which seeds them.')
  }
  fs.mkdirSync(authDir, { recursive: true })
  const env = envFile()
  const demo = JSON.parse(fs.readFileSync(path.join(root, '.e2e', 'demo_logins.json'), 'utf8'))

  // scripts/e2e.sh runs the API with RATELIMIT_ENABLED=false, so there are no
  // counters to clear. Kept as a call site for a run against an environment
  // that does limit (see resetLimits in tests/helpers.js).
  const flush = () => {
    const url = process.env.RATELIMIT_STORAGE_URI || ''
    if (!url.startsWith('redis')) return
    try { execSync(`redis-cli -u ${JSON.stringify(url)} FLUSHALL`, { stdio: 'ignore' }) } catch {}
  }
  flush()

  const owner = await signIn(baseURL, '/api/admin/auth/login', { email: env.ADMIN_EMAIL, password: env.ADMIN_PASSWORD }, 'owner.json')
  await signIn(baseURL, '/api/admin/auth/login', demo.manager, 'manager.json')
  await signIn(baseURL, '/api/admin/auth/login', demo.staff, 'staff.json')
  await signIn(baseURL, '/api/auth/login', demo.shopper, 'shopper.json')

  // Two more customers, new on every run: one to be blocked, and "someone
  // else" who must never see the shopper's data.
  const api = await request.newContext({ baseURL })
  const stamp = Date.now().toString(36)
  const people = {}
  for (const kind of ['other', 'blocked']) {
    const credentials = { email: `e2e.${kind}.${stamp}@example.com`, password: `E2e-${stamp}-${kind}-Pw1!` }
    const response = await api.post('/api/auth/register', { data: { full_name: `E2E ${kind}`, ...credentials } })
    if (!response.ok()) throw new Error(`Could not register the ${kind} customer: ${response.status()}`)
    people[kind] = { ...credentials, id: (await response.json()).user.id }
    await signIn(baseURL, '/api/auth/login', credentials, `${kind}.json`)
  }
  // One buyer per screen width and per test file that fills a bag: the widths
  // and the files run side by side, and a shared account would mean a shared
  // bag. ("buyer" is the customer file, "keys" the keyboard-only file, "desk"
  // the customer whose order the staff tests work on.)
  for (const project of config.projects) for (const prefix of ['buyer', 'keys', 'desk']) {
    const kind = `${prefix}-${project.name}`
    flush()          // registering and signing in are both rate limited per address
    const credentials = { email: `e2e.${kind}.${stamp}@example.com`, password: `E2e-${stamp}-${kind}-Pw1!` }
    const response = await api.post('/api/auth/register', { data: { full_name: `E2E Buyer ${project.name}`, ...credentials } })
    if (!response.ok()) throw new Error(`Could not register ${kind}: ${response.status()}`)
    const body = await response.json()
    people[kind] = { ...credentials, id: body.user.id }
    const address = await api.post('/api/addresses', {
      headers: { Authorization: `Bearer ${body.access_token}` },
      data: { label: 'Home', full_name: `E2E Buyer ${project.name}`, phone: '+919800000099', line1: '12 Test Lane', city: 'Patna', state: 'Bihar', pin_code: '800001', is_default: true },
    })
    if (!address.ok()) throw new Error(`Could not add an address for ${kind}: ${address.status()}`)
    await signIn(baseURL, '/api/auth/login', credentials, `${kind}.json`)
  }
  const admin = { Authorization: `Bearer ${owner.access_token}`, 'X-Demo-Content': '1' }
  // The tests buy these three products on every run; top their stock back up
  // so the suite can be run again and again against the same copy.
  for (const slug of ['oxford-button-down-shirt', 'double-breasted-wool-blazer', 'slim-chino-trousers']) {
    const product = await (await api.get(`/api/products/${slug}`)).json()
    for (const v of product.variants || []) {
      if (v.stock_qty >= 40) continue
      const topped = await api.put(`/api/admin/products/${product.id}/variants/${v.id}`, {
        headers: { Authorization: `Bearer ${owner.access_token}` },
        data: { size: v.size, color_name: v.color_name, color_hex: v.color_hex, sku: v.sku, stock_qty: 40 },
      })
      if (!topped.ok()) throw new Error(`Could not restock ${slug}: ${topped.status()}`)
    }
  }
  const blocked = await api.patch(`/api/admin/users/${people.blocked.id}`, { headers: admin, data: { is_active: false } })
  if (!blocked.ok()) throw new Error('Could not block the test customer')
  for (const kind of Object.keys(people)) {
    await api.post('/api/admin/demo/tag', { headers: admin, data: { kind: 'customers', ids: [people[kind].id], is_demo: true } })
  }
  await api.dispose()

  fs.writeFileSync(path.join(authDir, 'people.json'), JSON.stringify({
    owner: { email: env.ADMIN_EMAIL, password: env.ADMIN_PASSWORD },
    manager: demo.manager, staff: demo.staff, shopper: demo.shopper, ...people,
  }))

  // The sign-ins above used up most of the allowance; the tests that sign in
  // through the screens start from zero.
  flush()
}
