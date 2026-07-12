import { create } from 'zustand'
import apiClient from '@/services/apiClient'

export const useProductStore = create((set, get) => ({
  products: [],
  product: null,
  categories: [],
  loading: false,
  error: null,
  page: 1,
  pages: 1,
  total: 0,

  fetchProducts: async (params = {}) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.get('/products', { params })
      set({
        products: data.products,
        page: data.page,
        pages: data.pages,
        total: data.total,
        loading: false,
      })
    } catch (err) {
      set({ loading: false, error: 'Failed to load products' })
    }
  },

  fetchProduct: async (slug) => {
    set({ loading: true, error: null, product: null })
    try {
      const { data } = await apiClient.get(`/products/${slug}`)
      set({ product: data, loading: false })
    } catch (err) {
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
