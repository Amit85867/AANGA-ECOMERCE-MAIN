// What a visitor who is not signed in can see and do.
import { test, expect } from '@playwright/test'
import { cardPrices, isNarrow, noSidewaysScroll, watch } from './helpers.js'

test.describe('storefront, anonymous visitor', () => {
  test('SF-HOME-01 home page shows the live campaign, every section and no errors', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible()
    // the Diwali campaign from the demo content is live
    await expect(page.locator('html')).toHaveAttribute('data-festive', 'marigold')
    await expect(page.getByText(/Ends in/).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /Shop the Diwali Edit/ }).first()).toBeVisible()
    for (const heading of ['Shop by Category', 'Best Sellers', 'What Customers Say']) {
      await expect(page.getByRole('heading', { name: heading })).toBeVisible()
    }
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible()
    await noSidewaysScroll(page)
    problems.check()
  })

  test('SF-HOME-02 header menu reaches a category and the footer links work', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/')
    if (isNarrow(page)) {
      await page.getByRole('button', { name: 'Open menu' }).click()
      await page.getByRole('link', { name: 'Offers', exact: true }).first().click()
      await expect(page).toHaveURL(/\/offers/)
    } else {
      await page.getByRole('navigation').getByRole('link', { name: /^Women/ }).first().click()
      await expect(page).toHaveURL(/category=women/)
      await expect(page.getByRole('heading', { level: 1, name: 'Women' })).toBeVisible()
    }
    await page.goto('/')
    await page.getByRole('contentinfo').getByRole('link', { name: 'FAQ' }).click()
    await expect(page).toHaveURL(/\/faq/)
    problems.check()
  })

  test('SF-SHOP-01 listing loads, a parent category shows its products, and filters combine', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/shop')
    await expect(page.getByText(/^\d+ products?$/)).toBeVisible()
    expect(await page.locator('main a[href^="/product/"]').count()).toBeGreaterThan(0)

    await page.goto('/shop?category=men')
    await expect(page.getByRole('heading', { level: 1, name: 'Men' })).toBeVisible()
    await expect(page.getByText(/^\d+ products?$/)).not.toHaveText('0 products')

    await page.goto('/shop?category=women&sort=price_asc&max_price=3000')
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible()
    const prices = await cardPrices(page)
    expect(prices.every((p) => p <= 3000)).toBeTruthy()
    expect(prices).toEqual([...prices].sort((a, b) => a - b))
    await noSidewaysScroll(page)
    problems.check()
  })

  test('SF-SHOP-02 sort by price uses the sale price, low to high and high to low', async ({ page }) => {
    await page.goto('/collections/diwali-edit?sort=price_asc')
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible()
    const up = await cardPrices(page)
    expect(up.length).toBe(12)
    expect(up).toEqual([...up].sort((a, b) => a - b))
    await page.goto('/collections/diwali-edit?sort=price_desc')
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible()
    const down = await cardPrices(page)
    expect(down).toEqual([...down].sort((a, b) => b - a))
  })

  test('SF-SHOP-03 search finds products, and a search with no match says so', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/shop?q=kurta')
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toContainText('kurta')
    await page.goto('/shop?q=zzzznothingmatches')
    await expect(page.getByText('Nothing matches')).toBeVisible()
    await expect(page.getByText('0 products')).toBeVisible()
    problems.check()
  })

  test('SF-SHOP-04 a long list pages with "load more"', async ({ page }) => {
    await page.goto('/shop')
    const cards = page.locator('main a[href^="/product/"]')
    await expect(cards.first()).toBeVisible()
    const before = await cards.count()
    await page.getByRole('button', { name: /load more|show more/i }).click()
    await expect.poll(() => cards.count()).toBeGreaterThan(before)
  })

  test('SF-SHOP-05 slow network shows a loading state, then the products', async ({ page }) => {
    await page.route('**/api/products?**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2500))
      await route.continue()
    })
    await page.goto('/shop?sort=price_asc')
    await expect(page.getByText('Loading products…')).toBeVisible()
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible({ timeout: 15_000 })
  })

  test('SF-SHOP-06 a failing API shows an error with a way to retry, and recovers', async ({ page }) => {
    let failing = true
    await page.route('**/api/products?**', (route) => (failing ? route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"boom"}' }) : route.continue()))
    await page.goto('/shop?sort=price_desc')
    await expect(page.getByText('We could not load the products.')).toBeVisible({ timeout: 15_000 })
    failing = false
    await page.getByRole('button', { name: 'Try again' }).click()
    await expect(page.locator('main a[href^="/product/"]').first()).toBeVisible()
  })

  test('SF-COLL-01 the Diwali Edit shows sale badges and reduced prices', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/collections/diwali-edit')
    await expect(page.getByRole('heading', { level: 1, name: 'Diwali Edit' })).toBeVisible()
    await expect(page.getByText('12 products')).toBeVisible()
    await expect(page.locator('.sale-badge').first()).toBeVisible()
    await expect(page.getByText(/20% off everything in this collection/)).toBeVisible()
    await noSidewaysScroll(page)
    problems.check()
  })

  test('SF-PROD-01 product page: gallery, price, variants, details; adding to the bag asks a visitor to sign in', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/product/silk-blend-anarkali-kurta')
    await expect(page.getByRole('heading', { level: 1, name: 'Silk Blend Anarkali Kurta' })).toBeVisible()
    await expect(page.locator('.sale-badge').first()).toContainText('Diwali Festive Sale')
    await expect(page.getByText('₹3,599').first()).toBeVisible()
    await page.getByRole('button', { name: 'Size M', exact: true }).click()
    await page.getByRole('button', { name: 'Emerald' }).click()
    await expect(page.getByText(/COLOUR: EMERALD/i)).toBeVisible()
    await page.getByRole('button', { name: /Fabric & Care/i }).click()
    await expect(page.getByText(/Dry clean only/)).toBeVisible()
    // no courier keys: the delivery check must not be offered
    await expect(page.getByLabel('PIN code')).toHaveCount(0)
    await noSidewaysScroll(page)
    await page.getByRole('button', { name: 'Add to bag' }).click()
    await expect(page).toHaveURL(/\/login/)
    problems.check()
  })

  test('SF-PROD-02 an unknown product shows "not found", not a broken page', async ({ page }) => {
    const problems = watch(page, { allow: ['/api/products/no-such-product'] })
    await page.goto('/product/no-such-product')
    await expect(page.getByText(/not found|could not find/i).first()).toBeVisible()
    problems.check()
  })

  for (const [id, path, heading] of [
    ['SF-PAGE-ABOUT', '/about', 'About Us'], ['SF-PAGE-SHIPPING', '/shipping', 'Shipping Policy'],
    ['SF-PAGE-RETURNS', '/returns', 'Returns & Exchanges'], ['SF-PAGE-PRIVACY', '/privacy-policy', 'Privacy Policy'],
    ['SF-PAGE-TERMS', '/terms', 'Terms & Conditions'],
  ]) {
    test(`${id} ${path} shows the owner-written page`, async ({ page }) => {
      const problems = watch(page)
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
      await expect(page.locator('.cms-prose')).toBeVisible()
      await noSidewaysScroll(page)
      problems.check()
    })
  }

  test('SF-PAGE-FAQ questions open and close', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/faq')
    const question = page.getByRole('button', { name: 'How much is shipping?' })
    await expect(question).toBeVisible()
    await question.click()
    await expect(page.getByText(/Shipping is free above the amount/)).toBeVisible()
    await question.click()
    await expect(page.getByText(/Shipping is free above the amount/)).toHaveCount(0)
    await noSidewaysScroll(page)
    problems.check()
  })

  test('SF-PAGE-CONTACT the contact form validates and sends', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/contact')
    await expect(page.getByText('hello@example.com')).toBeVisible()
    await page.getByRole('button', { name: /send/i }).click()
    await expect(page.locator('[role="alert"], .text-danger').first()).toBeVisible()
    await page.getByLabel(/name/i).first().fill('E2E Visitor')
    await page.getByLabel(/email/i).first().fill('e2e.visitor@example.com')
    await page.getByLabel(/message/i).fill('This is an automated end-to-end test message.')
    await page.getByRole('button', { name: /send/i }).click()
    await expect(page.getByText(/thank|received|sent|got your message/i).first()).toBeVisible()
    problems.check()
  })

  test('SF-PAGE-OFFERS offers and wholesale pages load', async ({ page }) => {
    const problems = watch(page)
    await page.goto('/offers')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.goto('/wholesale')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await noSidewaysScroll(page)
    problems.check()
  })

  test('SF-404-01 an unknown address shows the 404 page with a way back', async ({ page }) => {
    await page.goto('/this/page/does/not/exist')
    await expect(page.getByText('Page Not Found')).toBeVisible()
    await page.getByRole('link', { name: /home|shop/i }).first().click()
    await expect(page).not.toHaveURL(/does\/not\/exist/)
  })

  test('SF-AUTH-01 account pages send a visitor to sign in', async ({ page }) => {
    for (const path of ['/account/orders', '/account/addresses', '/account/profile', '/checkout']) {
      await page.goto(path)
      await expect(page).toHaveURL(/\/login/)
    }
    // the wishlist explains itself instead of redirecting
    await page.goto('/wishlist')
    await expect(page.getByRole('heading', { name: 'Sign in to see your wishlist' })).toBeVisible()
  })

  test('SF-CAMP-01 with no campaign live the festive look and countdown are absent', async ({ page }) => {
    await page.route('**/api/content/layout', async (route) => {
      const response = await route.fetch()
      const body = await response.json()
      await route.fulfill({ response, json: { ...body, campaign: null, next_change_at: null } })
    })
    await page.addInitScript(() => localStorage.removeItem('aanga.layout.v1'))
    await page.goto('/about')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.locator('html')).not.toHaveAttribute('data-festive', /.+/)
    await expect(page.getByText(/Ends in/)).toHaveCount(0)
    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })

  test('SF-MAINT-01 maintenance mode shows the maintenance page instead of the store', async ({ page }) => {
    await page.route('**/api/cms/settings', async (route) => {
      const response = await route.fetch()
      const body = await response.json()
      await route.fulfill({ response, json: { settings: { ...body.settings, maintenance_mode: 'true', maintenance_message: 'Back at 6 pm.' } } })
    })
    await page.goto('/shop')
    await expect(page.getByText('Back at 6 pm.')).toBeVisible()
    await expect(page.locator('main a[href^="/product/"]')).toHaveCount(0)
    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })
})
