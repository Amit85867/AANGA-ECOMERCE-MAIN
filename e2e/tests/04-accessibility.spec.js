// Keyboard only: no mouse, no touch. Everything is reached with Tab and
// pressed with Enter or Space, and the focused control is always marked.
import { test, expect } from '@playwright/test'
import { apiAs, authFile, unique } from './helpers.js'

/** Press Tab until `target` has the focus (fails if it never gets it). */
async function tabTo(page, target, { limit = 80 } = {}) {
  for (let i = 0; i < limit; i += 1) {
    if (await target.evaluate((el) => el === document.activeElement).catch(() => false)) {
      // the focus must be visible, not just present
      const marked = await target.evaluate((el) => {
        const s = getComputedStyle(el)
        return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'
      })
      expect(marked, 'the focused control shows a focus ring').toBeTruthy()
      return
    }
    await page.keyboard.press('Tab')
  }
  throw new Error(`Tab never reached ${target}`)
}

test.describe('keyboard only', () => {
  test.describe('checkout', () => {
    test.use({ storageState: ({}, use, testInfo) => use(authFile(`keys-${testInfo.project.name}`)) })

    test('A11Y-CHECKOUT-01 a customer checks out with cash on delivery using only the keyboard', async ({ page, baseURL }, testInfo) => {
      const api = await apiAs(baseURL, `keys-${testInfo.project.name}`)
      for (const line of (await (await api.get('/api/cart')).json()).items || []) await api.delete(`/api/cart/items/${line.id}`)
      const source = await (await api.get('/api/products/oxford-button-down-shirt')).json()
      await api.post('/api/cart/items', { variant_id: source.variants.find((v) => v.stock_qty > 3).id, quantity: 1 })

      await page.goto('/cart')
      await expect(page.getByRole('link', { name: 'Checkout' })).toBeVisible()
      await tabTo(page, page.getByRole('link', { name: 'Checkout' }))
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL(/\/checkout/)

      await expect(page.getByRole('button', { name: 'Continue to payment' })).toBeVisible()
      await tabTo(page, page.getByRole('button', { name: 'Continue to payment' }))
      await page.keyboard.press('Enter')

      await expect(page.getByRole('radio', { name: /Cash on delivery/ })).toBeChecked()
      await tabTo(page, page.getByRole('button', { name: 'Review order' }))
      await page.keyboard.press('Enter')

      await expect(page.getByRole('button', { name: 'Place order' })).toBeVisible()
      await tabTo(page, page.getByRole('button', { name: 'Place order' }))
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: /Thank you/ })).toBeVisible()
      await api.dispose()
    })
  })

  test.describe('dashboard', () => {
    test.use({ storageState: authFile('manager') })

    test('A11Y-ADMIN-01 a manager adds a FAQ entry using only the keyboard', async ({ page, baseURL }, testInfo) => {
      const question = `${unique(testInfo, 'E2E keyboard question')}?`
      await page.goto('/admin/faq')
      const add = page.getByRole('button', { name: 'Add question' }).first()
      await expect(add).toBeVisible()
      await tabTo(page, add)
      await page.keyboard.press('Enter')
      await tabTo(page, page.getByLabel('Question *'))
      await page.keyboard.type(question)
      await page.keyboard.press('Tab')
      await expect(page.getByLabel('Answer *')).toBeFocused()
      await page.keyboard.type('Typed without touching the mouse.')
      await tabTo(page, page.locator('form').getByRole('button', { name: 'Add question' }))
      await page.keyboard.press('Enter')
      await expect(page.getByText('Question added.')).toBeVisible()

      // the confirm dialog takes the focus and Escape closes it without removing anything
      const remove = page.getByRole('button', { name: `Remove: ${question}` })
      await remove.focus()
      await page.keyboard.press('Enter')
      const dialog = page.getByRole('alertdialog')
      await expect(dialog).toBeVisible()
      expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBeTruthy()
      await page.keyboard.press('Escape')
      await expect(dialog).toHaveCount(0)
      await expect(page.getByText(question)).toBeVisible()

      const api = await apiAs(baseURL, 'manager')
      const items = (await (await api.get('/api/admin/faq')).json())
      const mine = (items.faqs || items.items || items.entries || []).find((f) => f.question === question)
      if (mine) await api.delete(`/api/admin/faq/${mine.id}`)
      await api.dispose()
    })
  })
})
