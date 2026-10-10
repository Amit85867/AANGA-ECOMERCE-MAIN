import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import { IconPlus, IconEdit, IconTrash, IconPhoto } from '@tabler/icons-react'

export default function AdminBanners() {
  const [banners, setBanners] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [uploading, setUploading] = useState(false)

  const empty = {
    title: '', subtitle: '', description: '', image_url: '', mobile_image_url: '',
    link_url: '', link_text: '', secondary_link_url: '', secondary_link_text: '',
    pill_label: '', pill_value: '', chip_value: '', chip_label: '',
    sort_order: 0, is_active: true, starts_at: '', ends_at: '',
  }
  const [form, setForm] = useState(empty)

  const fetchBanners = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/banners', { params: { per_page: 100 } })
      .then((r) => setBanners(r.data.banners))
      .catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchBanners() }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }

  const openEdit = (b) => {
    setEditing(b)
    setForm({
      title: b.title, subtitle: b.subtitle || '', description: b.description || '',
      image_url: b.image_url, mobile_image_url: b.mobile_image_url || '',
      link_url: b.link_url || '', link_text: b.link_text || '',
      secondary_link_url: b.secondary_link_url || '', secondary_link_text: b.secondary_link_text || '',
      pill_label: b.pill_label || '', pill_value: b.pill_value || '',
      chip_value: b.chip_value || '', chip_label: b.chip_label || '',
      sort_order: b.sort_order, is_active: b.is_active,
      starts_at: b.starts_at ? b.starts_at.slice(0, 16) : '',
      ends_at: b.ends_at ? b.ends_at.slice(0, 16) : '',
    })
    setShowForm(true)
  }

  const handleUpload = async (e, field) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const r = await adminApi.post('/admin/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setForm((f) => ({ ...f, [field]: r.data.url }))
    } catch {
      toast.error('Upload failed')
    }
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
      starts_at: form.starts_at || null,
      ends_at: form.ends_at || null,
      subtitle: form.subtitle || null,
      description: form.description || null,
      mobile_image_url: form.mobile_image_url || null,
      link_url: form.link_url || null,
      link_text: form.link_text || null,
      secondary_link_url: form.secondary_link_url || null,
      secondary_link_text: form.secondary_link_text || null,
      pill_label: form.pill_label || null,
      pill_value: form.pill_value || null,
      chip_value: form.chip_value || null,
      chip_label: form.chip_label || null,
    }
    try {
      if (editing) {
        await adminApi.put(`/admin/banners/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/banners', payload)
      }
      toast.success(editing ? 'Changes saved.' : 'Created.')
      setShowForm(false)
      fetchBanners()
    } catch (err) {
      notifyError(err, 'Save failed')
    }
  }

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this banner?', message: 'It will be removed from the home page straight away.', confirmLabel: 'Delete', danger: true }))) return
    try {
      await adminApi.delete(`/admin/banners/${id}`)
      toast.success('Deleted.')
      fetchBanners()
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
          <h1 className="text-2xl font-semibold text-gray-900">Hero Banners</h1>
          <p className="mt-1 text-sm text-gray-500">Manage the homepage hero slider banners</p>
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Banner
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-medium text-gray-900">{editing ? 'Edit Banner' : 'New Banner'}</h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Title *</label>
              <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} required className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Subtitle</label>
              <input value={form.subtitle} onChange={(e) => setForm((f) => ({ ...f, subtitle: e.target.value }))} placeholder="e.g. Summer Collection 2026" className={inputCls} />
            </div>
          </div>

          <div className="mt-4">
            <label className={labelCls}>Description</label>
            <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} className={inputCls} />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Desktop Image *</label>
              <div className="flex gap-2">
                <input value={form.image_url} onChange={(e) => setForm((f) => ({ ...f, image_url: e.target.value }))} required className={inputCls} />
                <label className="shrink-0 cursor-pointer rounded-lg border border-gray-200 px-3 py-2.5 text-gray-500 hover:bg-gray-50">
                  <IconPhoto size={18} />
                  <input type="file" accept="image/*" className="hidden" onChange={(e) => handleUpload(e, 'image_url')} />
                </label>
              </div>
              {form.image_url && <img src={form.image_url} alt="" className="mt-2 h-20 rounded border object-cover" />}
            </div>
            <div>
              <label className={labelCls}>Mobile Image</label>
              <div className="flex gap-2">
                <input value={form.mobile_image_url} onChange={(e) => setForm((f) => ({ ...f, mobile_image_url: e.target.value }))} className={inputCls} />
                <label className="shrink-0 cursor-pointer rounded-lg border border-gray-200 px-3 py-2.5 text-gray-500 hover:bg-gray-50">
                  <IconPhoto size={18} />
                  <input type="file" accept="image/*" className="hidden" onChange={(e) => handleUpload(e, 'mobile_image_url')} />
                </label>
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className={labelCls}>Primary Button Text</label>
              <input value={form.link_text} onChange={(e) => setForm((f) => ({ ...f, link_text: e.target.value }))} placeholder="Shop Now" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Primary Button URL</label>
              <input value={form.link_url} onChange={(e) => setForm((f) => ({ ...f, link_url: e.target.value }))} placeholder="/shop" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Secondary Button Text</label>
              <input value={form.secondary_link_text} onChange={(e) => setForm((f) => ({ ...f, secondary_link_text: e.target.value }))} placeholder="View Offers" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Secondary Button URL</label>
              <input value={form.secondary_link_url} onChange={(e) => setForm((f) => ({ ...f, secondary_link_url: e.target.value }))} placeholder="/offers" className={inputCls} />
            </div>
          </div>

          {/* Decorative overlay badges (optional) — shown on the hero visual */}
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium text-gray-400">Hero badges (optional) — leave blank to hide</p>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className={labelCls}>Pill Label</label>
                <input value={form.pill_label} onChange={(e) => setForm((f) => ({ ...f, pill_label: e.target.value }))} placeholder="This Season" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Pill Value</label>
                <input value={form.pill_value} onChange={(e) => setForm((f) => ({ ...f, pill_value: e.target.value }))} placeholder="Summer Edit '26" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Chip Value</label>
                <input value={form.chip_value} onChange={(e) => setForm((f) => ({ ...f, chip_value: e.target.value }))} placeholder="40%" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Chip Label</label>
                <input value={form.chip_label} onChange={(e) => setForm((f) => ({ ...f, chip_label: e.target.value }))} placeholder="Off Sale Items" className={inputCls} />
              </div>
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
            <button type="submit" disabled={uploading || saving} aria-busy={saving} className="disabled:cursor-not-allowed disabled:opacity-60 rounded-lg bg-gold px-5 py-2 text-sm font-medium text-white hover:bg-gold-dark disabled:opacity-50">
              {uploading ? 'Uploading...' : editing ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetchBanners()} />
      ) : banners.length === 0 ? (
        <EmptyState title="No hero banners yet" hint="Add your first hero banner for the home page." />
      ) : (
        <div className="grid gap-4">
          {banners.map((b) => (
            <div key={b.id} className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4">
              <div className="h-20 w-32 shrink-0 overflow-hidden rounded-lg bg-gray-100">
                {b.image_url && <img src={b.image_url} alt="" className="h-full w-full object-cover" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900 truncate">{b.title}</h3>
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${b.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {b.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                {b.subtitle && <p className="text-sm text-gray-500 truncate">{b.subtitle}</p>}
                <p className="mt-1 text-xs text-gray-400">
                  Order: {b.sort_order} &middot;
                  {b.starts_at ? ` From ${new Date(b.starts_at).toLocaleDateString('en-IN')}` : ' No start date'}
                  {b.ends_at ? ` to ${new Date(b.ends_at).toLocaleDateString('en-IN')}` : ''}
                </p>
              </div>
              <div className="flex gap-1">
                <button type="button" onClick={() => openEdit(b)} aria-label="Edit" title="Edit" className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                <button type="button" onClick={() => handleDelete(b.id)} aria-label="Delete" title="Delete" className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
