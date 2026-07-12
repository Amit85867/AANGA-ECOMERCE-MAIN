import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { IconSearch, IconEye } from '@tabler/icons-react'

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  packed: 'bg-indigo-100 text-indigo-700',
  shipped: 'bg-purple-100 text-purple-700',
  out_for_delivery: 'bg-cyan-100 text-cyan-700',
  delivered: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
  return_requested: 'bg-orange-100 text-orange-700',
  returned: 'bg-gray-100 text-gray-600',
}

const STATUSES = ['', 'pending', 'confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'return_requested', 'returned']

export default function AdminOrders() {
  const [orders, setOrders] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchOrders = useCallback(
    (pg = 1) => {
      setLoading(true)
      const params = { page: pg, per_page: 20 }
      if (search) params.q = search
      if (status) params.status = status
      adminApi
        .get('/admin/orders', { params })
        .then((r) => {
          setOrders(r.data.orders)
          setPage(r.data.page)
          setPages(r.data.pages)
          setTotal(r.data.total)
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    },
    [search, status],
  )

  useEffect(() => { fetchOrders() }, [status])

  const handleSearch = (e) => {
    e.preventDefault()
    fetchOrders(1)
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Orders ({total})</h1>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <form onSubmit={handleSearch} className="relative flex-1">
          <IconSearch size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by order number..."
            className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-[#C8963E]"
          />
        </form>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none"
        >
          <option value="">All statuses</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : orders.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No orders found</div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                  <th className="px-6 py-3 font-medium">Order</th>
                  <th className="px-6 py-3 font-medium">Customer</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Payment</th>
                  <th className="px-6 py-3 font-medium">Amount</th>
                  <th className="px-6 py-3 font-medium">Date</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id} className="border-b border-gray-50 last:border-0">
                    <td className="px-6 py-3 font-medium text-gray-900">{o.order_number}</td>
                    <td className="px-6 py-3">
                      <div className="text-gray-900">{o.customer_name}</div>
                      <div className="text-xs text-gray-400">{o.customer_email}</div>
                    </td>
                    <td className="px-6 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[o.status] || 'bg-gray-100 text-gray-600'}`}>
                        {o.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${o.payment_status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {o.payment_status}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-gray-700">₹{o.total_amount.toLocaleString('en-IN')}</td>
                    <td className="px-6 py-3 text-gray-400">{new Date(o.placed_at).toLocaleDateString('en-IN')}</td>
                    <td className="px-6 py-3">
                      <Link to={`/admin/orders/${o.id}`} className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
                        <IconEye size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                <button key={p} onClick={() => fetchOrders(p)} className={`h-9 min-w-9 rounded-lg px-3 text-sm ${p === page ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'}`}>
                  {p}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
