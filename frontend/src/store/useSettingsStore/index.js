import { useEffect } from 'react'
import { create } from 'zustand'
import apiClient from '@/services/apiClient'

// Site-wide settings (key → value), fetched once and shared across the storefront.
export const useSettingsStore = create((set, get) => ({
  settings: {},
  loaded: false,
  loading: false,

  fetchSettings: async () => {
    if (get().loaded || get().loading) return
    await get().refreshSettings()
  },

  // Always asks the server — used to notice the store reopening after
  // maintenance, where the cached copy is exactly what must not be trusted.
  refreshSettings: async () => {
    if (get().loading) return
    set({ loading: true })
    try {
      const { data } = await apiClient.get('/cms/settings')
      set({ settings: data.settings || {}, loaded: true, loading: false })
    } catch {
      set({ loaded: true, loading: false })
    }
  },

  // An API call was refused because the store is closed for maintenance.
  setMaintenance: (message) =>
    set((state) => ({
      settings: {
        ...state.settings,
        maintenance_mode: 'true',
        ...(message ? { maintenance_message: message } : {}),
      },
    })),
}))

// Convenience hook: returns a getter s(key, fallback) and ensures settings load.
export function useSetting() {
  const settings = useSettingsStore((st) => st.settings)
  const fetchSettings = useSettingsStore((st) => st.fetchSettings)

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  return (key, fallback = '') => settings[key] || fallback
}
