import apiClient from '@/services/apiClient'

export const cartService = {
  get: () => apiClient.get('/cart'),
  addItem: (payload) => apiClient.post('/cart/items', payload),
  updateItem: (itemId, payload) => apiClient.patch(`/cart/items/${itemId}`, payload),
  removeItem: (itemId) => apiClient.delete(`/cart/items/${itemId}`),
}
