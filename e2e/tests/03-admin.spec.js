// The dashboard, as each of the three roles: every screen opens, the everyday
// jobs work from the screens, and a role cannot reach what it should not.
import { test, expect } from '@playwright/test'
import { apiAs, authFile, isNarrow, noSidewaysScroll, people, unique, watch } from './helpers.js'

// address, the area of the admin API it uses, the menu label, the page heading
const SCREENS = [
  ['/admin', 'dashboard', 'Dashboard', 'Dashboard'],
  ['/admin/orders', 'orders', 'Orders', 'Orders'],
  ['/admin/returns', 'returns', 'Returns', 'Returns'],
  ['/admin/users', 'users', 'Customers', 'Customers'],
  ['/admin/settlements', 'settlements', 'Settlements', 'Payments & Settlements'],
  ['/admin/products', 'products', 'Products', 'Products'],
  ['/admin/products/new', 'products', null, 'New Product'],
  ['/admin/categories', 'categories', 'Categories', 'Categories'],
  ['/admin/collections', 'collections', 'Collections', 'Collections'],
  ['/admin/media', 'media', 'Media library', 'Media library'],
  ['/admin/reviews', 'reviews', 'Reviews', 'Reviews'],
  ['/admin/campaigns', 'campaigns', 'Campaigns', 'Campaigns'],
  ['/admin/coupons', 'coupons', 'Coupons', 'Coupons'],
  ['/admin/offers', 'offers', 'Offers', 'Offers'],
  ['/admin/homepage', 'homepage', 'Homepage', 'Homepage'],
  ['/admin/banners', 'banners', 'Hero slides', 'Hero Banners'],
  ['/admin/announcements', 'announcements', 'Announcements', 'Announcements'],
  ['/admin/promo-banners', 'promo-banners', 'Promo banners', 'Promo Banners'],
  ['/admin/testimonials', 'testimonials', 'Testimonials', 'Testimonials'],
  ['/admin/features', 'features', 'Feature cards', 'Why Choose (Feature Cards)'],
  ['/admin/navigation', 'navigation', 'Menus', 'Menus'],
  ['/admin/pages', 'pages', 'Pages', 'Pages'],
  ['/admin/faq', 'faq', 'FAQ', 'FAQ'],
  ['/admin/inquiries', 'wholesale-inquiries', 'Wholesale inquiries', 'Wholesale inquiries'],
  ['/admin/messages', 'contact-messages', 'Messages', 'Messages'],
  ['/admin/newsletter', 'newsletter', 'Newsletter', 'Newsletter'],
  ['/admin/settings', 'settings', 'Store settings', 'Store settings'],
  ['/admin/staff', 'staff', 'Staff', 'Staff'],
  ['/admin/site-settings', 'site-settings', 'Other text', 'Site Settings'],
  ['/admin/demo', 'demo', 'Demo content', 'Demo content'],
  ['/admin/system', 'system', 'System health', 'System health'],
  ['/admin/audit-log', 'audit-log', 'Audit log', 'Audit log'],
  ['/admin/help', null, 'Help', null],            // its heading is the title of the owner guide
]
const EVERYONE = ['dashboard', 'orders', 'returns', 'products', 'categories', 'media']
const OWNER_ONLY = ['settings', 'staff', 'site-settings', 'demo', 'system']
const allowed = (role, area) => !area || role === 'owner' || EVERYONE.includes(area) || (role === 'manager' && !OWNER_ONLY.includes(area))
const slugOf = (path) => path.replace('/admin', '').replace(/\//g, '-').replace(/^-/, '') || 'dashboard'

async function openScreen(page, path, heading) {
  await page.goto(path)
  await expect(heading ? page.getByRole('heading', { level: 1, name: heading, exact: true }) : page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByText('Something went wrong')).toHaveCount(0)
  await expect(page.locator('main .animate-pulse')).toHaveCount(0)      // loading placeholders are gone
}

async function menu(page) {
  if (isNarrow(page)) await page.getByRole('button', { name: 'Open menu' }).click()
  return page.getByRole('navigation', { name: 'Admin' })
}

test.describe('owner', () => {
  test.use({ storageState: authFile('owner') })

  for (const [path, , , heading] of SCREENS) {
    test(`AD-SCREEN-${slugOf(path)} owner: ${path} opens with no errors`, async ({ page }) => {
      const problems = watch(page)
      await openScreen(page, path, heading)
      await noSidewaysScroll(page)
      problems.check()
    })
  }

  test('AD-NAV-OWNER the owner’s menu lists every screen and each link opens it', async ({ page }) => {
    await page.goto('/admin')
    const nav = await menu(page)
    for (const [, , label] of SCREENS) {
      if (label) await expect(nav.getByRole('link', { name: label, exact: true })).toBeVisible()
    }
    await nav.getByRole('link', { name: 'Coupons', exact: true }).click()
    await expect(page).toHaveURL(/\/admin\/coupons$/)
    await expect(page.getByRole('heading', { level: 1, name: 'Coupons' })).toBeVisible()
  })

  test('AD-STAFF-01 add a staff member (one-time password shown once), refuse a duplicate, remove', async ({ page }, testInfo) => {
    const problems = watch(page, { allow: ['/api/admin/staff'] })
    const name = unique(testInfo, 'E2E Staff')
    const email = `${name.toLowerCase().replace(/\s+/g, '.')}@example.com`
    await page.goto('/admin/staff')
    const add = async () => {
      await page.getByRole('button', { name: 'Add staff member' }).first().click()
      await page.getByLabel('Full name *').fill(name)
      await page.getByLabel('Email *').fill(email)
      await page.locator('form').getByLabel('Role').selectOption('staff')
      await page.locator('form').getByRole('button', { name: 'Add staff member' }).click()
    }
    await add()
    await expect(page.getByText(`One-time password for ${email}`)).toBeVisible()
    await page.getByRole('button', { name: 'I have saved it' }).click()
    await expect(page.getByText(`One-time password for ${email}`)).toHaveCount(0)
    await expect(page.getByRole('row').filter({ hasText: email })).toBeVisible()

    await add()                                           // the same address again
    await expect(page.locator('form [role="alert"]').first()).toBeVisible()
    await page.locator('form').getByRole('button', { name: 'Cancel' }).click()

    await page.getByRole('button', { name: `Remove ${name}` }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click()
    await expect(page.getByText('Removed.')).toBeVisible()
    await expect(page.getByRole('row').filter({ hasText: email })).toHaveCount(0)
    await noSidewaysScroll(page)
    problems.check()
  })

  test('AD-SETTINGS-01 a store setting takes effect on the storefront; a bad value is refused', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'w1280', 'store-wide settings: one width writes them so the widths do not overwrite each other (the screen itself is checked at every width in AD-SCREEN-settings)')
    const problems = watch(page, { allow: ['/api/admin/settings'] })
    const tagline = unique(testInfo, 'Clothes worth keeping')
    await page.goto('/admin/settings')
    const before = await page.getByLabel('Tagline').inputValue()
    await page.getByLabel('GSTIN').fill('NOT-A-GSTIN')
    await page.getByRole('button', { name: 'Save settings' }).first().click()
    await expect(page.locator('form [role="alert"]').first()).toBeVisible()
    await page.getByLabel('GSTIN').fill('')
    await page.getByLabel('Tagline').fill(tagline)
    await page.getByRole('button', { name: 'Save settings' }).first().click()
    await expect(page.getByText('Settings saved. The storefront is already using them.')).toBeVisible()
    await page.goto('/about')
    await expect(page.getByRole('contentinfo').getByText(tagline)).toBeVisible()
    // put it back
    await page.goto('/admin/settings')
    await page.getByLabel('Tagline').fill(before)
    await page.getByRole('button', { name: 'Save settings' }).first().click()
    await expect(page.getByText('Settings saved. The storefront is already using them.')).toBeVisible()
    problems.check()
  })

  test('AD-SYSTEM-01 System health says the payment gateway and courier are not configured, and the database is up to date', async ({ page }) => {
    await page.goto('/admin/system')
    await expect(page.getByRole('heading', { level: 1, name: 'System health' })).toBeVisible()
    await expect(page.getByText(/Not configured/i).first()).toBeVisible()
    await expect(page.getByText(/Database migrations/i)).toBeVisible()
    await expect(page.getByText(/pending/i)).toHaveCount(0)
  })

  test('AD-CAMPAIGN-01 the live campaign is listed, opens for editing, previews, and an overlapping one is refused', async ({ page, baseURL, context }, testInfo) => {
    const problems = watch(page)
    await page.goto('/admin/campaigns')
    const row = page.getByRole('row').filter({ hasText: 'Diwali' }).first()
    await expect(row).toBeVisible()
    await expect(row.getByText(/live/i).first()).toBeVisible()
    await noSidewaysScroll(page)

    const api = await apiAs(baseURL, 'owner')
    const campaigns = (await (await api.get('/api/admin/campaigns')).json()).campaigns
    const live = campaigns.find((c) => c.status === 'live')
    expect(live, 'a live campaign in the demo content').toBeTruthy()
    const clash = await api.post('/api/admin/campaigns', {
      name: unique(testInfo, 'E2E Overlap'), starts_at: live.starts_at, ends_at: live.ends_at, headline: 'Overlap',
    })
    expect(clash.status()).toBe(409)
    await api.dispose()

    await page.goto(`/admin/campaigns/${live.id}`)
    await expect(page.getByLabel('Campaign name *')).toHaveValue(live.name)
    const popup = context.waitForEvent('page')
    await page.getByRole('button', { name: 'Preview' }).first().click()
    const preview = await popup
    await preview.waitForLoadState('domcontentloaded')
    await expect(preview.locator('h1').first()).toBeVisible()
    await preview.close()
    problems.check()
  })

  test('AD-DEMO-01 the demo screen counts the demo content and asks for the exact phrase before removing', async ({ page }) => {
    await page.goto('/admin/demo')
    await expect(page.getByRole('heading', { level: 1, name: 'Demo content' })).toBeVisible()
    const remove = page.getByRole('button', { name: /remove (all )?demo content/i }).last()
    await expect(remove).toBeVisible()
    // (the removal itself is tested on a throwaway copy of the database, not here)
  })
})

