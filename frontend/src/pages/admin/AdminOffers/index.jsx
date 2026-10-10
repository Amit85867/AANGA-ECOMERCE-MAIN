import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import { IconPlus, IconEdit, IconTrash } from '@tabler/icons-react'

const OFFER_TYPES = ['percentage_off', 'flat_off', 'free_shipping', 'bogo']

export default function AdminOffers() {
  const [offers, setOffers] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const empty = {
    title: '', description: '', category_id: '', offer_type: 'percentage_off',
    discount_percent: '', image_url: '', is_active: true, starts_at: '', ends_at: '',
  }
  const [form, setForm] = useState(empty)

  const fetch = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/offers', { params: { per_page: 100 } })
      .then((r) => setOffers(r.data.offers))
      .catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetch()
    adminApi.get('/admin/categories').then((r) => {
      const flat = []
      const flatten = (cats, d = 0) => {
        for (const c of cats) {
          flat.push({ id: c.id, name: '  '.repeat(d) + c.name })
          if (c.children?.length) flatten(c.children, d + 1)
        }
      }
      flatten(r.data.categories)
      setCategories(flat)
    })
  }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }

  const openEdit = (o) => {
    setEditing(o)
    setForm({
      title: o.title, description: o.description || '', category_id: o.category_id || '',
      offer_type: o.offer_type, discount_percent: o.discount_percent ?? '',
      image_url: o.image_url || '', is_active: o.is_active,
      starts_at: o.starts_at ? o.starts_at.slice(0, 16) : '',
      ends_at: o.ends_at ? o.ends_at.slice(0, 16) : '',
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
      category_id: form.category_id ? Number(form.category_id) : null,
      discount_percent: form.discount_percent ? Number(form.discount_percent) : null,
      starts_at: form.starts_at || null,
      ends_at: form.ends_at || null,
    }
    try {
      if (editing) {
        await adminApi.put(`/admin/offers/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/offers', payload)
      }
      toast.success(editing ? 'Changes saved.' : 'Created.')
      setShowForm(false)
      fetch()
    } catch (err) {
      notifyError(err, 'Save failed')
    }
  }

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this offer?', message: 'It will disappear from the Offers page.', confirmLabel: 'Delete', danger: true }))) return
    try {
      await adminApi.delete(`/admin/offers/${id}`)
      toast.success('Deleted.')
      fetch()
    } catch (err) {
      notifyError(err, 'Could not delete this.')
    }
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Offers</h1>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Offer
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-medium text-gray-900">{editing ? 'Edit Offer' : 'New Offer'}</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="Title *" required className={inputCls} />
            <input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="Description" className={inputCls} />
            <select value={form.offer_type} onChange={(e) => setForm((f) => ({ ...f, offer_type: e.target.value }))} className={inputCls}>
              {OFFER_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
            </select>
            <input type="number" step="0.01" value={form.discount_percent} onChange={(e) => setForm((f) => ({ ...f, discount_percent: e.target.value }))} placeholder="Discount %" className={inputCls} />
            <select value={form.category_id} onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))} className={inputCls}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input value={form.image_url} onChange={(e) => setForm((f) => ({ ...f, image_url: e.target.value }))} placeholder="Image URL" className={inputCls} />
            <input type="datetime-local" value={form.starts_at} onChange={(e) => setForm((f) => ({ ...f, starts_at: e.target.value }))} className={inputCls} />
            <input type="datetime-local" value={form.ends_at} onChange={(e) => setForm((f) => ({ ...f, ends_at: e.target.value }))} className={inputCls} />
            <label className="flex items-center gap-2 py-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              <span className="text-sm text-gray-700">Active</span>
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="submit" disabled={saving} aria-busy={saving} className="disabled:cursor-not-allowed disabled:opacity-60 rounded-lg bg-gold px-5 py-2 text-sm font-medium text-white hover:bg-gold-dark">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetch()} />
      ) : offers.length === 0 ? (
        <EmptyState title="No offers yet" hint="Create an offer to feature on the Offers page." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                <th className="px-6 py-3 font-medium">Title</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Discount</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Period</th>
                <th className="px-6 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {offers.map((o) => (
                <tr key={o.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3 font-medium text-gray-900">{o.title}</td>
                  <td className="px-6 py-3 capitalize text-gray-500">{o.offer_type.replace(/_/g, ' ')}</td>
                  <td className="px-6 py-3 text-gray-700">{o.discount_percent ? `${o.discount_percent}%` : '-'}</td>
                  <td className="px-6 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${o.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {o.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-xs text-gray-400">
                    {o.starts_at ? new Date(o.starts_at).toLocaleDateString('en-IN') : '—'} → {o.ends_at ? new Date(o.ends_at).toLocaleDateString('en-IN') : '—'}
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex gap-1">
                      <button type="button" onClick={() => openEdit(o)} aria-label="Edit" title="Edit" className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                      <button type="button" onClick={() => handleDelete(o.id)} aria-label="Delete" title="Delete" className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
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
