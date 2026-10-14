import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
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
            <button type="button" onClick={() => onEdit(cat)} aria-label="Edit" title="Edit" className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
              <IconEdit size={16} />
            </button>
            <button type="button" onClick={() => onDelete(cat)} aria-label="Deactivate" title="Deactivate" className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
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
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)

  const [form, setForm] = useState({
    name: '', slug: '', description: '', parent_id: '', sort_order: 0, is_active: true,
  })

  const fetch = () => {
    setLoading(true)
    setError(null)
    adminApi.get('/admin/categories', { params: { per_page: 100 } })
      .then((r) => setCategories(r.data.categories))
      .catch((err) => setError(err.response?.data?.error || 'Could not load this page. Check your connection and try again.'))
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
    const payload = { ...form, sort_order: Number(form.sort_order), parent_id: form.parent_id ? Number(form.parent_id) : null }
    try {
      if (editing) {
        await adminApi.put(`/admin/categories/${editing.id}`, payload)
      } else {
        await adminApi.post('/admin/categories', payload)
      }
      toast.success(editing ? 'Changes saved.' : 'Created.')
      setShowForm(false)
      fetch()
    } catch (err) {
      notifyError(err, 'Save failed')
    }
  }

  const handleDelete = async (cat) => {
    if (!(await confirm({ title: `Deactivate “${cat.name}”?`, message: 'It is hidden from the storefront. Products in it are kept.', confirmLabel: 'Deactivate', danger: true }))) return
    try {
      await adminApi.delete(`/admin/categories/${cat.id}`)
      toast.success(`“${cat.name}” deactivated.`)
      fetch()
    } catch (err) {
      notifyError(err, 'Delete failed')
    }
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Categories</h1>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-white hover:bg-gold-dark">
          <IconPlus size={18} /> Add Category
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-medium text-gray-900">{editing ? 'Edit Category' : 'New Category'}</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-500">Name *</span>
              <input name="name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value, ...(!editing && { slug: autoSlug(e.target.value) }) }))} required className={inputCls} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-500">Slug *</span>
              <input name="slug" value={form.slug} onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))} required className={inputCls} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-500">Parent category</span>
              <select name="parent_id" value={form.parent_id} onChange={(e) => setForm((f) => ({ ...f, parent_id: e.target.value }))} className={inputCls}>
                <option value="">No parent (root)</option>
                {flatCats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-500">Sort order</span>
              <input name="sort_order" type="number" value={form.sort_order} onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))} className={inputCls} />
            </label>
            <label className="flex items-center gap-2 py-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              <span className="text-sm text-gray-700">Active</span>
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="submit" disabled={saving} aria-busy={saving} className="disabled:cursor-not-allowed disabled:opacity-60 rounded-lg bg-gold px-5 py-2 text-sm font-medium text-white hover:bg-gold-dark">
              {editing ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg bg-gray-100 px-5 py-2 text-sm text-gray-600 hover:bg-gray-200">
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetch()} />
      ) : categories.length === 0 ? (
        <EmptyState title="No categories yet" hint="Create a category before adding products." />
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
