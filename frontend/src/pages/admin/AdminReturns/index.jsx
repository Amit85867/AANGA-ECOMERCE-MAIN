import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'

const RETURN_STATUSES = [
  'requested', 'approved', 'pickup_scheduled',
  'picked_up', 'inspected', 'resolved', 'rejected',
]
const RESOLUTION_TYPES = ['refund', 'exchange', 'store_credit']

const STATUS_COLORS = {
  requested: 'bg-blue-100 text-blue-700',
  approved: 'bg-indigo-100 text-indigo-700',
  pickup_scheduled: 'bg-yellow-100 text-yellow-700',
  picked_up: 'bg-yellow-100 text-yellow-700',
  inspected: 'bg-purple-100 text-purple-700',
  resolved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
}

const label = (s) => s.replace(/_/g, ' ')

export default function AdminReturns() {
  const [returns, setReturns] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  // Per-return draft of the resolution fields, so a refund amount can be typed
  // before it is submitted alongside the status change.
  const [drafts, setDrafts] = useState({})

  const fetch = (pg = 1) => {
    setLoading(true)
    const params = { page: pg, per_page: 20 }
    if (statusFilter) params.status = statusFilter
    adminApi.get('/admin/returns', { params })
      .then((r) => {
        setReturns(r.data.returns)
        setPage(r.data.page)
        setPages(r.data.pages)
        setTotal(r.data.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [statusFilter])

  const draftFor = (ret) => drafts[ret.id] ?? {
    resolution_type: ret.resolution_type || '',
    refund_amount: ret.refund_amount ?? '',
  }

  const setDraft = (ret, patch) =>
    setDrafts((d) => ({ ...d, [ret.id]: { ...draftFor(ret), ...patch } }))

  const update = async (ret, status) => {
    const draft = draftFor(ret)
    const payload = { status }
    if (draft.resolution_type) payload.resolution_type = draft.resolution_type
    if (draft.refund_amount !== '' && draft.refund_amount !== null) {
      payload.refund_amount = Number(draft.refund_amount)
    }
    await adminApi.patch(`/admin/returns/${ret.id}`, payload)
    setDrafts((d) => { const n = { ...d }; delete n[ret.id]; return n })
    fetch(page)
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Returns ({total})</h1>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none"
        >
          <option value="">All statuses</option>
          {RETURN_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : returns.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No return requests</div>
      ) : (
        <div className="space-y-3">
          {returns.map((ret) => {
            const draft = draftFor(ret)
            return (
              <div key={ret.id} className="rounded-xl border border-gray-200 bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-medium text-gray-900">{ret.product_name}</div>
                    <div className="text-sm text-gray-500">
                      {ret.customer_name} &middot; {label(ret.reason)}
                    </div>
                    <div className="text-sm text-gray-400">
                      Requested {new Date(ret.requested_at).toLocaleDateString('en-IN')}
                      {ret.refund_amount != null && ` · Refund ₹${ret.refund_amount}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[ret.status] || 'bg-gray-100 text-gray-600'}`}>
                      {label(ret.status)}
                    </span>
                    <select
                      value={ret.status}
                      onChange={(e) => update(ret, e.target.value)}
                      className="rounded border border-gray-200 px-2 py-1 text-xs"
                    >
                      {RETURN_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
                    </select>
                  </div>
                </div>

                <button
                  onClick={() => setExpanded(expanded === ret.id ? null : ret.id)}
                  className="mt-2 text-xs text-[#C8963E] hover:underline"
                >
                  {expanded === ret.id ? 'Less' : 'More details'}
                </button>

                {expanded === ret.id && (
                  <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 text-sm">
                    <div>
                      <span className="text-gray-400">Customer note:</span>{' '}
                      <span className="text-gray-700">{ret.description || '-'}</span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div>
                        <span className="text-gray-400">Resolved:</span>{' '}
                        <span className="text-gray-700">
                          {ret.resolved_at ? new Date(ret.resolved_at).toLocaleDateString('en-IN') : '-'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Order item:</span>{' '}
                        <span className="text-gray-700">#{ret.order_item_id}</span>
                      </div>
                    </div>

                    {/* Resolution is set here, then applied with the status change
                        above — the API accepts all three in one PATCH. */}
                    <div className="flex flex-wrap items-end gap-3 border-t border-gray-100 pt-3">
                      <label className="flex flex-col gap-1">
                        <span className="text-xs text-gray-400">Resolution</span>
                        <select
                          value={draft.resolution_type}
                          onChange={(e) => setDraft(ret, { resolution_type: e.target.value })}
                          className="rounded border border-gray-200 px-2 py-1.5 text-xs"
                        >
                          <option value="">Not set</option>
                          {RESOLUTION_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
                        </select>
                      </label>
                      <label className="flex flex-col gap-1">
                        <span className="text-xs text-gray-400">Refund amount (₹)</span>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={draft.refund_amount}
                          onChange={(e) => setDraft(ret, { refund_amount: e.target.value })}
                          className="w-32 rounded border border-gray-200 px-2 py-1.5 text-xs"
                        />
                      </label>
                      <button
                        onClick={() => update(ret, 'resolved')}
                        className="rounded-lg bg-gray-900 px-4 py-2 text-xs font-medium text-white hover:bg-gray-800"
                      >
                        Mark resolved
                      </button>
                      <button
                        onClick={() => update(ret, 'rejected')}
                        className="rounded-lg border border-gray-200 px-4 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => fetch(p)}
                  className={`h-9 min-w-9 rounded-lg px-3 text-sm ${p === page ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
