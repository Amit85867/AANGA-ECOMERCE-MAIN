// A signed-in customer: account, wishlist, bag, coupons, checkout, orders, returns.
// Each screen width has its own buyer (made in global-setup), so widths do not
// share a bag.
import { test, expect } from '@playwright/test'
import { apiAs, authFile, noSidewaysScroll, people, watch } from './helpers.js'

const PRODUCT = 'oxford-button-down-shirt'          // ₹1,799, not in the sale
const PRICEY = 'double-breasted-wool-blazer'        // ₹5,999, not in the sale

const buyer = (testInfo) => `buyer-${testInfo.project.name}`

async function emptyBag(api) {
  const cart = await (await api.get('/api/cart')).json()
  for (const line of cart.items || []) await api.delete(`/api/cart/items/${line.id}`)
  await api.delete('/api/cart/coupon')
}

async function putInBag(api, slug, quantity = 1) {
  const product = await (await api.get(`/api/products/${slug}`)).json()
  const variant = product.variants.find((v) => v.stock_qty >= quantity + 2)
  const added = await api.post('/api/cart/items', { variant_id: variant.id, quantity })
  expect(added.ok(), `adding ${slug} to the bag`).toBeTruthy()
  return product
}

test.describe('new and returning customers', () => {
  test('CU-REG-01 a visitor registers, is signed in, and can sign out', async ({ page }, testInfo) => {
    const problems = watch(page)
    const email = `e2e.new.${testInfo.project.name}.${Date.now().toString(36)}@example.com`
    await page.goto('/register')
    await page.getByLabel('Full name').fill('E2E New Customer')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill('E2e-New-Customer-1!')
    await page.getByLabel('Confirm password').fill('E2e-New-Customer-1!')
    // the terms box is required: without it the form says so and stays put
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.getByText('Please accept the terms to create an account.')).toBeVisible()
    await page.getByRole('checkbox').check()
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.getByText('Your account is ready')).toBeVisible()
    await page.goto('/account/profile')
    await expect(page.locator('input[name="profile-email"]')).toHaveValue(email)
    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/auth/logout')),
      page.getByRole('button', { name: 'Sign out' }).first().click(),
    ])
    await page.goto('/account/orders')
    await expect(page).toHaveURL(/\/login/)
    problems.check()
  })

  test('CU-REG-02 registration refuses a weak password and a mismatched one', async ({ page }) => {
    await page.goto('/register')
    await page.getByLabel('Full name').fill('E2E Weak')
    await page.getByLabel('Email').fill(`e2e.weak.${Date.now().toString(36)}@example.com`)
    await page.getByLabel('Password', { exact: true }).fill('short')
    await page.getByLabel('Confirm password').fill('different')
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.locator('[role="alert"], .text-danger').first()).toBeVisible()
    await expect(page).toHaveURL(/\/register/)
  })

  test('CU-LOGIN-01 a returning customer signs in and lands where they were going', async ({ page }) => {
    const problems = watch(page)
    const who = people().other
    await page.goto('/account/addresses')
    await expect(page).toHaveURL(/\/login/)
    await page.getByLabel('Email').fill(who.email)
    await page.getByLabel('Password').fill(who.password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page).toHaveURL(/\/account\/addresses/)
    problems.check()
  })

  test('CU-LOGIN-02 a wrong password is refused with a clear message', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'w1280', 'sign-ins are limited to 10 per 15 minutes; one width is enough to see the message');
    const problems = watch(page, { allow: ['/api/auth/login'] })
    await page.goto('/login')
    await page.getByLabel('Email').fill(people().other.email)
    await page.getByLabel('Password').fill('not-the-password')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Invalid email or password')).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
    problems.check()
  })

  test('CU-FORGOT-01 "forgot password" accepts an address and does not say whether it exists', async ({ page }) => {
    await page.goto('/forgot-password')
    await page.locator('input[name="email"]').fill('nobody-here@example.com')
    await page.getByRole('button', { name: /send|reset/i }).click()
    await expect(page.getByText(/if an account|check your (email|inbox)|we have sent|sent/i).first()).toBeVisible()
  })

  test('CU-RESET-01 the reset page refuses a made-up link', async ({ page }) => {
    await page.goto('/reset-password?token=not-a-real-token')
    await page.locator('#new-password').fill('E2e-Another-Pass-1!')
    await page.locator('#confirm-password').fill('E2e-Another-Pass-1!')
    await page.getByRole('button', { name: /reset|save|change/i }).click()
    await expect(page.getByText(/invalid|expired/i).first()).toBeVisible()
  })
})

