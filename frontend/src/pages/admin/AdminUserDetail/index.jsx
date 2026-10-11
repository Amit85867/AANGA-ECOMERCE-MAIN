import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/admin/controls'
import { RETURN_STATUS_TONE, formatDate, humanize, inr, notifyError } from '@/components/admin/helpers'
import { IconArrowLeft } from '@tabler/icons-react'

export default function AdminUserDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchUser = () => {
    setError(null)
    return adminApi
      .get(`/admin/users/${id}`)
      .then((r) => setUser(r.data))
      .catch((err) =>
        setError(
          err.response?.status === 404
            ? 'This customer does not exist.'
            : err.response?.data?.error || 'Could not load this customer.',
        ),
      )
      .finally(() => setLoading(false))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchUser() }, [id])

  const toggle = async (field, value) => {
    try {
      await adminApi.patch(`/admin/users/${id}`, { [field]: value })
      toast.success('Customer updated.')
      fetchUser()
    } catch (err) {
      notifyError(err, 'Could not update this customer.')
    }
  }

  if (loading) return <TableSkeleton rows={5} columns={3} />
  if (error || !user) return <ErrorState message={error || 'This customer does not exist.'} onRetry={fetchUser} />

  return (
    <div>
      <button onClick={() => navigate('/admin/users')} className="mb-4 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
        <IconArrowLeft size={16} /> Back to users
      </button>

      <h1 className="mb-6 text-2xl font-semibold text-gray-900">
        {user.full_name}
        {user.is_demo && <span className="ml-3 align-middle"><Badge tone="purple">Demo customer</Badge></span>}
      </h1>

      <dl className="mb-6 grid gap-4 sm:grid-cols-3">
        {[
          ['Lifetime spend', inr(user.lifetime_spend || 0)],
          ['Orders', user.order_count ?? 0],
          ['Returns', (user.returns || []).length],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white px-6 py-4">
            <dt className="text-xs text-gray-500">{label}</dt>
            <dd className="mt-1 text-2xl font-semibold tabular-nums text-gray-900">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Profile</h3>
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-gray-400">Email</dt><dd className="text-gray-900">{user.email}</dd></div>
              <div><dt className="text-gray-400">Phone</dt><dd className="text-gray-900">{user.phone || '-'}</dd></div>
              <div><dt className="text-gray-400">Account Type</dt><dd className="capitalize text-gray-900">{user.account_type}</dd></div>
              <div><dt className="text-gray-400">Auth Provider</dt><dd className="capitalize text-gray-900">{user.auth_provider}</dd></div>
              <div><dt className="text-gray-400">Joined</dt><dd className="text-gray-900">{new Date(user.created_at).toLocaleDateString('en-IN')}</dd></div>
            </dl>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Recent Orders</h3>
            {user.recent_orders.length === 0 ? (
              <p className="text-sm text-gray-400">No orders</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-gray-400">
                    <th className="pb-2 font-medium">Order</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Amount</th>
                    <th className="pb-2 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {user.recent_orders.map((o) => (
                    <tr key={o.id} className="border-b border-gray-50">
                      <td className="py-2 font-medium text-gray-900">{o.order_number}</td>
                      <td className="py-2 capitalize text-gray-500">{o.status.replace(/_/g, ' ')}</td>
                      <td className="py-2">{inr(o.total_amount)}</td>
                      <td className="py-2 text-gray-400">{new Date(o.placed_at).toLocaleDateString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Returns</h3>
            {(user.returns || []).length === 0 ? <p className="text-sm text-gray-500">No returns</p> : (
              <ul className="divide-y divide-gray-100 text-sm">
                {user.returns.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-3 py-2">
                    <Link to={`/admin/orders/${r.order_id}`} className="font-medium text-gray-900 hover:underline">{r.order_number}</Link>
                    <span className="text-gray-600">{humanize(r.reason)}</span>
                    <Badge tone={RETURN_STATUS_TONE[r.status]}>{humanize(r.status)}</Badge>
                    <span className="ml-auto text-xs text-gray-500">{formatDate(r.requested_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Reviews</h3>
            {(user.reviews || []).length === 0 ? <p className="text-sm text-gray-500">No reviews</p> : (
              <ul className="divide-y divide-gray-100 text-sm">
                {user.reviews.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-3 py-2">
                    <span className="font-medium text-gray-900">{r.product_name}</span>
                    <span className="text-gray-600">{r.rating} out of 5{r.title ? ` — ${r.title}` : ''}</span>
                    <span className="ml-auto text-xs text-gray-500">{formatDate(r.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Addresses</h3>
            {user.addresses.length === 0 ? (
              <p className="text-sm text-gray-400">No addresses</p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {user.addresses.map((a) => (
                  <div key={a.id} className="rounded-lg border border-gray-100 p-3 text-sm">
                    <div className="mb-1 font-medium text-gray-900">{a.label} {a.is_default && <span className="text-xs text-gold">(Default)</span>}</div>
                    <div className="text-gray-600">{a.full_name}</div>
                    <div className="text-gray-500">{a.city}, {a.state} {a.pin_code}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Actions</h3>
            <div className="space-y-3">
              <button
                onClick={() => toggle('is_active', !user.is_active)}
                className={`w-full rounded-lg px-4 py-2.5 text-sm font-medium ${user.is_active ? 'bg-red-50 text-red-600 hover:bg-red-100' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}
              >
                {user.is_active ? 'Block User' : 'Activate User'}
              </button>
              <button
                onClick={() => toggle('is_verified', !user.is_verified)}
                className={`w-full rounded-lg px-4 py-2.5 text-sm font-medium ${user.is_verified ? 'bg-gray-50 text-gray-600 hover:bg-gray-100' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}
              >
                {user.is_verified ? 'Unverify' : 'Mark Verified'}
              </button>
              <button
                onClick={() => toggle('is_demo', !user.is_demo)}
                className="w-full rounded-lg bg-gray-50 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
              >
                {user.is_demo ? 'This is a real customer' : 'Mark as demo customer'}
              </button>
              <select
                value={user.account_type}
                onChange={(e) => toggle('account_type', e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm"
              >
                <option value="retail">Retail</option>
                <option value="wholesale">Wholesale</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
