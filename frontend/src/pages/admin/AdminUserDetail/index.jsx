import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { inr, notifyError } from '@/components/admin/helpers'
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

      <h1 className="mb-6 text-2xl font-semibold text-gray-900">{user.full_name}</h1>

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
