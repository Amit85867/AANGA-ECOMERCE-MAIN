import axios from 'axios'

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

    if (err.response?.status === 403 || (err.response?.status === 401 && isAuthCall)) {
      setAdminAccessToken(null)
      if (!original?.url?.includes('/admin/auth/login')) {
        window.location.href = '/admin/login'
      }
    }
    return Promise.reject(err)
  },
)

export default adminApi
