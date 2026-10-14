import { create } from 'zustand'
import apiClient, { getAccessToken, sessionSettled } from '@/services/apiClient'
import { toast } from '@/components/ui/toastStore'

// Tokens are no longer persisted — the in-memory access token is the signal.
const hasToken = () => !!getAccessToken()

// Counts every change the customer makes, so a list fetched before a change
// but answered after it does not put the heart back the way it was.
let changes = 0

export const useWishlistStore = create((rawSet, get) => {
  const set = (next) => { if ('productIds' in next) changes += 1; rawSet(next) }
  return {
  items: [],
  productIds: [],
  loading: false,

  fetchWishlist: async () => {
    if (!hasToken()) {
      set({ items: [], productIds: [] })
      return
    }
    set({ loading: true })
    const before = changes
    try {
      const { data } = await apiClient.get('/wishlist')
      if (changes !== before) {
        set({ loading: false })
        return
      }
      set({
        items: data.items,
        productIds: data.items.map((i) => i.product_id),
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },

  // Toggle a product in the wishlist. Returns { needsAuth } if logged out.
  toggle: async (productId) => {
    await sessionSettled
    if (!hasToken()) {
      toast.info('Please sign in to save items')
      return { needsAuth: true }
    }
    const has = get().productIds.includes(productId)
    try {
      if (has) {
        await apiClient.delete(`/wishlist/${productId}`)
        set({
          productIds: get().productIds.filter((id) => id !== productId),
          items: get().items.filter((i) => i.product_id !== productId),
        })
      } else {
        await apiClient.post('/wishlist', { product_id: productId })
        set({ productIds: [...get().productIds, productId] })
        toast.success('Added to wishlist')
      }
      return { ok: true }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Wishlist update failed')
      return { ok: false }
    }
  },

  remove: async (productId) => {
    try {
      await apiClient.delete(`/wishlist/${productId}`)
      set({
        productIds: get().productIds.filter((id) => id !== productId),
        items: get().items.filter((i) => i.product_id !== productId),
      })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not remove item')
    }
  },

  clearLocal: () => set({ items: [], productIds: [] }),
  }
})
