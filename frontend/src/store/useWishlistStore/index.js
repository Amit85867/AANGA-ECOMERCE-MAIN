import { create } from 'zustand'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'

const hasToken = () => !!localStorage.getItem('aanga_token')

export const useWishlistStore = create((set, get) => ({
  items: [],
  productIds: [],
  loading: false,

  fetchWishlist: async () => {
    if (!hasToken()) {
      set({ items: [], productIds: [] })
      return
    }
    set({ loading: true })
    try {
      const { data } = await apiClient.get('/wishlist')
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
}))
