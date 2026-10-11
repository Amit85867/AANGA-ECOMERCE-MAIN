import axios from 'axios'
import { describeApiError } from '@/utils/apiError'
import { previewToken } from '@/services/preview'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  // Required so the httpOnly refresh cookie is sent to the API.
  withCredentials: true,
})

/*
 * The access token is deliberately kept in memory only — never in
 * localStorage — so an XSS payload cannot read it. It is short-lived (15 min)
 * and silently renewed from the httpOnly refresh cookie, which JavaScript
 * cannot touch at all.
 */
let accessToken = null

export const setAccessToken = (token) => {
  accessToken = token || null
}
export const getAccessToken = () => accessToken

apiClient.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  // Campaign preview (admin only): see services/preview.
  if (previewToken()) config.headers['X-Campaign-Preview'] = previewToken()
  return config
})

const readCookie = (name) =>
  document.cookie
    .split('; ')
    .find((c) => c.startsWith(`${name}=`))
    ?.split('=')[1]

// Collapse concurrent 401s into a single refresh request.
let refreshPromise = null

export const refreshAccessToken = () => {
  if (!refreshPromise) {
    const csrf = readCookie('csrf_refresh_token')
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh`, null, {
        withCredentials: true,
        headers: csrf ? { 'X-CSRF-TOKEN': decodeURIComponent(csrf) } : {},
      })
      .then(({ data }) => {
        setAccessToken(data.access_token)
        return data.access_token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const isAuthCall =
      original?.url?.includes('/auth/refresh') || original?.url?.includes('/auth/login')

    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true
      try {
        const token = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${token}`
        return apiClient(original)
      } catch {
        setAccessToken(null)
      }
    }
    // The store was closed while this tab was open. Announced as an event
    // rather than by importing the settings store, which itself imports this
    // client.
    if (error.response?.status === 503 && error.response.data?.maintenance) {
      window.dispatchEvent(
        new CustomEvent('aanga:maintenance', { detail: error.response.data.error }),
      )
    }
    return Promise.reject(describeApiError(error))
  },
)

export default apiClient
