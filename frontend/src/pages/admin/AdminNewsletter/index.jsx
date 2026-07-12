import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { IconTrash } from '@tabler/icons-react'

export default function AdminNewsletter() {
  const [subscribers, setSubscribers] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const fetch = (pg = 1) => {
    setLoading(true)
    adminApi.get('/admin/newsletter', { params: { page: pg, per_page: 50, active: 'true' } })
      .then((r) => {
        setSubscribers(r.data.subscribers)
        setPage(r.data.page)
        setPages(r.data.pages)
        setTotal(r.data.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [])

  const remove = async (id) => {
    if (!confirm('Remove this subscriber?')) return
    await adminApi.delete(`/admin/newsletter/${id}`)
    fetch(page)
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Newsletter Subscribers ({total})</h1>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : subscribers.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No subscribers</div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                  <th className="px-6 py-3 font-medium">Email</th>
                  <th className="px-6 py-3 font-medium">Subscribed</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {subscribers.map((s) => (
                  <tr key={s.id} className="border-b border-gray-50 last:border-0">
                    <td className="px-6 py-3 text-gray-900">{s.email}</td>
                    <td className="px-6 py-3 text-gray-400">{new Date(s.subscribed_at).toLocaleDateString('en-IN')}</td>
                    <td className="px-6 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {s.is_active ? 'Active' : 'Unsubscribed'}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <button onClick={() => remove(s.id)} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
                        <IconTrash size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                <button key={p} onClick={() => fetch(p)} className={`h-9 min-w-9 rounded-lg px-3 text-sm ${p === page ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'}`}>
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
