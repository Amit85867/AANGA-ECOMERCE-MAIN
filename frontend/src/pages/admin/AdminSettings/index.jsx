import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import { useAdminStore } from '@/store/useAdminStore'
import { IconPlus, IconTrash } from '@tabler/icons-react'

export default function AdminSettings() {
  const { admin } = useAdminStore()
  const [admins, setAdmins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'staff' })
  const [formError, setFormError] = useState('')

  const fetch = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/auth/admins', { params: { per_page: 100 } })
      .then((r) => setAdmins(r.data.admins))
      .catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (saving) return
    setFormError('')
    setSaving(true)
    try {
      await adminApi.post('/admin/auth/admins', form)
      toast.success(`${form.full_name} can now sign in to the admin panel.`)
      setShowForm(false)
      setForm({ email: '', password: '', full_name: '', role: 'staff' })
      fetch()
    } catch (err) {
      setFormError(err.response?.data?.error || 'Could not create the admin.')
    }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this admin?', message: 'They will be signed out and lose access to the admin panel.', confirmLabel: 'Delete admin', danger: true }))) return
    try {
      await adminApi.delete(`/admin/auth/admins/${id}`)
      toast.success('Admin removed.')
      fetch()
    } catch (err) {
      notifyError(err, 'Could not remove this admin.')
    }
  }

  if (admin?.role !== 'master') {
    return <div className="py-20 text-center text-gray-400">Master admin access required</div>
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Admin Settings</h1>
        <button onClick={() => setShowForm(!showForm)} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Admin
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-medium text-gray-900">Create Admin</h3>
          {formError && <div role="alert" className="mb-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{formError}</div>}
          <div className="grid gap-4 sm:grid-cols-2">
            <input value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} placeholder="Full name *" required className={inputCls} />
            <input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} placeholder="Email *" required className={inputCls} />
            <input type="password" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} placeholder="Password (min 8 characters) *" required minLength={8} autoComplete="new-password" className={inputCls} />
            <select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))} className={inputCls}>
              <option value="staff">Staff</option>
              <option value="master">Master</option>
            </select>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="submit" disabled={saving} aria-busy={saving} className="disabled:cursor-not-allowed disabled:opacity-60 rounded-lg bg-gold px-5 py-2 text-sm font-medium text-white hover:bg-gold-dark">{saving ? 'Creating…' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetch()} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Email</th>
                <th className="px-6 py-3 font-medium">Role</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Last Login</th>
                <th className="px-6 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3 font-medium text-gray-900">{a.full_name}</td>
                  <td className="px-6 py-3 text-gray-500">{a.email}</td>
                  <td className="px-6 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${a.role === 'master' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                      {a.role}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {a.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-400">
                    {a.last_login ? new Date(a.last_login).toLocaleString('en-IN') : 'Never'}
                  </td>
                  <td className="px-6 py-3">
                    {a.id !== admin.id && (
                      <button onClick={() => handleDelete(a.id)} aria-label={`Delete ${a.full_name}`} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
                        <IconTrash size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
