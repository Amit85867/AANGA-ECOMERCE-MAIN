import { create } from 'zustand'
import apiClient, { setAccessToken, refreshAccessToken } from '@/services/apiClient'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'

/*
 * No tokens are persisted in localStorage. The access token lives in memory
 * (see apiClient) and the refresh token is an httpOnly cookie the browser
 * sends automatically, so a page reload restores the session via
 * restoreSession() rather than by reading a stored token.
 */
export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  loading: false,
  // True until we've tried to restore an existing session on first load.
  initializing: true,
  error: null,

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  clearError: () => set({ error: null }),

  // Shared post-sign-in handling.
  _onAuthSuccess: (data) => {
    setAccessToken(data.access_token)
    set({ user: data.user, isAuthenticated: true, loading: false })
    useCartStore.getState().fetchCart()
    return data
  },

  // Email/Password Register
  register: async ({ full_name, email, phone, password, account_type }) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/register', {
        full_name, email, phone, password, account_type,
      })
      return get()._onAuthSuccess(data)
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.errors || 'Registration failed'
      set({ loading: false, error: typeof msg === 'string' ? msg : JSON.stringify(msg) })
      throw err
    }
  },

  // Email/Password Login
  login: async ({ email, password }) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/login', { email, password })
      return get()._onAuthSuccess(data)
    } catch (err) {
      const msg =
        err.response?.status === 429
          ? 'Too many attempts. Please wait a few minutes and try again.'
          : err.response?.data?.error || 'Invalid email or password'
      set({ loading: false, error: msg })
      throw err
    }
  },

  // Google OAuth
  googleAuth: async (idToken) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/google', { access_token: idToken })
      return get()._onAuthSuccess(data)
    } catch (err) {
      const msg = err.response?.data?.error || 'Google sign-in failed'
      set({ loading: false, error: msg })
      throw err
    }
  },

  // Phone OTP - Send
  sendOTP: async (phone) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/otp/send', { phone })
      set({ loading: false })
      return data
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to send OTP'
      set({ loading: false, error: msg })
      throw err
    }
  },

  // Phone OTP - Verify
  verifyOTP: async ({ phone, code, full_name }) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/otp/verify', { phone, code, full_name })
      return get()._onAuthSuccess(data)
    } catch (err) {
      const msg = err.response?.data?.error || 'OTP verification failed'
      set({ loading: false, error: msg })
      throw err
    }
  },

  /*
   * Called once on app start. Exchanges the httpOnly refresh cookie for a new
   * access token; if there is no valid cookie the user is simply signed out.
   */
  restoreSession: async () => {
    try {
      await refreshAccessToken()
      const { data } = await apiClient.get('/auth/me')
      set({ user: data, isAuthenticated: true, initializing: false })
      useCartStore.getState().fetchCart()
    } catch {
      setAccessToken(null)
      set({ user: null, isAuthenticated: false, initializing: false })
    }
  },

  // Refresh the cached user profile.
  fetchMe: async () => {
    try {
      const { data } = await apiClient.get('/auth/me')
      set({ user: data, isAuthenticated: true })
    } catch {
      setAccessToken(null)
      set({ user: null, isAuthenticated: false })
    }
  },

  // Logout — clears the refresh cookie server-side too.
  logout: async () => {
    try {
      await apiClient.post('/auth/logout')
    } catch {
      // Even if the call fails, drop local state.
    }
    setAccessToken(null)
    set({ user: null, isAuthenticated: false, error: null })
    useCartStore.getState().clearLocal()
    useWishlistStore.getState().clearLocal()
  },
}))
