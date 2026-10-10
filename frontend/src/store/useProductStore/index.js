import { create } from 'zustand'
import { takeEarly } from '@/services/early'
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
      // The plain first page of the shop may already be on its way.
      const isDefaultFirstPage =
        !append && params.page === 1 && params.per_page === 12 && params.sort === 'newest' &&
        Object.keys(params).length === 3
      const early = isDefaultFirstPage ? await takeEarly('products') : null
      const data = early ?? (await apiClient.get('/products', { params })).data
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
      const early = await takeEarly(`product:${slug}`)
      const data = early ?? (await apiClient.get(`/products/${slug}`)).data
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
