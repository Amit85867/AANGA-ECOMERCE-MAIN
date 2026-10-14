/**
 * Where the API lives.
 *
 * The storefront and the API are on different hosts in production
 * (https://example.com and https://api.example.com), so the build is told the
 * API's origin with VITE_API_BASE_URL. With nothing set we fall back to a
 * same-origin `/api`, which is what local development uses through the Vite
 * proxy.
 *
 * VITE_API_BASE_URL is accepted with or without the trailing `/api`, because
 * both readings are natural and getting it wrong produces 404s on every call
 * that are tedious to trace back to one missing path segment:
 *
 *   https://api.example.com        -> https://api.example.com/api
 *   https://api.example.com/api    -> https://api.example.com/api
 *   https://api.example.com/api/   -> https://api.example.com/api
 */
export function resolveApiBase(raw) {
  const value = (raw || '').trim().replace(/\/+$/, '')
  if (!value) return '/api'
  return /\/api$/.test(value) ? value : `${value}/api`
}

export const API_BASE_URL = resolveApiBase(import.meta.env.VITE_API_BASE_URL)
