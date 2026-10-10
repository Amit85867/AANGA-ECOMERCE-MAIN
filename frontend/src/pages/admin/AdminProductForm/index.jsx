import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { confirm } from '@/components/admin/confirm'
import { notifyError } from '@/components/admin/helpers'
import { toast } from '@/components/ui/toastStore'
import { ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { IconPlus, IconTrash, IconArrowLeft, IconUpload, IconLink } from '@tabler/icons-react'

export default function AdminProductForm() {
  const { id } = useParams()
  const isEdit = !!id
  const navigate = useNavigate()

  const [categories, setCategories] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(isEdit)
  const [loadError, setLoadError] = useState(null)
  // Stock typed into a variant row but not saved yet: { [variantId]: "12" }
  const [stockDrafts, setStockDrafts] = useState({})
  const [savingVariant, setSavingVariant] = useState(null)

  const [form, setForm] = useState({
    name: '',
    slug: '',
    category_id: '',
    description: '',
    mrp: '',
    selling_price: '',
    badge_label: '',
    badge_class: '',
    is_active: true,
    is_featured: false,
  })

  const [variants, setVariants] = useState([])
  const [images, setImages] = useState([])
  const [newVariant, setNewVariant] = useState({
    size: '',
    color_name: '',
    color_hex: '#000000',
    stock_qty: 0,
    price_override: '',
    sku: '',
  })
  const [newImageUrl, setNewImageUrl] = useState('')
  const [imageMode, setImageMode] = useState('upload')
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    adminApi.get('/admin/categories').then((r) => {
      setCategories(r.data.categories)
    }).catch((err) => {
      console.error('Failed to load categories:', err)
      setError('Failed to load categories — check backend console')
    })

    if (isEdit) {
      setLoading(true)
      setLoadError(null)
      adminApi.get(`/admin/products/${id}`).then((r) => {
        const p = r.data
        setForm({
          name: p.name,
          slug: p.slug,
          category_id: p.category_id,
          description: p.description || '',
          mrp: p.mrp,
          selling_price: p.selling_price,
          badge_label: p.badge_label || '',
          badge_class: p.badge_class || '',
          is_active: p.is_active,
          is_featured: p.is_featured,
        })
        setVariants(p.variants)
        setImages(p.images)
      }).catch((err) => {
        setLoadError(
          err.response?.status === 404
            ? 'This product does not exist.'
            : err.response?.data?.error || 'Could not load this product.',
        )
      }).finally(() => setLoading(false))
    }
  }, [id, isEdit])

  const autoSlug = (name) =>
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '')

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((f) => {
      const next = { ...f, [name]: type === 'checkbox' ? checked : value }
      if (name === 'name' && !isEdit) next.slug = autoSlug(value)
      return next
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    const payload = {
      ...form,
      category_id: Number(form.category_id),
      mrp: Number(form.mrp),
      selling_price: Number(form.selling_price),
    }

    try {
      if (isEdit) {
        await adminApi.put(`/admin/products/${id}`, payload)
        toast.success('Product saved.')
        navigate('/admin/products')
      } else {
        const r = await adminApi.post('/admin/products', payload)
        toast.success('Product created. Now add its sizes, colours and images.')
        navigate(`/admin/products/${r.data.id}`)
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Could not save the product.')
    } finally {
      setSaving(false)
    }
  }

  const addVariant = async () => {
    if (!isEdit) return
    try {
      const payload = {
        ...newVariant,
        stock_qty: Number(newVariant.stock_qty),
        price_override: newVariant.price_override ? Number(newVariant.price_override) : null,
        sku: newVariant.sku || null,
      }
      const r = await adminApi.post(`/admin/products/${id}/variants`, payload)
      setVariants(r.data.variants)
      setNewVariant({ size: '', color_name: '', color_hex: '#000000', stock_qty: 0, price_override: '', sku: '' })
      toast.success('Variant added.')
    } catch (err) {
      notifyError(err, 'Could not add the variant.')
    }
  }

  // Restocking is the most common edit on this page, so stock is changed in
  // place rather than by deleting and re-adding the variant.
  const saveStock = async (variant) => {
    const stock = Number(stockDrafts[variant.id])
    if (!Number.isInteger(stock) || stock < 0) {
      toast.error('Stock must be a whole number, 0 or more.')
      return
    }
    setSavingVariant(variant.id)
    try {
      const r = await adminApi.put(`/admin/products/${id}/variants/${variant.id}`, {
        size: variant.size,
        color_name: variant.color_name,
        color_hex: variant.color_hex,
        stock_qty: stock,
        price_override: variant.price_override,
        sku: variant.sku,
      })
      setVariants(r.data.variants)
      setStockDrafts((d) => { const next = { ...d }; delete next[variant.id]; return next })
      toast.success(`Stock for ${variant.size} · ${variant.color_name} set to ${stock}.`)
    } catch (err) {
      notifyError(err, 'Could not update the stock.')
    }
    setSavingVariant(null)
  }

  const deleteVariant = async (vid) => {
    if (!(await confirm({ title: 'Delete this variant?', message: 'This size and colour will no longer be sold.', confirmLabel: 'Delete', danger: true }))) return
    try {
      const r = await adminApi.delete(`/admin/products/${id}/variants/${vid}`)
      setVariants(r.data.variants)
      toast.success('Variant deleted.')
    } catch (err) {
      notifyError(err, 'Could not delete the variant.')
    }
  }

  const addImage = async () => {
    if (!isEdit || !newImageUrl) return
    try {
      const r = await adminApi.post(`/admin/products/${id}/images`, {
        image_url: newImageUrl,
        is_primary: images.length === 0,
      })
      setImages(r.data.images)
      setNewImageUrl('')
      toast.success('Image added.')
    } catch (err) {
      notifyError(err, 'Could not add the image.')
    }
  }

  const deleteImage = async (imgId) => {
    if (!(await confirm({ title: 'Delete this image?', confirmLabel: 'Delete', danger: true }))) return
    try {
      const r = await adminApi.delete(`/admin/products/${id}/images/${imgId}`)
      setImages(r.data.images)
      toast.success('Image deleted.')
    } catch (err) {
      notifyError(err, 'Could not delete the image.')
    }
  }

  if (loading) return <TableSkeleton rows={6} columns={3} />
  if (loadError) return <ErrorState message={loadError} onRetry={() => window.location.reload()} />

  const inputCls =
    'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-gold'

  return (
    <div>
      <button
        onClick={() => navigate('/admin/products')}
        className="mb-4 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
      >
        <IconArrowLeft size={16} /> Back to products
      </button>

      <h1 className="mb-6 text-2xl font-semibold text-gray-900">
        {isEdit ? 'Edit Product' : 'New Product'}
      </h1>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {typeof error === 'string' ? error : JSON.stringify(error)}
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-5 rounded-xl border border-gray-200 bg-white p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">Name *</span>
              <input name="name" value={form.name} onChange={handleChange} required className={inputCls} />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">Slug *</span>
              <input name="slug" value={form.slug} onChange={handleChange} required className={inputCls} />
            </label>
          </div>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Category *</span>
            <select name="category_id" value={form.category_id} onChange={handleChange} required className={inputCls}>
              <option value="">Select category</option>
              {categories.map((root) =>
                root.children?.length > 0 ? (
                  <optgroup key={root.id} label={root.name}>
                    {root.children.map((child) => (
                      <option key={child.id} value={child.id}>{child.name}</option>
                    ))}
                  </optgroup>
                ) : (
                  <option key={root.id} value={root.id}>{root.name}</option>
                )
              )}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Description</span>
            <textarea name="description" value={form.description} onChange={handleChange} rows={4} className={inputCls} />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">MRP (₹) *</span>
              <input name="mrp" type="number" step="0.01" min="1" value={form.mrp} onChange={handleChange} required className={inputCls} />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">Selling Price (₹) *</span>
              <input name="selling_price" type="number" step="0.01" min="1" value={form.selling_price} onChange={handleChange} required className={inputCls} />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">Badge Label</span>
              <input name="badge_label" value={form.badge_label} onChange={handleChange} placeholder="New, Hot, Bestseller" className={inputCls} />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">Badge Class</span>
              <input name="badge_class" value={form.badge_class} onChange={handleChange} placeholder="badge-new, badge-hot" className={inputCls} />
            </label>
          </div>
        </div>

        <div className="space-y-5">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Status</h3>
            <label className="mb-3 flex items-center gap-2">
              <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} className="rounded" />
              <span className="text-sm text-gray-700">Active</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" name="is_featured" checked={form.is_featured} onChange={handleChange} className="rounded" />
              <span className="text-sm text-gray-700">Featured</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-gold py-3 text-sm font-semibold text-white hover:bg-gold-dark disabled:opacity-50"
          >
            {saving ? 'Saving...' : isEdit ? 'Update Product' : 'Create Product'}
          </button>
        </div>
      </form>

      {isEdit && (
        <>
          <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 text-lg font-medium text-gray-900">Variants ({variants.length})</h3>

            {variants.length > 0 && (
              <div className="mb-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs text-gray-400">
                      <th className="pb-2 pr-4 font-medium">Size</th>
                      <th className="pb-2 pr-4 font-medium">Color</th>
                      <th className="pb-2 pr-4 font-medium">Stock</th>
                      <th className="pb-2 pr-4 font-medium">Override ₹</th>
                      <th className="pb-2 pr-4 font-medium">SKU</th>
                      <th className="pb-2 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {variants.map((v) => (
                      <tr key={v.id} className="border-b border-gray-50">
                        <td className="py-2 pr-4 text-gray-900">{v.size}</td>
                        <td className="py-2 pr-4">
                          <span className="flex items-center gap-2">
                            <span className="inline-block h-4 w-4 rounded-full border" style={{ background: v.color_hex }} />
                            {v.color_name}
                          </span>
                        </td>
                        <td className="py-2 pr-4">
                          <div className="flex items-center gap-2">
                            <input
                              type="number" min="0" step="1"
                              aria-label={`Stock for ${v.size} ${v.color_name}`}
                              value={stockDrafts[v.id] ?? v.stock_qty}
                              onChange={(e) => setStockDrafts((d) => ({ ...d, [v.id]: e.target.value }))}
                              className={`w-20 rounded border px-2 py-1 text-sm ${v.stock_qty === 0 ? 'border-red-300 text-red-600' : 'border-gray-200'}`}
                            />
                            {stockDrafts[v.id] != null && String(stockDrafts[v.id]) !== String(v.stock_qty) && (
                              <button
                                type="button" onClick={() => saveStock(v)} disabled={savingVariant === v.id}
                                className="rounded bg-gray-900 px-2.5 py-1 text-xs font-medium text-white hover:bg-black disabled:opacity-60"
                              >
                                {savingVariant === v.id ? 'Saving…' : 'Save'}
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="py-2 pr-4">{v.price_override ?? '-'}</td>
                        <td className="py-2 pr-4 text-gray-400">{v.sku || '-'}</td>
                        <td className="py-2">
                          <button type="button" onClick={() => deleteVariant(v.id)} aria-label={`Delete variant ${v.size} ${v.color_name}`} className="text-red-400 hover:text-red-600">
                            <IconTrash size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex flex-wrap items-end gap-3 border-t border-gray-100 pt-4">
              <label className="block">
                <span className="mb-1 block text-xs text-gray-500">Size</span>
                <input value={newVariant.size} onChange={(e) => setNewVariant((v) => ({ ...v, size: e.target.value }))} placeholder="M" className="w-20 rounded border border-gray-200 px-2 py-1.5 text-sm" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-gray-500">Color</span>
                <input value={newVariant.color_name} onChange={(e) => setNewVariant((v) => ({ ...v, color_name: e.target.value }))} placeholder="Black" className="w-24 rounded border border-gray-200 px-2 py-1.5 text-sm" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-gray-500">Hex</span>
                <input type="color" value={newVariant.color_hex} onChange={(e) => setNewVariant((v) => ({ ...v, color_hex: e.target.value }))} className="h-8 w-10 cursor-pointer rounded border border-gray-200" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-gray-500">Stock</span>
                <input type="number" min="0" value={newVariant.stock_qty} onChange={(e) => setNewVariant((v) => ({ ...v, stock_qty: e.target.value }))} className="w-20 rounded border border-gray-200 px-2 py-1.5 text-sm" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-gray-500">SKU</span>
                <input value={newVariant.sku} onChange={(e) => setNewVariant((v) => ({ ...v, sku: e.target.value }))} placeholder="Optional" className="w-28 rounded border border-gray-200 px-2 py-1.5 text-sm" />
              </label>
              <button
                type="button"
                onClick={addVariant}
                className="flex items-center gap-1 rounded bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-800"
              >
                <IconPlus size={14} /> Add
              </button>
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 text-lg font-medium text-gray-900">Images ({images.length})</h3>

            {images.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-3">
                {images.map((img) => (
                  <div key={img.id} className="group relative">
                    <img
                      src={img.image_url}
                      alt=""
                      className="h-24 w-24 rounded-lg border object-cover"
                    />
                    {img.is_primary && (
                      <span className="absolute left-1 top-1 rounded bg-gold px-1.5 py-0.5 text-[10px] text-white">
                        Primary
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => deleteImage(img.id)}
                      aria-label="Delete image"
                      className="absolute -right-1 -top-1 rounded-full bg-red-500 p-0.5 text-white opacity-0 focus-visible:opacity-100 group-hover:opacity-100"
                    >
                      <IconTrash size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-1 mb-3">
              <button type="button" onClick={() => setImageMode('upload')} className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm ${imageMode === 'upload' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600'}`}>
                <IconUpload size={16} /> Upload
              </button>
              <button type="button" onClick={() => setImageMode('link')} className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm ${imageMode === 'link' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600'}`}>
                <IconLink size={16} /> URL
              </button>
            </div>

            {imageMode === 'upload' ? (
              <div className="flex gap-2">
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  disabled={uploading}
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    setUploading(true)
                    try {
                      const fd = new FormData()
                      fd.append('file', file)
                      const { data: uploadRes } = await adminApi.post('/admin/upload', fd, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                      })
                      const r = await adminApi.post(`/admin/products/${id}/images`, {
                        image_url: uploadRes.url,
                        is_primary: images.length === 0,
                      })
                      setImages(r.data.images)
                    } catch (err) {
                      notifyError(err, 'Upload failed')
                    } finally {
                      setUploading(false)
                      e.target.value = ''
                    }
                  }}
                  className="flex-1 rounded border border-gray-200 px-3 py-1.5 text-sm file:mr-3 file:rounded file:border-0 file:bg-gray-100 file:px-3 file:py-1 file:text-sm file:text-gray-700"
                />
                {uploading && <span className="self-center text-sm text-gray-400">Uploading...</span>}
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  value={newImageUrl}
                  onChange={(e) => setNewImageUrl(e.target.value)}
                  placeholder="https://example.com/image.jpg"
                  className="flex-1 rounded border border-gray-200 px-3 py-1.5 text-sm"
                />
                <button
                  type="button"
                  onClick={addImage}
                  className="flex items-center gap-1 rounded bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-800"
                >
                  <IconPlus size={14} /> Add
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