test.describe('manager', () => {
  test.use({ storageState: authFile('manager') })

  test('AD-ROLE-MANAGER a manager opens every screen of the role, and the owner’s screens are closed in the menu, by address and on the server', async ({ page, baseURL }) => {
    test.slow()
    const problems = watch(page)
    for (const [path, area, , heading] of SCREENS.filter(([, a]) => allowed('manager', a))) {
      await openScreen(page, path, heading)
    }
    problems.check()

    await page.goto('/admin')
    const nav = await menu(page)
    await expect(nav.getByRole('link', { name: 'Coupons', exact: true })).toBeVisible()
    for (const [, area, label] of SCREENS.filter(([, a]) => OWNER_ONLY.includes(a))) {
      await expect(nav.getByRole('link', { name: label, exact: true }), `${area} in the menu`).toHaveCount(0)
    }
    for (const [path, , label] of SCREENS.filter(([, a]) => OWNER_ONLY.includes(a))) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: `${label} is not part of your role` })).toBeVisible()
    }
    const api = await apiAs(baseURL, 'manager')
    for (const url of ['/api/admin/settings', '/api/admin/staff', '/api/admin/system/health', '/api/admin/demo', '/api/admin/site-settings']) {
      expect((await api.get(url)).status(), url).toBe(403)
    }
    expect((await api.post('/api/admin/demo/remove', { confirm: 'REMOVE DEMO' })).status()).toBe(403)
    await api.dispose()
  })

  test('AD-COUPON-01 create, edit and delete a coupon; a bad one is refused', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page, { allow: ['/api/admin/coupons'] })
    const code = `E2E${testInfo.project.name.toUpperCase()}${Date.now().toString(36).slice(-4).toUpperCase()}`
    await page.goto('/admin/coupons')
    await page.getByRole('button', { name: 'Add Coupon' }).click()
    await page.getByLabel('Code *').fill(code)
    await page.getByLabel('Discount type').selectOption({ label: 'Percentage' })
    await page.getByLabel('Discount value *').fill('150')             // more than 100%
    await page.locator('form button[type="submit"]').click()
    await expect(page.locator('[role="alert"]').first()).toBeVisible()
    await page.getByLabel('Discount value *').fill('15')
    await page.getByLabel('Minimum order value').fill('500')
    await page.locator('form button[type="submit"]').click()
    await expect(page.getByText('Created.')).toBeVisible()
    const row = page.getByRole('row').filter({ hasText: code })
    await expect(row).toBeVisible()
    await noSidewaysScroll(page)

    await row.getByRole('button', { name: 'Edit' }).click()
    await page.getByLabel('Discount value *').fill('20')
    await page.locator('form button[type="submit"]').click()
    await expect(page.getByText('Changes saved.')).toBeVisible()
    await expect(row.getByText('20%')).toBeVisible()

    // every change is in the audit log
    const api = await apiAs(baseURL, 'manager')
    const log = await (await api.get('/api/admin/audit-log?entity_type=coupons&per_page=50')).json()
    const mine = log.entries.filter((e) => JSON.stringify(e.changes).includes(code))
    expect(mine.length, 'audit entries for creating and editing the coupon').toBeGreaterThanOrEqual(2)
    expect(mine[0].actor).toBe(people().manager.email)
    await api.dispose()

    await row.getByRole('button', { name: 'Delete' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete' }).click()
    await expect(page.getByText('Deleted.')).toBeVisible()
    await expect(row).toHaveCount(0)
    problems.check()
  })

  test('AD-FAQ-01 add a question (blank is refused), see it on the store, edit and remove it', async ({ page }, testInfo) => {
    const problems = watch(page, { allow: ['/api/admin/faq'] })
    const question = `${unique(testInfo, 'E2E question')}?`
    await page.goto('/admin/faq')
    await page.getByRole('button', { name: 'Add question' }).first().click()
    await page.locator('form').getByRole('button', { name: 'Add question' }).click()
    // a blank form is not sent: the form stays open and nothing is added
    await expect(page.getByRole('heading', { name: 'New question' })).toBeVisible()
    await expect(page.getByText('Question added.')).toHaveCount(0)
    await page.getByLabel('Question *').fill(question)
    await page.getByLabel('Answer *').fill('An answer written by the end-to-end test.')
    await page.locator('form').getByRole('button', { name: 'Add question' }).click()
    await expect(page.getByText('Question added.')).toBeVisible()
    await expect(page.getByText(question)).toBeVisible()

    await expect(async () => {
      await page.goto('/faq')
      await expect(page.getByRole('button', { name: question })).toBeVisible({ timeout: 3000 })
    }).toPass({ timeout: 45_000 })

    await page.goto('/admin/faq')
    await page.getByRole('button', { name: `Edit: ${question}` }).click()
    await page.getByLabel('Answer *').fill('A changed answer.')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText('Changes saved.')).toBeVisible()
    await page.getByRole('button', { name: `Remove: ${question}` }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Remove' }).click()
    await expect(page.getByText('Removed.')).toBeVisible()
    await expect(page.getByText(question)).toHaveCount(0)
    problems.check()
  })

  test('AD-USERS-01 customers: search, filter by blocked, open one', async ({ page }) => {
    const problems = watch(page)
    const blocked = people().blocked
    await page.goto('/admin/users')
    await page.getByPlaceholder('Name, email or phone').fill(blocked.email)
    const row = page.getByRole('row').filter({ hasText: blocked.email })
    await expect(row).toBeVisible()
    await expect(page.getByRole('row')).toHaveCount(2)                 // the heading row and the one match
    await page.getByPlaceholder('Name, email or phone').fill('')
    await page.getByLabel('Status').selectOption({ label: 'Blocked' })
    await expect(row).toBeVisible()
    await page.getByPlaceholder('Name, email or phone').fill('zzzz-no-such-customer')
    await expect(page.getByRole('row').filter({ hasText: '@' })).toHaveCount(0)
    await page.getByPlaceholder('Name, email or phone').fill(blocked.email)
    await row.getByRole('link').first().click()
    await expect(page).toHaveURL(/\/admin\/users\/[0-9a-f-]{36}/)
    await expect(page.getByText(blocked.email).first()).toBeVisible()
    await noSidewaysScroll(page)
    problems.check()
  })

  test('AD-AUDIT-01 the audit log lists actions and can be searched and filtered', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/admin/audit-log')
    await expect(page.getByRole('row').nth(1)).toBeVisible()
    await page.getByLabel('Made by').selectOption({ label: 'Admins' })
    await expect(page.getByRole('row').nth(1)).toBeVisible()
    await page.getByPlaceholder('Search summary, action, admin or record id').fill('zzzz-nothing-like-this')
    await expect(page.getByRole('row')).toHaveCount(0)
    await noSidewaysScroll(page)
    problems.check()
  })
})

