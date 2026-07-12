import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'

const MSG_STATUSES = ['unread', 'read', 'replied', 'closed']
const STATUS_COLORS = {
  unread: 'bg-red-100 text-red-700',
  read: 'bg-blue-100 text-blue-700',
  replied: 'bg-green-100 text-green-700',
  closed: 'bg-gray-100 text-gray-500',
}

export default function AdminMessages() {
  const [messages, setMessages] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)

  const fetch = (pg = 1) => {
    setLoading(true)
    const params = { page: pg, per_page: 20 }
    if (statusFilter) params.status = statusFilter
    adminApi.get('/admin/contact-messages', { params })
      .then((r) => {
        setMessages(r.data.messages)
        setPage(r.data.page)
        setPages(r.data.pages)
        setTotal(r.data.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [statusFilter])

  const updateStatus = async (id, status) => {
    await adminApi.patch(`/admin/contact-messages/${id}`, { status })
    fetch(page)
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Contact Messages ({total})</h1>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none">
          <option value="">All statuses</option>
          {MSG_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : messages.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No messages</div>
      ) : (
        <div className="space-y-3">
          {messages.map((msg) => (
            <div key={msg.id} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-gray-900">{msg.name}</div>
                  <div className="text-sm text-gray-500">{msg.email} {msg.phone && `· ${msg.phone}`}</div>
                  <div className="mt-1 inline-block rounded bg-gray-100 px-2 py-0.5 text-xs capitalize text-gray-600">{msg.subject.replace(/_/g, ' ')}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[msg.status]}`}>
                    {msg.status}
                  </span>
                  <select
                    value={msg.status}
                    onChange={(e) => updateStatus(msg.id, e.target.value)}
                    className="rounded border border-gray-200 px-2 py-1 text-xs"
                  >
                    {MSG_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <p className="mt-3 text-sm text-gray-700">{msg.message}</p>
              <div className="mt-2 text-xs text-gray-400">
                {new Date(msg.sent_at).toLocaleString('en-IN')}
                {msg.replied_at && <span> &middot; Replied {new Date(msg.replied_at).toLocaleString('en-IN')}</span>}
              </div>
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
