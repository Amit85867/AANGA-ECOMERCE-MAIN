import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import { IconPlus, IconEdit, IconTrash } from '@tabler/icons-react'

export default function AdminAnnouncements() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const empty = {
    text: '', highlight_text: '', link_url: '', link_text: '',
    bg_color: '#0A0A0A', text_color: '#ffffff', highlight_color: '#D4AF37',
    sort_order: 0, is_active: true, starts_at: '', ends_at: '',
  }
  const [form, setForm] = useState(empty)

  const fetchItems = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/announcements', { params: { per_page: 100 } })
      .then((r) => setItems(r.data.announcements))
      .catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchItems() }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }

  const openEdit = (a) => {
    setEditing(a)
    setForm({
      text: a.text, highlight_text: a.highlight_text || '',
      link_url: a.link_url || '', link_text: a.link_text || '',
      bg_color: a.bg_color || '#0A0A0A', text_color: a.text_color || '#ffffff',
      highlight_color: a.highlight_color || '#D4AF37',
      sort_order: a.sort_order, is_active: a.is_active,
      starts_at: a.starts_at ? a.starts_at.slice(0, 16) : '',
      ends_at: a.ends_at ? a.ends_at.slice(0, 16) : '',
    })
    setShowForm(true)
  }

  // Guards the save so a double click (or Enter twice) cannot create two.
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      await saveForm(e)
    } finally {
      setSaving(false)
    }
  }

  const saveForm = async (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      sort_order: Number(form.sort_order) || 0,
      highlight_text: form.highlight_text || null,
      link_url: form.link_url || null,
      link_text: form.link_text || null,
      starts_at: form.starts_at || null,
      ends_at: form.ends_at || null,
    }
    try {
      if (editing) {
        await adminApi.put(`/admin/announcements/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/announcements', payload)
      }
      toast.success(editing ? 'Changes saved.' : 'Created.')
      setShowForm(false)
      fetchItems()
    } catch (err) {
      notifyError(err, 'Save failed')
    }
  }

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this announcement?', message: 'It will disappear from the storefront straight away.', confirmLabel: 'Delete', danger: true }))) return
    try {
      await adminApi.delete(`/admin/announcements/${id}`)
      toast.success('Deleted.')
      fetchItems()
    } catch (err) {
      notifyError(err, 'Could not delete this.')
    }
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold'
  const labelCls = 'block text-xs font-medium text-gray-500 mb-1'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Announcements</h1>
          <p className="mt-1 text-sm text-gray-500">Manage the top announcement bar on the website</p>
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Announcement
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-medium text-gray-900">{editing ? 'Edit Announcement' : 'New Announcement'}</h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Main Text *</label>
              <input value={form.text} onChange={(e) => setForm((f) => ({ ...f, text: e.target.value }))} placeholder="e.g. Summer Sale Live" required className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Highlight Text (shown in accent color)</label>
              <input value={form.highlight_text} onChange={(e) => setForm((f) => ({ ...f, highlight_text: e.target.value }))} placeholder="e.g. Free shipping on orders above ₹999" className={inputCls} />
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Link URL</label>
              <input value={form.link_url} onChange={(e) => setForm((f) => ({ ...f, link_url: e.target.value }))} placeholder="/offers" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Link Text</label>
              <input value={form.link_text} onChange={(e) => setForm((f) => ({ ...f, link_text: e.target.value }))} placeholder="Shop Now" className={inputCls} />
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <label className={labelCls}>Background Color</label>
              <div className="flex gap-2">
                <input type="color" value={form.bg_color} onChange={(e) => setForm((f) => ({ ...f, bg_color: e.target.value }))} className="h-10 w-12 cursor-pointer rounded border border-gray-200" />
                <input value={form.bg_color} onChange={(e) => setForm((f) => ({ ...f, bg_color: e.target.value }))} className={inputCls} />
              </div>
            </div>
            <div>
              <label className={labelCls}>Text Color</label>
              <div className="flex gap-2">
                <input type="color" value={form.text_color} onChange={(e) => setForm((f) => ({ ...f, text_color: e.target.value }))} className="h-10 w-12 cursor-pointer rounded border border-gray-200" />
                <input value={form.text_color} onChange={(e) => setForm((f) => ({ ...f, text_color: e.target.value }))} className={inputCls} />
              </div>
            </div>
            <div>
              <label className={labelCls}>Highlight Color</label>
              <div className="flex gap-2">
                <input type="color" value={form.highlight_color} onChange={(e) => setForm((f) => ({ ...f, highlight_color: e.target.value }))} className="h-10 w-12 cursor-pointer rounded border border-gray-200" />
                <input value={form.highlight_color} onChange={(e) => setForm((f) => ({ ...f, highlight_color: e.target.value }))} className={inputCls} />
              </div>
            </div>
          </div>

          {/* Live preview */}
          <div className="mt-4">
            <label className={labelCls}>Preview</label>
            <div
              className="rounded-lg py-2.5 px-4 text-center text-[11px] tracking-[1.5px] uppercase"
              style={{ backgroundColor: form.bg_color, color: form.text_color + 'd9' }}
            >
              {form.text}{' '}
              <span style={{ color: form.highlight_color }}>{form.highlight_text}</span>
              {form.link_text && <span className="ml-2 underline">{form.link_text}</span>}
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <div>
              <label className={labelCls}>Sort Order</label>
              <input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Starts At</label>
              <input type="datetime-local" value={form.starts_at} onChange={(e) => setForm((f) => ({ ...f, starts_at: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Ends At</label>
              <input type="datetime-local" value={form.ends_at} onChange={(e) => setForm((f) => ({ ...f, ends_at: e.target.value }))} className={inputCls} />
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" />
                <span className="text-sm text-gray-700">Active</span>
              </label>
            </div>
          </div>

          <div className="mt-5 flex gap-2">
            <button type="submit" disabled={saving} aria-busy={saving} className="disabled:cursor-not-allowed disabled:opacity-60 rounded-lg bg-gold px-5 py-2 text-sm font-medium text-white hover:bg-gold-dark">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetchItems()} />
      ) : items.length === 0 ? (
        <EmptyState title="No announcements yet" hint="Add one to show a notice bar at the top of the store." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                <th className="px-6 py-3 font-medium">Preview</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Schedule</th>
                <th className="px-6 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3">
                    <div
                      className="inline-block rounded px-3 py-1 text-[10px] tracking-[1px] uppercase"
                      style={{ backgroundColor: a.bg_color, color: a.text_color + 'd9' }}
                    >
                      {a.text}{' '}
                      <span style={{ color: a.highlight_color }}>{a.highlight_text}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {a.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-xs text-gray-400">
                    {a.starts_at ? new Date(a.starts_at).toLocaleDateString('en-IN') : '—'} → {a.ends_at ? new Date(a.ends_at).toLocaleDateString('en-IN') : '—'}
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex gap-1">
                      <button type="button" onClick={() => openEdit(a)} aria-label="Edit" title="Edit" className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                      <button type="button" onClick={() => handleDelete(a.id)} aria-label="Delete" title="Delete" className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
                    </div>
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