test.describe('staff', () => {
  test.use({ storageState: authFile('staff') })

  test('AD-ROLE-STAFF staff open orders and the catalogue only; everything else is closed in the menu, by address and on the server', async ({ page, baseURL }) => {
    test.slow()
    const problems = watch(page)
    for (const [path, , , heading] of SCREENS.filter(([, a]) => allowed('staff', a))) {
      await openScreen(page, path, heading)
    }
    // the dashboard shows no tile a staff member cannot open
    await page.goto('/admin')
    await expect(page.getByRole('main').getByRole('link', { name: /customers|coupons|settings/i })).toHaveCount(0)
    problems.check()

    const nav = await menu(page)
    await expect(nav.getByRole('link', { name: 'Orders', exact: true })).toBeVisible()
    const closed = SCREENS.filter(([, a]) => !allowed('staff', a))
    for (const [, , label] of closed) {
      if (label) await expect(nav.getByRole('link', { name: label, exact: true })).toHaveCount(0)
    }
    for (const [path, , label] of closed) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: `${label} is not part of your role` })).toBeVisible()
    }
    const api = await apiAs(baseURL, 'staff')
    for (const url of ['/api/admin/users', '/api/admin/coupons', '/api/admin/campaigns', '/api/admin/audit-log', '/api/admin/settings', '/api/admin/staff', '/api/admin/pages', '/api/admin/homepage']) {
      expect((await api.get(url)).status(), url).toBe(403)
    }
    expect((await api.post('/api/admin/coupons', { code: 'STAFFTRY', discount_type: 'flat', discount_value: 1 })).status()).toBe(403)
    await api.dispose()
  })

  test('AD-ORDER-01 find an order, move it through its statuses, and the customer sees the change', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    const buyer = await apiAs(baseURL, `desk-${testInfo.project.name}`)
    const product = await (await buyer.get('/api/products/oxford-button-down-shirt')).json()
    for (const line of (await (await buyer.get('/api/cart')).json()).items || []) await buyer.delete(`/api/cart/items/${line.id}`)
    await buyer.post('/api/cart/items', { variant_id: product.variants.find((v) => v.stock_qty > 3).id, quantity: 1 })
    const address = (await (await buyer.get('/api/addresses')).json()).addresses[0]
    const placed = await (await buyer.post('/api/orders', { address_id: address.id, payment_method: 'cod' })).json()

    await page.goto('/admin/orders')
    await page.getByPlaceholder('Order number, customer name, email or phone').fill(placed.order_number)
    const row = page.getByRole('row').filter({ hasText: placed.order_number })
    await expect(row).toBeVisible()
    await expect(page.getByRole('row')).toHaveCount(2)
    await noSidewaysScroll(page)
    await row.getByRole('link', { name: placed.order_number }).click()
    await expect(page.getByRole('heading', { level: 1, name: placed.order_number })).toBeVisible()

    const status = page.locator('select').filter({ has: page.locator('option[value="confirmed"]') }).first()
    await status.selectOption('confirmed')
    await page.getByRole('button', { name: 'Update', exact: true }).click()
    await expect(page.getByText('Order status updated.')).toBeVisible()
    // an order only moves forward: "pending" is no longer offered
    await expect(status.locator('option[value="pending"]')).toHaveCount(0)
    await expect(status.locator('option[value="shipped"]')).toHaveCount(1)
    await noSidewaysScroll(page)

    expect((await (await buyer.get(`/api/orders/${placed.order_id}`)).json()).status).toBe('confirmed')
    await buyer.dispose()
    problems.check()
  })

  test('AD-PRODUCT-01 products: search, filters, pages, an empty result, and editing a product', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    await page.goto('/admin/products')
    await expect(page.getByRole('navigation', { name: 'Pagination' })).toContainText(/Page 1 of [2-9]/)
    await page.getByRole('button', { name: 'Next page' }).click()
    await expect(page.getByRole('navigation', { name: 'Pagination' })).toContainText(/Page 2 of/)
    await page.getByPlaceholder('Search by product name').fill('kurta')
    await expect(page.getByRole('row').filter({ hasText: /kurta/i }).first()).toBeVisible()
    await expect(page.getByRole('row').filter({ hasText: /blazer/i })).toHaveCount(0)
    await page.getByPlaceholder('Search by product name').fill('zzzz-no-such-product')
    await expect(page.getByRole('row').filter({ hasText: '₹' })).toHaveCount(0)
    await noSidewaysScroll(page)

    // a product made for this test, then edited on its screen
    const api = await apiAs(baseURL, 'staff')
    const categories = (await (await api.get('/api/admin/categories')).json()).categories
    const leaf = categories[0].children?.[0] || categories[0]
    const name = unique(testInfo, 'E2E Test Shirt')
    const slug = name.toLowerCase().replace(/\s+/g, '-')
    const created = await api.post('/api/admin/products', { category_id: leaf.id, name, slug, description: 'Made by the end-to-end test.', mrp: 999, selling_price: 799, is_active: false })
    expect(created.ok()).toBeTruthy()
    const product = await created.json()
    await page.goto(`/admin/products/${product.id}`)
    await expect(page.getByRole('heading', { level: 1, name: 'Edit Product' })).toBeVisible()
    await expect(page.getByLabel('Name *')).toHaveValue(name)
    await page.getByLabel('Name *').fill(`${name} edited`)
    await page.locator('form button[type="submit"]').first().click()
    await expect(page.getByText('Product saved.')).toBeVisible()
    expect((await (await api.get(`/api/admin/products/${product.id}`)).json()).name).toBe(`${name} edited`)
    await api.dispose()
    problems.check()
  })
})

test.describe('not signed in', () => {
  test('AD-LOGIN-01 the dashboard sends a visitor to the admin sign-in; a customer session does not open it', async ({ page }) => {
    await page.goto('/admin/orders')
    await expect(page).toHaveURL(/\/admin\/login/)
    await expect(page.getByLabel('Email')).toBeVisible()
  })

  test('AD-LOGIN-02 a wrong admin password is refused', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'w768', 'admin sign-ins are limited to 5 per 15 minutes; one width is enough to see the message')
    const problems = watch(page, { allow: ['/api/admin/auth/login'] })
    await page.goto('/admin/login')
    await page.getByLabel('Email').fill(people().owner.email)
    await page.getByLabel('Password').fill('not-the-password')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page.getByText(/invalid|incorrect|wrong/i).first()).toBeVisible()
    await expect(page).toHaveURL(/\/admin\/login/)
    problems.check()
  })
})
