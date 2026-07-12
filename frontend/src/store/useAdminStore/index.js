import { create } from 'zustand'
import adminApi from '@/services/adminApi'

export const useAdminStore = create((set, get) => ({
  admin: JSON.parse(localStorage.getItem('aanga_admin') || 'null'),
  isAuthenticated: !!localStorage.getItem('aanga_admin_token'),

  login: async (email, password) => {
    const { data } = await adminApi.post('/admin/auth/login', { email, password })
    localStorage.setItem('aanga_admin_token', data.access_token)
    localStorage.setItem('aanga_admin', JSON.stringify(data.admin))
    set({ admin: data.admin, isAuthenticated: true })
    return data
  },

  logout: () => {
    localStorage.removeItem('aanga_admin_token')
    localStorage.removeItem('aanga_admin')
    set({ admin: null, isAuthenticated: false })
  },

  fetchMe: async () => {
    try {
      const { data } = await adminApi.get('/admin/auth/me')
      localStorage.setItem('aanga_admin', JSON.stringify(data))
      set({ admin: data, isAuthenticated: true })
    } catch {
      get().logout()
    }
  },
}))
