/* Helpers shared by the owner-dashboard screens (components live in kit.jsx). */
import { useCallback, useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'

export const btnPrimary =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark disabled:cursor-not-allowed disabled:opacity-60'
export const btnGhost =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60'
export const btnDanger =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-2.5 text-sm text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60'
export const cardCls = 'rounded-xl border border-gray-200 bg-white p-6'

/* First message for a field from a 422 body: {errors: {field: ["…"]}}. */
export const fieldErrors = (err) => {
  const errors = err?.response?.data?.errors
  if (!errors || typeof errors !== 'object') return {}
  return Object.fromEntries(Object.entries(errors).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)]))
}

/* GET a URL into state, with loading / error and a reload(). */
export function useLoad(url, params) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const key = JSON.stringify(params || {})
  const reload = useCallback(() => {
    if (!url) return Promise.resolve()
    setState((s) => ({ ...s, loading: true, error: null }))
    return adminApi.get(url, { params: JSON.parse(key) })
      .then((r) => setState({ data: r.data, loading: false, error: null }))
      .catch((err) => setState({
        data: null, loading: false,
        error: err.response?.data?.error || 'Could not load this page. Check your connection and try again.',
      }))
  }, [url, key])
  useEffect(() => { reload() }, [reload])
  return { ...state, reload, setData: (data) => setState((s) => ({ ...s, data })) }
}

export const moveItem = (list, from, to) => {
  const next = [...list]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

/* ── Dates in Indian time ────────────────────────────────────
   A campaign's start and end are always entered and shown in IST, whatever
   the time zone of the computer the owner happens to be using. */
const IST_OFFSET_MIN = 330

export function toIstInput(iso) {
  if (!iso) return ''
  const shifted = new Date(new Date(iso).getTime() + IST_OFFSET_MIN * 60_000)
  return shifted.toISOString().slice(0, 16)          // "2026-10-11T18:30"
}

export const fromIstInput = (value) => (value ? `${value}:00+05:30` : null)

export const formatIst = (iso) =>
  iso
    ? `${new Date(iso).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' })} IST`
    : '—'

export async function uploadImage(file, extra = {}) {
  const body = new FormData()
  body.append('file', file)
  for (const [k, v] of Object.entries(extra)) if (v) body.append(k, v)
  const { data } = await adminApi.post('/admin/media', body, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}
