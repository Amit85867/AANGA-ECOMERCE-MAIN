import { previewToken } from '@/services/preview'

/*
 * Answers to requests that index.html started before the app's code loaded.
 *
 * `takeEarly(key)` hands one over exactly once — a later visit to the same
 * page must ask the server again, not reuse a stale answer — and resolves to
 * null when there is nothing (or the early request failed), in which case the
 * caller makes the request normally.
 */
export function takeEarly(key) {
  if (previewToken()) return null
  const store = window.__early
  const promise = store?.[key]
  if (!promise) return null
  store[key] = null
  return promise
}
