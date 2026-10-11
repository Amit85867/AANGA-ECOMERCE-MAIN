import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import {
  IconPlus, IconEdit, IconTrash, IconPhoto, IconShieldCheck,
} from '@tabler/icons-react'
import { FEATURE_ICONS } from '@/utils/featureIcons'

const ICON_NAMES = Object.keys(FEATURE_ICONS)

export default function AdminFeatures() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [uploading, setUploading] = useState(false)

  const empty = { icon: 'shield-check', title: '', description: '', image_url: '', sort_order: 0, is_active: true }
  const [form, setForm] = useState(empty)

  const fetchItems = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/features', { params: { per_page: 100 } }).then((r) => setItems(r.data.features)).catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.')).finally(() => setLoading(false))
  }
  useEffect(() => { fetchItems() }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }
  const openEdit = (f) => {
    setEditing(f)
    setForm({ icon: f.icon || 'shield-check', title: f.title, description: f.description || '', image_url: f.image_url || '', sort_order: f.sort_order, is_active: f.is_active })
    setShowForm(true)
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const r = await adminApi.post('/admin/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setForm((f) => ({ ...f, image_url: r.data.url }))
    } catch { toast.error('Upload failed') }
    setUploading(false)
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
      description: form.description || null,
      image_url: form.image_url || null,
      icon: form.icon || null,
    }
    try {
      if (editing) await adminApi.put(`/admin/features/${editing.id}`, payload)
      else await adminApi.post('/admin/features', payload)
      toast.success(editing ? 'Changes saved.' : 'Created.')
      setShowForm(false); fetchItems()
    } catch (err) { notifyError(err, 'Save failed') }
  }

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this card?', message: 'It will be removed from the home page.', confirmLabel: 'Delete', danger: true }))) return
    try {
      await adminApi.delete(`/admin/features/${id}`)
      toast.success('Deleted.')
      fetchItems()
    } catch (err) {
      notifyError(err, 'Could not delete this.')
    }
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold'
  const labelCls = 'block text-xs font-medium text-gray-500 mb-1'
  const PreviewIcon = FEATURE_ICONS[form.icon] || IconShieldCheck

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Why Choose (Feature Cards)</h1>
          <p className="mt-1 text-sm text-gray-500">The promise cards shown on the homepage. Use an icon, or upload an image to replace it.</p>
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Card
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-medium text-gray-900">{editing ? 'Edit Card' : 'New Card'}</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label htmlFor="features-icon" className={labelCls}>Icon</label>
              <div className="flex items-center gap-2">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-ink"><PreviewIcon size={18} className="text-gold" /></span>
                <select id="features-icon" value={form.icon} onChange={(e) => setForm((f) => ({ ...f, icon: e.target.value }))} className={inputCls}>
                  {ICON_NAMES.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>
            <div><label htmlFor="features-title" className={labelCls}>Title *</label><input id="features-title" required value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} className={inputCls} /></div>
            <div><label htmlFor="features-sort-order" className={labelCls}>Sort Order</label><input id="features-sort-order" type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))} className={inputCls} /></div>
          </div>
          <div className="mt-4">
            <label htmlFor="features-description" className={labelCls}>Description</label>
            <textarea id="features-description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} className={inputCls} />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="features-image-optional-replaces-the-icon" className={labelCls}>Image (optional — replaces the icon)</label>
              <div className="flex gap-2">
                <input id="features-image-optional-replaces-the-icon" value={form.image_url} onChange={(e) => setForm((f) => ({ ...f, image_url: e.target.value }))} placeholder="Image URL or upload →" className={inputCls} />
                <label className="shrink-0 cursor-pointer rounded-lg border border-gray-200 px-3 py-2.5 text-gray-500 hover:bg-gray-50">
                  <IconPhoto size={18} />
                  <input type="file" accept="image/*" aria-label="Upload image" className="hidden" onChange={handleUpload} />
                </label>
              </div>
              {form.image_url && <img src={form.image_url} alt="" className="mt-2 h-14 rounded border object-cover" />}
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" /><span className="text-sm text-gray-700">Active</span></label>
            </div>
          </div>
          <div className="mt-5 flex gap-2">
            <button type="submit" disabled={uploading || saving} aria-busy={saving} className="disabled:cursor-not-allowed disabled:opacity-60 rounded-lg bg-gold px-5 py-2 text-sm font-medium text-white hover:bg-gold-dark disabled:opacity-50">{uploading ? 'Uploading…' : editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetchItems()} />
      ) : items.length === 0 ? (
        <EmptyState title="No cards yet" hint="Add the reasons customers should shop with you." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {items.map((f) => {
            const Icon = FEATURE_ICONS[f.icon] || IconShieldCheck
            return (
              <div key={f.id} className="flex items-start gap-4 rounded-xl border border-gray-200 bg-white p-4">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-ink">
                  {f.image_url ? <img src={f.image_url} alt="" className="h-full w-full object-cover" /> : <Icon size={20} className="text-gold" />}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{f.title}</span>
                    {!f.is_active && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500">Inactive</span>}
                  </div>
                  <p className="mt-0.5 text-sm text-gray-500 line-clamp-2">{f.description}</p>
                </div>
                <div className="flex gap-1">
                  <button type="button" onClick={() => openEdit(f)} aria-label="Edit" title="Edit" className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                  <button type="button" onClick={() => handleDelete(f.id)} aria-label="Delete" title="Delete" className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
