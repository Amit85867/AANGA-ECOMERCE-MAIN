import { create } from 'zustand'
import apiClient from '@/services/apiClient'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  clearError: () => set({ error: null }),

  // Email/Password Register
  register: async ({ full_name, email, phone, password, account_type }) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/register', { full_name, email, phone, password, account_type })
      localStorage.setItem('aanga_token', data.access_token)
      localStorage.setItem('aanga_refresh', data.refresh_token)
      set({ user: data.user, isAuthenticated: true, loading: false })
      useCartStore.getState().fetchCart()
      return data
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
      localStorage.setItem('aanga_token', data.access_token)
      localStorage.setItem('aanga_refresh', data.refresh_token)
      set({ user: data.user, isAuthenticated: true, loading: false })
      useCartStore.getState().fetchCart()
      return data
    } catch (err) {
      const msg = err.response?.data?.error || 'Invalid email or password'
      set({ loading: false, error: msg })
      throw err
    }
  },

  // Google OAuth
  googleAuth: async (idToken) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post('/auth/google', { access_token: idToken })
      localStorage.setItem('aanga_token', data.access_token)
      localStorage.setItem('aanga_refresh', data.refresh_token)
      set({ user: data.user, isAuthenticated: true, loading: false })
      useCartStore.getState().fetchCart()
      return data
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
      localStorage.setItem('aanga_token', data.access_token)
      localStorage.setItem('aanga_refresh', data.refresh_token)
      set({ user: data.user, isAuthenticated: true, loading: false })
      useCartStore.getState().fetchCart()
      return data
    } catch (err) {
      const msg = err.response?.data?.error || 'OTP verification failed'
      set({ loading: false, error: msg })
      throw err
    }
  },

  // Fetch current user from token
  fetchMe: async () => {
    const token = localStorage.getItem('aanga_token')
    if (!token) return
    try {
      const { data } = await apiClient.get('/auth/me')
      set({ user: data, isAuthenticated: true })
      useCartStore.getState().fetchCart()
    } catch {
      localStorage.removeItem('aanga_token')
      localStorage.removeItem('aanga_refresh')
      set({ user: null, isAuthenticated: false })
    }
  },

  // Logout
  logout: () => {
    localStorage.removeItem('aanga_token')
    localStorage.removeItem('aanga_refresh')
    set({ user: null, isAuthenticated: false, error: null })
    useCartStore.getState().clearLocal()
    useWishlistStore.getState().clearLocal()
  },
}))
