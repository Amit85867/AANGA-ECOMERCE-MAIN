import { useEffect } from 'react'
import { create } from 'zustand'
import apiClient from '@/services/apiClient'
import { takeEarly } from '@/services/early'
import { previewToken } from '@/services/preview'

/*
 * What the owner controls about the storefront's shape: homepage section
 * order, the two menus, and the campaign that is live right now.
 *
 * One request (/content/layout). The last answer is kept in localStorage so a
 * returning visitor's page is laid out correctly from the first paint, and
 * the built-in defaults below match the server's, so a first-time visitor
 * normally sees no reordering either.
 *
 * A campaign starts and ends by the clock, not by anyone pressing a button,
 * so an open page has to notice by itself: the server says when the next
 * change is due (`next_change_at`) and the page asks again at that moment,
 * and otherwise once a minute while it is visible. When the campaign changes,
 * `epoch` goes up and everything that shows campaign-dependent data (prices,
 * hero slides, the announcement) loads again.
 */
const CACHE_KEY = 'aanga.layout.v1'

const DEFAULT_HOME = [
  'hero', 'category_strip', 'features', 'category_tiles', 'featured', 'promo', 'testimonials', 'newsletter',
].map((key) => ({ key, title: null, subtitle: null }))

const readCache = () => {
  if (previewToken()) return null
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) || 'null')
  } catch {
    return null
  }
}

const cached = readCache()
// A cached campaign may be over by now: trust the clock, not the cache.
const stillLive = (c) => (c && new Date(c.ends_at).getTime() > Date.now() ? c : null)

let timer = null
let polling = false

export const useLayoutStore = create((set, get) => ({
  homepage: cached?.homepage || DEFAULT_HOME,
  navigation: cached?.navigation || { header: [], footer: [] },
  campaign: stillLive(cached?.campaign),
  loaded: false,
  epoch: 0,

  load: async () => {
    try {
      const early = takeEarly('layout')
      const data = (early && !previewToken() ? await early : null)
        ?? (await apiClient.get('/content/layout')).data
      const before = get().campaign?.id ?? null
      const after = data.campaign?.id ?? null
      set((state) => ({
        homepage: data.homepage?.length ? data.homepage : DEFAULT_HOME,
        navigation: data.navigation || state.navigation,
        campaign: data.campaign || null,
        loaded: true,
        // Everything on the page was fetched moments ago on the first answer,
        // so only a change seen later means "load again".
        epoch: state.loaded && before !== after ? state.epoch + 1 : state.epoch,
      }))
      if (!previewToken()) {
        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify({
            homepage: data.homepage, navigation: data.navigation, campaign: data.campaign,
          }))
        } catch { /* private mode: the page still works, just without the head start */ }
      }

      clearTimeout(timer)
      if (data.next_change_at) {
        // Measured on the server's clock so a wrong clock on the phone does not matter.
        const wait = new Date(data.next_change_at).getTime() - new Date(data.server_time).getTime()
        if (wait > 0 && wait < 2 ** 31 - 2000) timer = setTimeout(() => get().load(), wait + 1500)
      }
    } catch {
      set({ loaded: true })
    }
  },

  start: () => {
    get().load()
    if (polling) return
    polling = true
    setInterval(() => { if (!document.hidden) get().load() }, 60_000)
    document.addEventListener('visibilitychange', () => { if (!document.hidden) get().load() })
  },
}))

/** Start watching the layout (once, from the storefront shell). */
export function useLayoutWatcher() {
  const start = useLayoutStore((s) => s.start)
  useEffect(() => { start() }, [start])
}

/** Changes whenever a campaign starts or ends: put it in an effect's deps to reload. */
export const useCampaignEpoch = () => useLayoutStore((s) => s.epoch)
export const useCampaign = () => useLayoutStore((s) => s.campaign)
