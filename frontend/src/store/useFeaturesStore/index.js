import { useEffect } from 'react'
import { create } from 'zustand'
import apiClient from '@/services/apiClient'

/*
 * Which optional parts of the store are switched on (online payment, delivery
 * check, Google and phone sign-in). The storefront hides what is not
 * configured rather than offering it and showing an error.
 *
 * Everything defaults to off: until the answer arrives — or if it never does —
 * the page shows only what is certain to work.
 */
// (Cash on delivery is the exception: it is on unless the owner switches it off.)
const OFF = { online_payments: false, delivery_check: false, google_login: false, phone_login: false, cash_on_delivery: true }

export const useFeaturesStore = create((set, get) => ({
  features: OFF,
  loaded: false,
  loading: false,

  fetchFeatures: async () => {
    if (get().loaded || get().loading) return
    set({ loading: true })
    try {
      const { data } = await apiClient.get('/cms/features-available')
      set({ features: { ...OFF, ...data }, loaded: true, loading: false })
    } catch {
      set({ loaded: true, loading: false })
    }
  },
}))

export function useFeatures() {
  const features = useFeaturesStore((s) => s.features)
  const loaded = useFeaturesStore((s) => s.loaded)
  const fetchFeatures = useFeaturesStore((s) => s.fetchFeatures)

  useEffect(() => { fetchFeatures() }, [fetchFeatures])

  return { ...features, loaded }
}
