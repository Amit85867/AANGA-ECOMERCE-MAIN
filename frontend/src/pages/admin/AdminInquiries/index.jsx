import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'

const INQUIRY_STATUSES = ['new', 'contacted', 'qualified', 'converted', 'rejected']
const STATUS_COLORS = {
  new: 'bg-blue-100 text-blue-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  qualified: 'bg-indigo-100 text-indigo-700',
  converted: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
}

export default function AdminInquiries() {
  const [inquiries, setInquiries] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)

  const fetch = (pg = 1) => {
    setLoading(true)
    const params = { page: pg, per_page: 20 }
    if (statusFilter) params.status = statusFilter
    adminApi.get('/admin/wholesale-inquiries', { params })
      .then((r) => {
        setInquiries(r.data.inquiries)
        setPage(r.data.page)
        setPages(r.data.pages)
        setTotal(r.data.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [statusFilter])

  const updateStatus = async (id, status) => {
    await adminApi.patch(`/admin/wholesale-inquiries/${id}`, { status })
    fetch(page)
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Wholesale Inquiries ({total})</h1>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none">
          <option value="">All statuses</option>
          {INQUIRY_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : inquiries.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No inquiries</div>
      ) : (
        <div className="space-y-3">
          {inquiries.map((inq) => (
            <div key={inq.id} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-gray-900">{inq.shop_name}</div>
                  <div className="text-sm text-gray-500">{inq.owner_name} &middot; {inq.phone} &middot; {inq.email}</div>
                  <div className="text-sm text-gray-400">{inq.city}, {inq.state} &middot; GST: {inq.gst_number || '-'}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[inq.status] || 'bg-gray-100 text-gray-600'}`}>
                    {inq.status}
                  </span>
                  <select
                    value={inq.status}
                    onChange={(e) => updateStatus(inq.id, e.target.value)}
                    className="rounded border border-gray-200 px-2 py-1 text-xs"
                  >
                    {INQUIRY_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={() => setExpanded(expanded === inq.id ? null : inq.id)} className="mt-2 text-xs text-[#C8963E] hover:underline">
                {expanded === inq.id ? 'Less' : 'More details'}
              </button>
              {expanded === inq.id && (
                <div className="mt-3 grid gap-2 border-t border-gray-100 pt-3 text-sm sm:grid-cols-2">
                  <div><span className="text-gray-400">Volume:</span> <span className="text-gray-700">{inq.monthly_volume_range.replace(/_/g, ' ')}</span></div>
                  <div><span className="text-gray-400">Categories:</span> <span className="text-gray-700">{inq.categories_interest?.join(', ') || '-'}</span></div>
                  <div><span className="text-gray-400">Notes:</span> <span className="text-gray-700">{inq.notes || '-'}</span></div>
                  <div><span className="text-gray-400">Submitted:</span> <span className="text-gray-700">{new Date(inq.submitted_at).toLocaleDateString('en-IN')}</span></div>
                </div>
              )}
            </div>
          ))}

          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                <button key={p} onClick={() => fetch(p)} className={`h-9 min-w-9 rounded-lg px-3 text-sm ${p === page ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'}`}>
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
