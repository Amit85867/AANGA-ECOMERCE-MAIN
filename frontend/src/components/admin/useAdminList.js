import { useCallback, useEffect, useRef, useState } from 'react'
import adminApi from '@/services/adminApi'

/*
 * Loads one admin list: owns loading / error / page state so every list page
 * behaves the same way and none of them swallows a failed request.
 *
 *   const list = useAdminList('/admin/coupons', 'coupons', { q: search })
 *   list.rows, list.loading, list.error, list.reload, list.page, list.setPage
 *
 * `params` are the filters. Changing any of them goes back to page 1, because
 * page 4 of the old filter is meaningless under the new one.
 */
export default function useAdminList(url, key, params = {}, { perPage = 20 } = {}) {
  const [rows, setRows] = useState([])
  const [meta, setMeta] = useState({ page: 1, pages: 1, total: 0 })
  const [extra, setExtra] = useState({})
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const filterKey = JSON.stringify(params)
  const requestId = useRef(0)
  const lastFilterKey = useRef(filterKey)

  const load = useCallback(
    (pageToLoad) => {
      const id = ++requestId.current
      setLoading(true)
      setError(null)

      const clean = Object.fromEntries(
        Object.entries(JSON.parse(filterKey)).filter(([, v]) => v !== '' && v != null),
      )

      return adminApi
        .get(url, { params: { ...clean, page: pageToLoad, per_page: perPage } })
        .then(({ data }) => {
          // A slower, older response must not overwrite a newer one.
          if (id !== requestId.current) return
          const { [key]: list, page: p, pages, total, ...rest } = data
          setRows(list ?? [])
          setMeta({ page: p ?? 1, pages: pages ?? 1, total: total ?? (list?.length || 0) })
          setExtra(rest)
        })
        .catch((err) => {
          if (id !== requestId.current) return
          setError(err.response?.data?.error || 'Could not load this list. Check your connection and try again.')
        })
        .finally(() => {
          if (id === requestId.current) setLoading(false)
        })
    },
    [url, key, filterKey, perPage],
  )

  useEffect(() => {
    if (lastFilterKey.current !== filterKey) {
      lastFilterKey.current = filterKey
      if (page !== 1) {
        setPage(1) // re-runs this effect with page 1
        return
      }
    }
    load(page)
  }, [load, page, filterKey])

  return {
    rows,
    ...meta,
    extra,
    loading,
    error,
    setPage,
    reload: () => load(page),
    filtered: Object.values(params).some((v) => v !== '' && v != null),
  }
}
