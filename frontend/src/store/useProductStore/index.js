import { create } from 'zustand'
import apiClient from '@/services/apiClient'

export const useProductStore = create((set) => ({
  products: [],
  product: null,
  categories: [],
  loading: true,
  loadingMore: false,
  error: null,
  page: 1,
  pages: 1,
  total: 0,

  // Pass append=true to keep the existing products and add the next page onto
  // them (the "Load More" flow); otherwise the result replaces the list.
  fetchProducts: async (params = {}, append = false) => {
    set(append ? { loadingMore: true, error: null } : { loading: true, error: null })
    try {
      const { data } = await apiClient.get('/products', { params })
      set((state) => ({
        products: append ? [...state.products, ...data.products] : data.products,
        page: data.page,
        pages: data.pages,
        total: data.total,
        loading: false,
        loadingMore: false,
      }))
    } catch {
      set({ loading: false, loadingMore: false, error: 'Failed to load products' })
    }
  },

  fetchProduct: async (slug) => {
    set({ loading: true, error: null, product: null })
    try {
      const { data } = await apiClient.get(`/products/${slug}`)
      set({ product: data, loading: false })
    } catch {
      set({ loading: false, error: 'Product not found' })
    }
  },

  fetchCategories: async () => {
    try {
      const { data } = await apiClient.get('/categories')
      set({ categories: data.categories })
    } catch {
      // silent
    }
  },
}))
