import { create } from 'zustand'
import apiClient, { getAccessToken, sessionSettled } from '@/services/apiClient'
import { toast } from '@/components/ui/toastStore'

// Tokens are no longer persisted — the in-memory access token is the signal.
const hasToken = () => !!getAccessToken()

// Counts every change the customer makes. A bag fetched before a change but
// answered after it is out of date, and showing it would undo what they just
// did on screen (the item they added, the coupon they removed) until the next
// reload.
let changes = 0

export const useCartStore = create((rawSet) => {
  const set = (next) => { if ('cart' in next) changes += 1; rawSet(next) }
  return {
  cart: null,
  loading: false,

  // Fetch the current server cart. No-op when logged out.
  fetchCart: async () => {
    if (!hasToken()) {
      set({ cart: null })
      return
    }
    set({ loading: true })
    const before = changes
    try {
      const { data } = await apiClient.get('/cart')
      set(changes === before ? { cart: data, loading: false } : { loading: false })
    } catch {
      set({ loading: false })
    }
  },

  // Add a variant to the cart. Returns { ok } or { needsAuth } so the caller
  // can redirect to login.
  addItem: async ({ variant_id, quantity = 1 }) => {
    await sessionSettled
    if (!hasToken()) return { needsAuth: true }
    try {
      const { data } = await apiClient.post('/cart/items', { variant_id, quantity })
      set({ cart: data })
      toast.success('Added to cart')
      return { ok: true }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not add to cart')
      return { ok: false }
    }
  },

  updateItem: async (itemId, quantity) => {
    try {
      const { data } = await apiClient.patch(`/cart/items/${itemId}`, { quantity })
      set({ cart: data })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Update failed')
    }
  },

  removeItem: async (itemId) => {
    try {
      const { data } = await apiClient.delete(`/cart/items/${itemId}`)
      set({ cart: data })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Remove failed')
    }
  },

  applyCoupon: async (code) => {
    try {
      const { data } = await apiClient.post('/cart/coupon', { code: code.trim().toUpperCase() })
      set({ cart: data })
      toast.success('Coupon applied')
      return { ok: true }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Invalid coupon')
      return { ok: false }
    }
  },

  removeCoupon: async () => {
    try {
      const { data } = await apiClient.delete('/cart/coupon')
      set({ cart: data })
    } catch {
      // ignore
    }
  },

  // Reset local state (e.g. after logout or a placed order).
  clearLocal: () => set({ cart: null }),
  }
})

// Selector helper — use as useCartStore(selectCartCount)
export const selectCartCount = (state) => state.cart?.item_count || 0
