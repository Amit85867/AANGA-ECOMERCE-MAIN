import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import {
  IconUsers,
  IconPackage,
  IconShoppingCart,
  IconCurrencyRupee,
  IconBuildingStore,
  IconMail,
} from '@tabler/icons-react'

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-3 flex items-center gap-3">
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon size={20} stroke={1.5} className="text-white" />
        </div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-gray-400">{sub}</div>}
    </div>
  )
}

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  packed: 'bg-indigo-100 text-indigo-700',
  shipped: 'bg-purple-100 text-purple-700',
  delivered: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi
      .get('/admin/dashboard/stats')
      .then((r) => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading)
    return <div className="py-20 text-center text-gray-400">Loading dashboard...</div>
  if (!stats) return <div className="py-20 text-center text-gray-400">Failed to load stats</div>

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Dashboard</h1>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          icon={IconUsers}
          label="Users"
          value={stats.users.total}
          sub={`+${stats.users.new_30d} last 30d`}
          color="bg-blue-500"
        />
        <StatCard
          icon={IconPackage}
          label="Products"
          value={stats.products.total}
          sub={`${stats.products.out_of_stock} out of stock`}
          color="bg-indigo-500"
        />
        <StatCard
          icon={IconShoppingCart}
          label="Orders"
          value={stats.orders.total}
          sub={`${stats.orders.pending} pending`}
          color="bg-purple-500"
        />
        <StatCard
          icon={IconCurrencyRupee}
          label="Revenue"
          value={`₹${stats.revenue.total.toLocaleString('en-IN')}`}
          sub={`₹${stats.revenue.last_30d.toLocaleString('en-IN')} last 30d`}
          color="bg-green-500"
        />
        <StatCard
          icon={IconBuildingStore}
          label="Inquiries"
          value={stats.pending_inquiries}
          sub="pending"
          color="bg-orange-500"
        />
        <StatCard
          icon={IconMail}
          label="Messages"
          value={stats.unread_messages}
          sub="unread"
          color="bg-red-500"
        />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="font-medium text-gray-900">Recent Orders</h2>
          <Link to="/admin/orders" className="text-sm text-[#C8963E] hover:underline">
            View all
          </Link>
        </div>
        {stats.recent_orders.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-gray-400">No orders yet</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                <th className="px-6 py-3 font-medium">Order</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Amount</th>
                <th className="px-6 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_orders.map((o) => (
                <tr key={o.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3 font-medium text-gray-900">
                    <Link to={`/admin/orders/${o.id}`} className="hover:text-[#C8963E]">
                      {o.order_number}
                    </Link>
                  </td>
                  <td className="px-6 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[o.status] || 'bg-gray-100 text-gray-600'}`}
                    >
                      {o.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-700">
                    ₹{o.total_amount.toLocaleString('en-IN')}
                  </td>
                  <td className="px-6 py-3 text-gray-400">
                    {new Date(o.placed_at).toLocaleDateString('en-IN')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
