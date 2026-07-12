import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { IconPlus, IconEdit, IconTrash } from '@tabler/icons-react'

export default function AdminCoupons() {
  const [coupons, setCoupons] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const empty = {
    code: '', description: '', discount_type: 'percentage', discount_value: '',
    min_order_value: 0, max_discount: '', usage_limit: '', is_active: true, expires_at: '',
  }
  const [form, setForm] = useState(empty)

  const fetch = () => {
    setLoading(true)
    adminApi.get('/admin/coupons')
      .then((r) => setCoupons(r.data.coupons))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [])

  const openNew = () => { setEditing(null); setForm(empty); setShowForm(true) }

  const openEdit = (c) => {
    setEditing(c)
    setForm({
      code: c.code, description: c.description || '', discount_type: c.discount_type,
      discount_value: c.discount_value, min_order_value: c.min_order_value,
      max_discount: c.max_discount ?? '', usage_limit: c.usage_limit ?? '',
      is_active: c.is_active, expires_at: c.expires_at ? c.expires_at.slice(0, 16) : '',
    })
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      discount_value: Number(form.discount_value),
      min_order_value: Number(form.min_order_value),
      max_discount: form.max_discount ? Number(form.max_discount) : null,
      usage_limit: form.usage_limit ? Number(form.usage_limit) : null,
      expires_at: form.expires_at || null,
    }
    try {
      if (editing) {
        await adminApi.put(`/admin/coupons/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/coupons', payload)
      }
      setShowForm(false)
      fetch()
    } catch (err) {
      alert(err.response?.data?.error || 'Save failed')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this coupon?')) return
    await adminApi.delete(`/admin/coupons/${id}`)
    fetch()
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-[#C8963E]'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Coupons</h1>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-[#C8963E] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#b88534]">
          <IconPlus size={18} /> Add Coupon
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-medium text-gray-900">{editing ? 'Edit Coupon' : 'New Coupon'}</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <input value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value.toUpperCase() }))} placeholder="Code *" required className={inputCls} />
            <input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="Description" className={inputCls} />
            <select value={form.discount_type} onChange={(e) => setForm((f) => ({ ...f, discount_type: e.target.value }))} className={inputCls}>
              <option value="percentage">Percentage</option>
              <option value="flat">Flat</option>
            </select>
            <input type="number" step="0.01" value={form.discount_value} onChange={(e) => setForm((f) => ({ ...f, discount_value: e.target.value }))} placeholder="Discount value *" required className={inputCls} />
            <input type="number" step="0.01" value={form.min_order_value} onChange={(e) => setForm((f) => ({ ...f, min_order_value: e.target.value }))} placeholder="Min order value" className={inputCls} />
            <input type="number" step="0.01" value={form.max_discount} onChange={(e) => setForm((f) => ({ ...f, max_discount: e.target.value }))} placeholder="Max discount cap" className={inputCls} />
            <input type="number" value={form.usage_limit} onChange={(e) => setForm((f) => ({ ...f, usage_limit: e.target.value }))} placeholder="Usage limit" className={inputCls} />
            <input type="datetime-local" value={form.expires_at} onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))} className={inputCls} />
            <label className="flex items-center gap-2 py-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              <span className="text-sm text-gray-700">Active</span>
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="submit" className="rounded-lg bg-[#C8963E] px-5 py-2 text-sm font-medium text-white hover:bg-[#b88534]">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                <th className="px-6 py-3 font-medium">Code</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Value</th>
                <th className="px-6 py-3 font-medium">Used</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Expires</th>
                <th className="px-6 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {coupons.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3 font-mono font-medium text-gray-900">{c.code}</td>
                  <td className="px-6 py-3 capitalize text-gray-500">{c.discount_type}</td>
                  <td className="px-6 py-3 text-gray-700">{c.discount_type === 'percentage' ? `${c.discount_value}%` : `₹${c.discount_value}`}</td>
                  <td className="px-6 py-3 text-gray-500">{c.used_count}{c.usage_limit ? `/${c.usage_limit}` : ''}</td>
                  <td className="px-6 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${c.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {c.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-400">{c.expires_at ? new Date(c.expires_at).toLocaleDateString('en-IN') : 'Never'}</td>
                  <td className="px-6 py-3">
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(c)} className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"><IconEdit size={16} /></button>
                      <button onClick={() => handleDelete(c.id)} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"><IconTrash size={16} /></button>
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
