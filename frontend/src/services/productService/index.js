import apiClient from '@/services/apiClient'

export const productService = {
  list: (params) => apiClient.get('/products', { params }),
  getBySlug: (slug) => apiClient.get(`/products/${slug}`),
}