test.describe('blocked customer', () => {
  test.use({ storageState: authFile('blocked') })

  test('CU-BLOCK-01 a blocked customer loses their session and cannot reach the account', async ({ page }) => {
    await page.goto('/account/orders')
    await expect(page).toHaveURL(/\/login/)
  })

  test('CU-BLOCK-02 a blocked customer is told so when signing in', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'w390', 'sign-ins are limited to 10 per 15 minutes; one width is enough to see the message')
    await page.context().clearCookies()
    await page.goto('/login')
    await page.getByLabel('Email').fill(people().blocked.email)
    await page.getByLabel('Password').fill(people().blocked.password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText(/deactivated|blocked/i).first()).toBeVisible()
  })
})

test.describe('signed-in buyer', () => {
  test.use({ storageState: ({}, use, testInfo) => use(authFile(buyer(testInfo))) })
  test.describe.configure({ mode: 'serial' })

  test('CU-SESSION-01 the session survives a reload and keeps no token in the browser storage', async ({ page }) => {
    await page.goto('/account/profile')
    await expect(page.getByRole('heading', { level: 1, name: 'Profile' })).toBeVisible()
    await page.reload()
    await expect(page.getByRole('heading', { level: 1, name: 'Profile' })).toBeVisible()
    const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
    expect(stored).not.toMatch(/eyJ[A-Za-z0-9_-]{10,}\./)       // nothing that looks like a JWT
  })

  test('CU-WISH-01 save a product to the wishlist and remove it', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    await page.goto(`/product/${PRODUCT}`)
    await page.getByRole('button', { name: 'Add to wishlist' }).first().click()
    await expect(page.getByRole('button', { name: 'Remove from wishlist' }).first()).toBeVisible()
    await page.goto('/wishlist')
    await expect(page.getByText('Oxford Button-Down Shirt').first()).toBeVisible()
    await noSidewaysScroll(page)
    await page.getByRole('button', { name: 'Remove from wishlist' }).first().click()
    await expect(page.getByText('Nothing saved yet')).toBeVisible()
    problems.check()
    const api = await apiAs(baseURL, buyer(testInfo))
    expect((await (await api.get('/api/wishlist')).json()).items).toHaveLength(0)
    await api.dispose()
  })

  test('CU-BAG-01 add to bag from the product page, change the quantity, remove', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    await page.goto(`/product/${PRODUCT}`)
    await page.getByRole('button', { name: 'Add to bag' }).click()
    await expect(page.getByText('Added to cart')).toBeVisible()
    await page.goto('/cart')
    await expect(page.getByText('Oxford Button-Down Shirt')).toBeVisible()
    const summary = page.getByRole('complementary', { name: 'Order summary' })
    await expect(summary.getByText('Subtotal (1 item)')).toBeVisible()
    await page.getByRole('button', { name: 'Increase quantity' }).click()
    await expect(summary.getByText('Subtotal (2 items)')).toBeVisible()
    await expect(summary.getByText('₹3,598').first()).toBeVisible()
    await noSidewaysScroll(page)
    await page.getByRole('button', { name: 'Remove' }).click()
    await expect(page.getByText('Your bag is empty')).toBeVisible()
    await api.dispose()
    problems.check()
  })

  test('CU-COUPON-01 coupons: unknown code, below the minimum, valid, and only one at a time', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page, { allow: ['/api/cart/coupon'] })
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    await putInBag(api, PRODUCT)                       // ₹1,799
    await page.goto('/cart')
    const summary = page.getByRole('complementary', { name: 'Order summary' })
    const apply = async (code) => {
      await page.getByLabel('Coupon code').fill(code)
      await page.getByRole('button', { name: 'Apply' }).click()
    }

    await apply('NOSUCHCODE')
    await expect(page.getByText('Invalid coupon code')).toBeVisible()

    await apply('FESTIVE500')                          // needs ₹4,999
    await expect(page.getByText(/Minimum order value/)).toBeVisible()

    await apply('DIWALI10')                            // 10% above ₹1,499
    await expect(summary.getByText('Discount (DIWALI10)')).toBeVisible()
    await expect(summary.getByText('−₹179.90')).toBeVisible()
    // while one is applied there is no box to add a second
    await expect(page.getByLabel('Coupon code')).toHaveCount(0)

    // a dearer bag: swap to the other coupon, and still only one applies
    await putInBag(api, PRICEY)
    await page.reload()
    await page.getByRole('button', { name: 'Remove coupon DIWALI10' }).click()
    await apply('FESTIVE500')
    await expect(summary.getByText('Discount (FESTIVE500)')).toBeVisible()
    await expect(summary.getByText('−₹500')).toBeVisible()
    await expect(summary.getByText(/DIWALI10/)).toHaveCount(0)
    await page.getByRole('button', { name: 'Remove coupon FESTIVE500' }).click()
    await expect(summary.getByText(/Discount/)).toHaveCount(0)
    await api.dispose()
    problems.check()
  })

  test('CU-ADDR-01 add, edit and remove a delivery address; invalid PIN is refused', async ({ page }) => {
    const problems = watch(page, { allow: ['/api/addresses'] })
    await page.goto('/account/addresses')
    await page.getByRole('button', { name: 'Add address' }).first().click()
    await page.getByLabel('Full name').fill('E2E Second Address')
    await page.getByLabel('Phone').fill('9800000077')
    await page.getByLabel('Address', { exact: true }).fill('77 Second Street')
    await page.getByLabel('City').fill('Mumbai')
    await page.getByLabel('State').fill('Maharashtra')
    await page.getByLabel('PIN code').fill('012')
    await page.getByRole('button', { name: 'Save address' }).click()
    await expect(page.locator('[role="alert"], .text-danger').first()).toBeVisible()
    await page.getByLabel('PIN code').fill('400050')
    await page.getByRole('button', { name: 'Save address' }).click()
    await expect(page.getByText('Address saved')).toBeVisible()
    await expect(page.getByText('77 Second Street')).toBeVisible()

    const card = page.getByRole('main').getByRole('listitem').filter({ hasText: '77 Second Street' })
    await card.getByRole('button', { name: 'Edit' }).click()
    await page.getByLabel('City').fill('Pune')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText('Address updated')).toBeVisible()
    await expect(page.getByText(/Pune/).first()).toBeVisible()

    await page.getByRole('main').getByRole('listitem').filter({ hasText: '77 Second Street' }).getByRole('button', { name: 'Remove' }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Remove' }).click()
    await expect(page.getByText('Address removed')).toBeVisible()
    await expect(page.getByText('77 Second Street')).toHaveCount(0)
    await noSidewaysScroll(page)
    problems.check()
  })

  test('CU-PROFILE-01 change the name on the profile', async ({ page }, testInfo) => {
    await page.goto('/account/profile')
    const name = `E2E Buyer ${testInfo.project.name} Renamed`
    await page.locator('input[name="profile-name"]').fill(name)
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText('Profile updated')).toBeVisible()
    await page.reload()
    await expect(page.locator('input[name="profile-name"]')).toHaveValue(name)
  })

  test('CU-CHECKOUT-01 cash on delivery from bag to confirmation, with the same total at every step', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    await putInBag(api, PRODUCT, 2)                    // 2 × ₹1,799 = ₹3,598
    await api.post('/api/cart/coupon', { code: 'DIWALI10' })
    const cart = await (await api.get('/api/cart')).json()
    const total = `₹${cart.total.toLocaleString('en-IN', { minimumFractionDigits: Number.isInteger(cart.total) ? 0 : 2, maximumFractionDigits: 2 })}`

    await page.goto('/cart')
    await expect(page.getByRole('complementary', { name: 'Order summary' }).getByText(total)).toBeVisible()
    await page.getByRole('link', { name: 'Checkout' }).click()

    // 1. address
    await expect(page.getByText('12 Test Lane')).toBeVisible()
    await expect(page.getByText(total).first()).toBeVisible()
    await page.getByRole('button', { name: 'Continue to payment' }).click()

    // 2. payment: with no gateway keys only cash on delivery can be chosen
    await expect(page.getByRole('radio', { name: /Cash on delivery/ })).toBeChecked()
    await expect(page.getByRole('radio', { name: /Pay online/ })).toBeDisabled()
    await expect(page.getByText('Not available at the moment.')).toBeVisible()
    await noSidewaysScroll(page)
    await page.getByRole('button', { name: 'Review order' }).click()

    // 3. review and place
    await expect(page.getByText(total).first()).toBeVisible()
    await page.getByRole('button', { name: 'Place order' }).click()
    await expect(page.getByRole('heading', { name: /Thank you/ })).toBeVisible()
    await expect(page).toHaveURL(/\/order-confirmed\/\d+/)
    await expect(page.getByText(total).first()).toBeVisible()
    const orderId = Number(page.url().match(/order-confirmed\/(\d+)/)[1])

    // the order as the server stored it, and as the customer and the owner see it
    const order = await (await api.get(`/api/orders/${orderId}`)).json()
    expect(order.total_amount).toBe(cart.total)
    expect(order.subtotal).toBe(cart.subtotal)
    expect(order.discount_amount).toBe(cart.discount)
    await page.goto(`/account/orders/${orderId}`)
    await expect(page.getByText(total).first()).toBeVisible()
    await noSidewaysScroll(page)
    const owner = await apiAs(baseURL, 'owner')
    expect((await (await owner.get(`/api/admin/orders/${orderId}`)).json()).total_amount).toBe(cart.total)
    await owner.dispose()

    // the bag is empty and the order is in the history
    expect((await (await api.get('/api/cart')).json()).items).toHaveLength(0)
    await page.goto('/account/orders')
    await expect(page.getByText(order.order_number)).toBeVisible()
    await api.dispose()
    problems.check()
  })

  test('CU-CHECKOUT-02 pressing "Place order" twice makes one order', async ({ page, baseURL }, testInfo) => {
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    await putInBag(api, PRODUCT)
    const before = (await (await api.get('/api/orders?per_page=50')).json()).total
    await page.goto('/checkout')
    await page.getByRole('button', { name: 'Continue to payment' }).click()
    await page.getByRole('button', { name: 'Review order' }).click()
    await page.getByRole('button', { name: 'Place order' }).dblclick()
    await expect(page.getByRole('heading', { name: /Thank you/ })).toBeVisible()
    const after = (await (await api.get('/api/orders?per_page=50')).json()).total
    expect(after).toBe(before + 1)
    await api.dispose()
  })

  test('CU-CHECKOUT-03 reloading in the middle of checkout loses nothing', async ({ page, baseURL }, testInfo) => {
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    await putInBag(api, PRODUCT)
    await page.goto('/checkout')
    await page.getByRole('button', { name: 'Continue to payment' }).click()
    await page.reload()
    await expect(page.getByText('12 Test Lane')).toBeVisible()
    await expect(page.getByRole('complementary', { name: 'Order summary' }).getByText('Subtotal (1 item)')).toBeVisible()
    await emptyBag(api)
    await page.reload()
    await expect(page.getByText('Your bag is empty')).toBeVisible()
    await api.dispose()
  })

  test('CU-ORDER-01 cancel an order; stock comes back', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    const product = await putInBag(api, PRICEY)
    const variantId = (await (await api.get('/api/cart')).json()).items[0].variant_id
    const stockOf = async () => (await (await api.get(`/api/products/${PRICEY}`)).json()).variants.find((v) => v.id === variantId).stock_qty
    const address = (await (await api.get('/api/addresses')).json()).addresses[0]
    const stockBefore = product.variants.find((v) => v.id === variantId).stock_qty
    const placed = await (await api.post('/api/orders', { address_id: address.id, payment_method: 'cod' })).json()

    await page.goto(`/account/orders/${placed.order_id}`)
    await page.getByRole('button', { name: 'Cancel order' }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel order' }).click()
    await expect(page.getByText('Order cancelled').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Cancel order' })).toHaveCount(0)
    // (the product page is cached for a few seconds; ask until it is fresh)
    await expect.poll(stockOf, { timeout: 45_000, intervals: [2000] }).toBe(stockBefore)
    await api.dispose()
    problems.check()
  })

  test('CU-RETURN-01 return an item from a delivered order, then review the product', async ({ page, baseURL }, testInfo) => {
    const problems = watch(page)
    const api = await apiAs(baseURL, buyer(testInfo))
    await emptyBag(api)
    await putInBag(api, 'slim-chino-trousers')
    const address = (await (await api.get('/api/addresses')).json()).addresses[0]
    const placed = await (await api.post('/api/orders', { address_id: address.id, payment_method: 'cod' })).json()
    const owner = await apiAs(baseURL, 'owner')
    for (const status of ['confirmed', 'shipped', 'delivered']) {
      expect((await owner.patch(`/api/admin/orders/${placed.order_id}/status`, { status })).ok()).toBeTruthy()
    }
    await owner.dispose()

    await page.goto(`/account/orders/${placed.order_id}`)
    await expect(page.getByText(/delivered/i).first()).toBeVisible()
    await page.getByRole('button', { name: 'Return an item' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.locator('[name="return-reason"]').selectOption('size_issue')
    await dialog.locator('[name="return-notes"]').fill('Too small. End-to-end test.')
    await dialog.getByRole('button', { name: 'Request return' }).click()
    await expect(page.getByText(/Return requested/).first()).toBeVisible()
    // nothing left to return on this order, so the button goes
    await expect(page.getByRole('button', { name: 'Return an item' })).toHaveCount(0)
    await page.goto('/account/returns')
    await expect(page.getByText(placed.order_number)).toBeVisible()
    await noSidewaysScroll(page)

    await page.goto('/product/slim-chino-trousers')
    await page.getByRole('button', { name: 'Write a review' }).click()
    const review = page.getByRole('dialog')
    await review.getByRole('radio', { name: /4/ }).check({ force: true })
    await review.getByLabel('Headline').fill(`Good trousers ${testInfo.project.name}`)
    await review.getByLabel('Your review').fill('Comfortable and well cut. <b>not bold</b>')
    await review.getByRole('button', { name: 'Submit review' }).click()
    await expect(page.getByText(`Good trousers ${testInfo.project.name}`)).toBeVisible()
    // text typed by a customer is shown as text
    await expect(page.getByText('<b>not bold</b>').first()).toBeVisible()
    await api.dispose()
    problems.check()
  })
})

test.describe('another customer', () => {
  test.use({ storageState: authFile('other') })

  test('CU-IDOR-01 someone else cannot open a buyer’s order by its address', async ({ page, baseURL }, testInfo) => {
    const buyerApi = await apiAs(baseURL, buyer(testInfo))
    const orders = (await (await buyerApi.get('/api/orders')).json()).orders
    await buyerApi.dispose()
    test.skip(orders.length === 0, 'the buyer has no order yet (run the whole file)')
    const problems = watch(page, { allow: [`/api/orders/${orders[0].id}`] })
    await page.goto(`/account/orders/${orders[0].id}`)
    await expect(page.getByText('We could not find that order.')).toBeVisible()
    await expect(page.getByText(orders[0].order_number)).toHaveCount(0)
    await page.goto('/account/orders')
    await expect(page.getByText('No orders yet')).toBeVisible()
    problems.check()
  })
})
