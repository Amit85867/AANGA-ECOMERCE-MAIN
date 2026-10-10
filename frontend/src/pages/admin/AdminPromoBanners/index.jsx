import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import { IconPlus, IconEdit, IconTrash, IconX } from '@tabler/icons-react'

export default function AdminPromoBanners() {
  const [promos, setPromos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const empty = {
    title: '', subtitle: '', description: '', badge_text: '',
    image_url: '', link_url: '', link_text: '',
    items: [{ pct: '', label: '' }],
    sort_order: 0, is_active: true, starts_at: '', ends_at: '',
  }
  const [form, setForm] = useState(empty)

  const fetchPromos = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/promo-banners', { params: { per_page: 100 } })
      .then((r) => setPromos(r.data.promo_banners))
      .catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchPromos() }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }

  const openEdit = (p) => {
    setEditing(p)
    setForm({
      title: p.title, subtitle: p.subtitle || '', description: p.description || '',
      badge_text: p.badge_text || '', image_url: p.image_url || '',
      link_url: p.link_url || '', link_text: p.link_text || '',
      items: p.items?.length ? p.items : [{ pct: '', label: '' }],
      sort_order: p.sort_order, is_active: p.is_active,
      starts_at: p.starts_at ? p.starts_at.slice(0, 16) : '',
      ends_at: p.ends_at ? p.ends_at.slice(0, 16) : '',
    })
    setShowForm(true)
  }

  const updateItem = (idx, field, val) => {
    setForm((f) => {
      const items = [...f.items]
      items[idx] = { ...items[idx], [field]: val }
      return { ...f, items }
    })
  }

  const addItem = () => setForm((f) => ({ ...f, items: [...f.items, { pct: '', label: '' }] }))

  const removeItem = (idx) => setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== idx) }))

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
    const validItems = form.items.filter((i) => i.pct && i.label)
    const payload = {
      ...form,
      sort_order: Number(form.sort_order) || 0,
      subtitle: form.subtitle || null,
      description: form.description || null,
      badge_text: form.badge_text || null,
      image_url: form.image_url || null,
      link_url: form.link_url || null,
      link_text: form.link_text || null,
      items: validItems.length ? validItems : null,
      starts_at: form.starts_at || null,
      ends_at: form.ends_at || null,
    }
    try {
      if (editing) {
        await adminApi.put(`/admin/promo-banners/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/promo-banners', payload)
      }
      toast.success(editing ? 'Changes saved.' : 'Created.')
      setShowForm(false)
      fetchPromos()
    } catch (err) {
      notifyError(err, 'Save failed')
    }
  }

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this promo banner?', message: 'It will be removed from the home page.', confirmLabel: 'Delete', danger: true }))) return
    try {
      await adminApi.delete(`/admin/promo-banners/${id}`)
      toast.success('Deleted.')
      fetchPromos()
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
          <h1 className="text-2xl font-semibold text-gray-900">Promo Banners</h1>
          <p className="mt-1 text-sm text-gray-500">Manage the mid-page sale/promotional banners</p>
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Promo
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-medium text-gray-900">{editing ? 'Edit Promo Banner' : 'New Promo Banner'}</h3>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className={labelCls}>Title *</label>
              <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} required className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Subtitle (accent word)</label>
              <input value={form.subtitle} onChange={(e) => setForm((f) => ({ ...f, subtitle: e.target.value }))} placeholder="e.g. Sale" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Badge Text</label>
              <input value={form.badge_text} onChange={(e) => setForm((f) => ({ ...f, badge_text: e.target.value }))} placeholder="e.g. Limited Time" className={inputCls} />
            </div>
          </div>

          <div className="mt-4">
            <label className={labelCls}>Description</label>
            <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} className={inputCls} />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <label className={labelCls}>Image URL</label>
              <input value={form.image_url} onChange={(e) => setForm((f) => ({ ...f, image_url: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Button Text</label>
              <input value={form.link_text} onChange={(e) => setForm((f) => ({ ...f, link_text: e.target.value }))} placeholder="Shop the Sale" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Button URL</label>
              <input value={form.link_url} onChange={(e) => setForm((f) => ({ ...f, link_url: e.target.value }))} placeholder="/offers" className={inputCls} />
            </div>
          </div>

          {/* Sale items grid */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <label className={labelCls + ' mb-0'}>Sale Items (shown as grid cards)</label>
              <button type="button" onClick={addItem} className="text-xs text-gold hover:underline">+ Add Item</button>
            </div>
            <div className="grid gap-2">
              {form.items.map((item, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                  <input value={item.pct} onChange={(e) => updateItem(idx, 'pct', e.target.value)} placeholder="e.g. 50%" className={inputCls + ' max-w-[120px]'} />
                  <input value={item.label} onChange={(e) => updateItem(idx, 'label', e.target.value)} placeholder="e.g. On Jackets" className={inputCls} />
                  {form.items.length > 1 && (
                    <button type="button" onClick={() => removeItem(idx)} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
                      <IconX size={16} />
                    </button>
                  )}
                </div>
              ))}
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
        <ErrorState message={error} onRetry={() => fetchPromos()} />
      ) : promos.length === 0 ? (
        <EmptyState title="No promo banners yet" hint="Add a promotional banner for the home page." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                <th className="px-6 py-3 font-medium">Title</th>
                <th className="px-6 py-3 font-medium">Badge</th>
                <th className="px-6 py-3 font-medium">Items</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Schedule</th>
                <th className="px-6 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {promos.map((p) => (
                <tr key={p.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3 font-medium text-gray-900">{p.title}</td>
                  <td className="px-6 py-3 text-gray-500">{p.badge_text || '—'}</td>
                  <td className="px-6 py-3 text-xs text-gray-500">
                    {p.items?.map((i) => `${i.pct} ${i.label}`).join(', ') || '—'}
                  </td>
                  <td className="px-6 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {p.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-xs text-gray-400">
                    {p.starts_at ? new Date(p.starts_at).toLocaleDateString('en-IN') : '—'} → {p.ends_at ? new Date(p.ends_at).toLocaleDateString('en-IN') : '—'}
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(p)} className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                      <button onClick={() => handleDelete(p.id)} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
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
