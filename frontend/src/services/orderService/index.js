import apiClient from '@/services/apiClient'

export const orderService = {
  list: () => apiClient.get('/orders'),
  getById: (orderId) => apiClient.get(`/orders/${orderId}`),
  create: (payload) => apiClient.post('/orders', payload),
}
