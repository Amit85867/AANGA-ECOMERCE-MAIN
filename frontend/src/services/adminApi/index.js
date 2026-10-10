import axios from 'axios'
import { describeApiError } from '@/utils/apiError'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const adminApi = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  // Required so the httpOnly admin refresh cookie is sent.
  withCredentials: true,
})

/*
 * Same model as the storefront client: the admin access token lives in memory
 * only, and the long-lived refresh token is an httpOnly cookie scoped to
 * /api/admin/auth. Nothing is written to localStorage.
 */
let adminAccessToken = null

export const setAdminAccessToken = (token) => {
  adminAccessToken = token || null
}
export const getAdminAccessToken = () => adminAccessToken

adminApi.interceptors.request.use((config) => {
  if (adminAccessToken) config.headers.Authorization = `Bearer ${adminAccessToken}`
  return config
})

const readCookie = (name) =>
  document.cookie
    .split('; ')
    .find((c) => c.startsWith(`${name}=`))
    ?.split('=')[1]

let refreshPromise = null

export const refreshAdminAccessToken = () => {
  if (!refreshPromise) {
    const csrf = readCookie('csrf_admin_refresh')
    refreshPromise = axios
      .post(`${baseURL}/admin/auth/refresh`, null, {
        withCredentials: true,
        headers: csrf ? { 'X-CSRF-TOKEN': decodeURIComponent(csrf) } : {},
      })
      .then(({ data }) => {
        setAdminAccessToken(data.access_token)
        return data.access_token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

adminApi.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    const isAuthCall =
      original?.url?.includes('/admin/auth/refresh') || original?.url?.includes('/admin/auth/login')

    // A 401 may just mean the short-lived access token expired — try once to
    // renew it from the refresh cookie before giving up.
    if (err.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true
      try {
        const token = await refreshAdminAccessToken()
        original.headers.Authorization = `Bearer ${token}`
        return adminApi(original)
      } catch {
        setAdminAccessToken(null)
        window.location.href = '/admin/login'
        return Promise.reject(err)
      }
    }

    // A failed refresh means the session is over. A 403 does not: it means this
    // admin may not do this one thing (a staff admin on a master-only screen),
    // and signing them out for it would lose their work for no reason. The one
    // 403 that does end the session is a deactivated or deleted account.
    const accountGone =
      err.response?.status === 403 &&
      /not found or deactivated/i.test(err.response?.data?.error || '')
    const refreshFailed = err.response?.status === 401 && original?.url?.includes('/admin/auth/refresh')

    if (accountGone || refreshFailed) {
      setAdminAccessToken(null)
      window.location.href = '/admin/login'
    }
    return Promise.reject(describeApiError(err))
  },
)

export default adminApi
