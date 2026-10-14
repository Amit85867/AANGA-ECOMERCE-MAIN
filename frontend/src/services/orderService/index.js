import apiClient from '@/services/apiClient'

export const orderService = {
  list: () => apiClient.get('/orders'),
  getById: (orderId) => apiClient.get(`/orders/${orderId}`),
  // idempotencyKey (optional): makes a retried/double-submitted COD checkout
  // resolve to a single order on the backend instead of placing two.
  create: (payload, idempotencyKey) =>
    apiClient.post('/orders', payload, {
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
    }),
}
