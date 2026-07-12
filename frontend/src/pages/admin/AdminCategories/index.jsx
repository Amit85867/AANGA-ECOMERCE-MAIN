import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { IconPlus, IconEdit, IconTrash, IconChevronRight } from '@tabler/icons-react'

function CategoryRow({ cat, depth = 0, onEdit, onDelete }) {
  const [open, setOpen] = useState(true)
  const hasChildren = cat.children?.length > 0

  return (
    <>
      <tr className="border-b border-gray-50">
        <td className="px-6 py-3">
          <div className="flex items-center" style={{ paddingLeft: depth * 24 }}>
            {hasChildren && (
              <button onClick={() => setOpen(!open)} className="mr-2 text-gray-400">
                <IconChevronRight size={16} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
              </button>
            )}
            {!hasChildren && <span className="mr-6" />}
            <span className="font-medium text-gray-900">{cat.name}</span>
          </div>
        </td>
        <td className="px-6 py-3 text-gray-500">{cat.slug}</td>
        <td className="px-6 py-3 text-gray-500">{cat.product_count}</td>
        <td className="px-6 py-3">
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cat.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
            {cat.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td className="px-6 py-3">
          <div className="flex gap-1">
            <button onClick={() => onEdit(cat)} className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
              <IconEdit size={16} />
            </button>
            <button onClick={() => onDelete(cat)} className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
              <IconTrash size={16} />
            </button>
          </div>
        </td>
      </tr>
      {open && hasChildren && cat.children.map((ch) => (
        <CategoryRow key={ch.id} cat={ch} depth={depth + 1} onEdit={onEdit} onDelete={onDelete} />
      ))}
    </>
  )
}

export default function AdminCategories() {
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const [form, setForm] = useState({
    name: '', slug: '', description: '', parent_id: '', sort_order: 0, is_active: true,
  })

  const fetch = () => {
    setLoading(true)
    adminApi.get('/admin/categories')
      .then((r) => setCategories(r.data.categories))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [])

  const flatCats = []
  const flatten = (cats, depth = 0) => {
    for (const c of cats) {
      flatCats.push({ id: c.id, name: '  '.repeat(depth) + c.name })
      if (c.children?.length) flatten(c.children, depth + 1)
    }
  }
  flatten(categories)

  const autoSlug = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')

  const openNew = () => {
    setEditing(null)
    setForm({ name: '', slug: '', description: '', parent_id: '', sort_order: 0, is_active: true })
    setShowForm(true)
  }

  const openEdit = (cat) => {
    setEditing(cat)
    setForm({
      name: cat.name,
      slug: cat.slug,
      description: cat.description || '',
      parent_id: cat.parent_id || '',
      sort_order: cat.sort_order,
      is_active: cat.is_active,
    })
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = { ...form, sort_order: Number(form.sort_order), parent_id: form.parent_id ? Number(form.parent_id) : null }
    try {
      if (editing) {
        await adminApi.put(`/admin/categories/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/categories', payload)
      }
      setShowForm(false)
      fetch()
    } catch (err) {
      alert(err.response?.data?.error || 'Save failed')
    }
  }

  const handleDelete = async (cat) => {
    if (!confirm(`Deactivate "${cat.name}"?`)) return
    try {
      await adminApi.delete(`/admin/categories/${cat.id}`)
      fetch()
    } catch (err) {
      alert(err.response?.data?.error || 'Delete failed')
    }
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-[#C8963E]'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Categories</h1>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-[#C8963E] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#b88534]">
          <IconPlus size={18} /> Add Category
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-medium text-gray-900">{editing ? 'Edit Category' : 'New Category'}</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <input name="name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value, ...(!editing && { slug: autoSlug(e.target.value) }) }))} placeholder="Name *" required className={inputCls} />
            <input name="slug" value={form.slug} onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))} placeholder="Slug *" required className={inputCls} />
            <select name="parent_id" value={form.parent_id} onChange={(e) => setForm((f) => ({ ...f, parent_id: e.target.value }))} className={inputCls}>
              <option value="">No parent (root)</option>
              {flatCats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input name="sort_order" type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))} placeholder="Sort order" className={inputCls} />
            <label className="flex items-center gap-2 py-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              <span className="text-sm text-gray-700">Active</span>
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="submit" className="rounded-lg bg-[#C8963E] px-5 py-2 text-sm font-medium text-white hover:bg-[#b88534]">
              {editing ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">
              Cancel
            </button>
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
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Slug</th>
                <th className="px-6 py-3 font-medium">Products</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <CategoryRow key={cat.id} cat={cat} onEdit={openEdit} onDelete={handleDelete} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
