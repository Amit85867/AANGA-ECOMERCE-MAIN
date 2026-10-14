import { create } from 'zustand'
import adminApi, { setAdminAccessToken, refreshAdminAccessToken } from '@/services/adminApi'

/*
 * No admin credentials are persisted. The access token lives in memory (see
 * adminApi) and the refresh token is an httpOnly cookie, so a reload restores
 * the session via restoreSession() instead of reading localStorage.
 */
export const useAdminStore = create((set) => ({
  admin: null,
  isAuthenticated: false,
  // True until we've tried to restore an existing admin session.
  initializing: true,

  login: async (email, password) => {
    const { data } = await adminApi.post('/admin/auth/login', { email, password })
    setAdminAccessToken(data.access_token)
    set({ admin: data.admin, isAuthenticated: true, initializing: false })
    return data
  },

  logout: async () => {
    try {
      await adminApi.post('/admin/auth/logout')
    } catch {
      // Drop local state regardless.
    }
    setAdminAccessToken(null)
    set({ admin: null, isAuthenticated: false, initializing: false })
  },

  // Exchange the httpOnly admin refresh cookie for an access token on load.
  restoreSession: async () => {
    try {
      await refreshAdminAccessToken()
      const { data } = await adminApi.get('/admin/auth/me')
      set({ admin: data, isAuthenticated: true, initializing: false })
    } catch {
      setAdminAccessToken(null)
      set({ admin: null, isAuthenticated: false, initializing: false })
    }
  },

  fetchMe: async () => {
    try {
      const { data } = await adminApi.get('/admin/auth/me')
      set({ admin: data, isAuthenticated: true })
    } catch {
      setAdminAccessToken(null)
      set({ admin: null, isAuthenticated: false })
    }
  },
}))
