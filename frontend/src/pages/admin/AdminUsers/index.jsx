import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { IconSearch, IconEye } from '@tabler/icons-react'

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchUsers = useCallback(
    (pg = 1) => {
      setLoading(true)
      const params = { page: pg, per_page: 20 }
      if (search) params.q = search
      adminApi
        .get('/admin/users', { params })
        .then((r) => {
          setUsers(r.data.users)
          setPage(r.data.page)
          setPages(r.data.pages)
          setTotal(r.data.total)
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    },
    [search],
  )

  useEffect(() => { fetchUsers() }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    fetchUsers(1)
  }

  const toggleActive = async (userId, current) => {
    await adminApi.patch(`/admin/users/${userId}`, { is_active: !current })
    fetchUsers(page)
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Users ({total})</h1>

      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <div className="relative flex-1">
          <IconSearch size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name, email, or phone..." className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-[#C8963E]" />
        </div>
        <button type="submit" className="rounded-lg bg-gray-900 px-4 text-sm text-white hover:bg-gray-800">Search</button>
      </form>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : users.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No users found</div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                  <th className="px-6 py-3 font-medium">User</th>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Auth</th>
                  <th className="px-6 py-3 font-medium">Orders</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Joined</th>
                  <th className="px-6 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-gray-50 last:border-0">
                    <td className="px-6 py-3">
                      <div className="font-medium text-gray-900">{u.full_name}</div>
                      <div className="text-xs text-gray-400">{u.email}</div>
                    </td>
                    <td className="px-6 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${u.account_type === 'wholesale' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                        {u.account_type}
                      </span>
                    </td>
                    <td className="px-6 py-3 capitalize text-gray-500">{u.auth_provider}</td>
                    <td className="px-6 py-3 text-gray-700">{u.order_count}</td>
                    <td className="px-6 py-3">
                      <button
                        onClick={() => toggleActive(u.id, u.is_active)}
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}
                      >
                        {u.is_active ? 'Active' : 'Blocked'}
                      </button>
                    </td>
                    <td className="px-6 py-3 text-gray-400">{new Date(u.created_at).toLocaleDateString('en-IN')}</td>
                    <td className="px-6 py-3">
                      <Link to={`/admin/users/${u.id}`} className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
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
                <button key={p} onClick={() => fetchUsers(p)} className={`h-9 min-w-9 rounded-lg px-3 text-sm ${p === page ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'}`}>
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
