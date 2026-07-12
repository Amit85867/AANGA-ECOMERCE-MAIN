import apiClient from '@/services/apiClient'

export const wishlistService = {
  get: () => apiClient.get('/wishlist'),
  add: (product_id, variant_id) => apiClient.post('/wishlist', { product_id, variant_id }),
  remove: (productId) => apiClient.delete(`/wishlist/${productId}`),
}
