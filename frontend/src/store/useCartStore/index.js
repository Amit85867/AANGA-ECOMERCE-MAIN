import { create } from 'zustand'
import apiClient, { getAccessToken } from '@/services/apiClient'
import { toast } from '@/components/ui/toastStore'

// Tokens are no longer persisted — the in-memory access token is the signal.
const hasToken = () => !!getAccessToken()

export const useCartStore = create((set) => ({
  cart: null,
  loading: false,

  // Fetch the current server cart. No-op when logged out.
  fetchCart: async () => {
    if (!hasToken()) {
      set({ cart: null })
      return
    }
    set({ loading: true })
    try {
      const { data } = await apiClient.get('/cart')
      set({ cart: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  // Add a variant to the cart. Returns { ok } or { needsAuth } so the caller
  // can redirect to login.
  addItem: async ({ variant_id, quantity = 1 }) => {
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
}))

// Selector helper — use as useCartStore(selectCartCount)
export const selectCartCount = (state) => state.cart?.item_count || 0
