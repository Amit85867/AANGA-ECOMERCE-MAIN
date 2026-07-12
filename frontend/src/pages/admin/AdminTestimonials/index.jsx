import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { IconPlus, IconEdit, IconTrash, IconPhoto, IconStarFilled } from '@tabler/icons-react'

export default function AdminTestimonials() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [uploading, setUploading] = useState(false)

  const empty = { name: '', location: '', rating: 5, quote: '', avatar_url: '', sort_order: 0, is_active: true }
  const [form, setForm] = useState(empty)

  const fetchItems = () => {
    setLoading(true)
    adminApi.get('/admin/testimonials').then((r) => setItems(r.data.testimonials)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(() => { fetchItems() }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }
  const openEdit = (t) => {
    setEditing(t)
    setForm({ name: t.name, location: t.location || '', rating: t.rating, quote: t.quote, avatar_url: t.avatar_url || '', sort_order: t.sort_order, is_active: t.is_active })
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
      setForm((f) => ({ ...f, avatar_url: r.data.url }))
    } catch { alert('Upload failed') }
    setUploading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      rating: Number(form.rating),
      sort_order: Number(form.sort_order) || 0,
      location: form.location || null,
      avatar_url: form.avatar_url || null,
    }
    try {
      if (editing) await adminApi.put(`/admin/testimonials/${editing.id}`, payload)
      else await adminApi.post('/admin/testimonials', payload)
      setShowForm(false); fetchItems()
    } catch (err) { alert(err.response?.data?.error || 'Save failed') }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this testimonial?')) return
    await adminApi.delete(`/admin/testimonials/${id}`)
    fetchItems()
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-[#C8963E]'
  const labelCls = 'block text-xs font-medium text-gray-500 mb-1'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Testimonials</h1>
          <p className="mt-1 text-sm text-gray-500">Customer reviews on the homepage. Only 4–5★ show up front; the rest sit under "View more".</p>
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-[#C8963E] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#b88534]">
          <IconPlus size={18} /> Add Testimonial
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-medium text-gray-900">{editing ? 'Edit Testimonial' : 'New Testimonial'}</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div><label className={labelCls}>Customer Name *</label><input required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} className={inputCls} /></div>
            <div><label className={labelCls}>Location</label><input value={form.location} onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))} placeholder="e.g. Patna, Bihar" className={inputCls} /></div>
            <div>
              <label className={labelCls}>Rating</label>
              <select value={form.rating} onChange={(e) => setForm((f) => ({ ...f, rating: e.target.value }))} className={inputCls}>
                {[5, 4, 3, 2, 1].map((r) => <option key={r} value={r}>{r} Star{r > 1 ? 's' : ''}{r >= 4 ? ' (shown up front)' : ' (in View more)'}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className={labelCls}>Review Quote *</label>
            <textarea required value={form.quote} onChange={(e) => setForm((f) => ({ ...f, quote: e.target.value }))} rows={3} className={inputCls} />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Customer Photo</label>
              <div className="flex gap-2">
                <input value={form.avatar_url} onChange={(e) => setForm((f) => ({ ...f, avatar_url: e.target.value }))} placeholder="Image URL or upload →" className={inputCls} />
                <label className="shrink-0 cursor-pointer rounded-lg border border-gray-200 px-3 py-2.5 text-gray-500 hover:bg-gray-50">
                  <IconPhoto size={18} />
                  <input type="file" accept="image/*" className="hidden" onChange={handleUpload} />
                </label>
              </div>
              {form.avatar_url && <img src={form.avatar_url} alt="" className="mt-2 h-14 w-14 rounded-full border object-cover" />}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><label className={labelCls}>Sort Order</label><input type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))} className={inputCls} /></div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" /><span className="text-sm text-gray-700">Active</span></label>
              </div>
            </div>
          </div>
          <div className="mt-5 flex gap-2">
            <button type="submit" disabled={uploading} className="rounded-lg bg-[#C8963E] px-5 py-2 text-sm font-medium text-white hover:bg-[#b88534] disabled:opacity-50">{uploading ? 'Uploading…' : editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : items.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No testimonials yet.</div>
      ) : (
        <div className="grid gap-4">
          {items.map((t) => (
            <div key={t.id} className="flex items-start gap-4 rounded-xl border border-gray-200 bg-white p-4">
              <div className="h-12 w-12 shrink-0 overflow-hidden rounded-full bg-gray-100">
                {t.avatar_url ? <img src={t.avatar_url} alt="" className="h-full w-full object-cover" /> : <div className="flex h-full w-full items-center justify-center text-xs font-bold text-gray-400">{t.name.split(' ').map((w) => w[0]).join('').slice(0, 2)}</div>}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900">{t.name}</span>
                  <span className="flex items-center text-[#C8963E]">{[...Array(t.rating)].map((_, i) => <IconStarFilled key={i} size={12} />)}</span>
                  {t.rating < 4 && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500">View more</span>}
                  {!t.is_active && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500">Inactive</span>}
                </div>
                {t.location && <div className="text-xs text-gray-400">{t.location}</div>}
                <p className="mt-1 text-sm text-gray-600 line-clamp-2">{t.quote}</p>
              </div>
              <div className="flex gap-1">
                <button onClick={() => openEdit(t)} className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                <button onClick={() => handleDelete(t.id)} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
