import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { IconArrowLeft, IconExternalLink, IconPlus, IconStack2, IconTrash } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, CardSkeleton, TableSkeleton } from '@/components/admin/DataState'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { confirm } from '@/components/admin/confirm'
import { inputCls, inr, notifyError } from '@/components/admin/helpers'
import { Field, ImageField, MoveButtons, Toggle } from '@/components/admin/kit'
import { btnGhost, btnPrimary, cardCls, fieldErrors, moveItem, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

function CollectionList() {
  const { data, loading, error, reload } = useLoad('/admin/collections')
  const rows = data?.collections || []

  const remove = async (c) => {
    if (!(await confirm({
      title: `Delete “${c.name}”?`, confirmLabel: 'Delete', danger: true,
      message: 'The collection page disappears. The products themselves are not touched.',
    }))) return
    try {
      await adminApi.delete(`/admin/collections/${c.id}`)
      toast.success('Deleted.')
      reload()
    } catch (err) {
      notifyError(err, 'Could not delete this collection.')
    }
  }

  return (
    <div>
      <PageHeading title="Collections" subtitle="Hand-picked groups of products — for the home page, a banner, or a campaign.">
        <Link to="/admin/collections/new" className={btnPrimary}><IconPlus size={18} /> New collection</Link>
      </PageHeading>
      {loading && !data ? <TableSkeleton rows={4} columns={4} /> : error ? <ErrorState message={error} onRetry={reload} /> : rows.length === 0 ? (
        <EmptyState icon={IconStack2} title="No collections yet" hint="Make one — for example “Diwali Edit” — and choose the products that belong in it." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="px-6 py-3 font-medium">Collection</th>
                <th className="px-6 py-3 font-medium">Products</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3">
                    <Link to={`/admin/collections/${c.id}`} className="font-medium text-gray-900 hover:underline">{c.name}</Link>
                    {c.is_demo && <span className="ml-2"><Badge tone="purple">Demo</Badge></span>}
                    <div className="text-xs text-gray-500">/collections/{c.slug}</div>
                  </td>
                  <td className="px-6 py-3 tabular-nums text-gray-700">{c.product_count}</td>
                  <td className="px-6 py-3"><Badge tone={c.is_active ? 'green' : 'gray'}>{c.is_active ? 'Visible' : 'Hidden'}</Badge></td>
                  <td className="px-6 py-3">
                    <div className="flex justify-end gap-1">
                      <Link to={`/admin/collections/${c.id}`} className={`${btnGhost} px-3 py-1.5`}>Edit</Link>
                      <button type="button" onClick={() => remove(c)} aria-label={`Delete ${c.name}`} title="Delete" className="rounded p-2 text-gray-500 hover:bg-red-50 hover:text-red-600"><IconTrash size={17} /></button>
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

function ProductPicker({ chosen, onAdd }) {
  const [q, setQ] = useState('')
  const { data, loading } = useLoad('/admin/products', { q, per_page: 12, active: 'true' })
  const taken = new Set(chosen.map((p) => p.id))
  return (
    <div>
      <SearchInput value={q} onChange={setQ} placeholder="Search products to add" />
      <ul className="mt-3 max-h-80 divide-y divide-gray-100 overflow-y-auto rounded-lg border border-gray-100">
        {loading && !data && <li className="px-3 py-3 text-sm text-gray-500">Loading…</li>}
        {(data?.products || []).map((p) => (
          <li key={p.id} className="flex items-center gap-3 px-3 py-2">
            <div className="h-10 w-10 shrink-0 overflow-hidden rounded bg-gray-100">
              {p.primary_image && <img src={p.primary_image} alt="" loading="lazy" className="h-full w-full object-cover" />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm text-gray-900">{p.name}</div>
              <div className="text-xs text-gray-500">{p.category_name} · {inr(p.selling_price)}</div>
            </div>
            <button
              type="button" disabled={taken.has(p.id)} className={`${btnGhost} px-3 py-1.5`}
              onClick={() => onAdd({ id: p.id, name: p.name, slug: p.slug, selling_price: p.selling_price, image_url: p.primary_image, is_active: p.is_active })}
              aria-label={`Add ${p.name}`}
            >
              {taken.has(p.id) ? 'Added' : 'Add'}
            </button>
          </li>
        ))}
        {data && data.products.length === 0 && <li className="px-3 py-3 text-sm text-gray-500">No products match.</li>}
      </ul>
    </div>
  )
}

function CollectionEditor({ id }) {
  const isNew = id === 'new'
  const navigate = useNavigate()
  const { data, loading, error, reload } = useLoad(isNew ? null : `/admin/collections/${id}`)
  const [form, setForm] = useState(isNew ? {
    name: '', slug: '', description: '', image_url: '', is_active: true, meta_title: '', meta_description: '', share_image_url: '',
  } : null)
  const [products, setProducts] = useState([])
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setForm({
      name: data.name, slug: data.slug, description: data.description || '', image_url: data.image_url || '',
      is_active: data.is_active, meta_title: data.meta_title || '', meta_description: data.meta_description || '',
      share_image_url: data.share_image_url || '',
    })
    setProducts(data.products)
  }, [data])

  const save = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    const body = {
      name: form.name, slug: form.slug || null, description: form.description || null, image_url: form.image_url || null,
      is_active: form.is_active, meta_title: form.meta_title || null, meta_description: form.meta_description || null,
      share_image_url: form.share_image_url || null, product_ids: products.map((p) => p.id),
    }
    try {
      if (isNew) {
        const { data: created } = await adminApi.post('/admin/collections', body)
        toast.success('Collection created.')
        navigate(`/admin/collections/${created.id}`, { replace: true })
      } else {
        await adminApi.put(`/admin/collections/${id}`, body)
        toast.success('Collection saved.')
        reload()
      }
      setErrors({})
    } catch (err) {
      setErrors(fieldErrors(err))
      notifyError(err, 'Could not save this collection.')
    } finally {
      setSaving(false)
    }
  }

  const back = (
    <Link to="/admin/collections" className="mb-3 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900">
      <IconArrowLeft size={16} /> All collections
    </Link>
  )
  if (!isNew && loading && !data) return <>{back}<CardSkeleton className="h-96" /></>
  if (error) return <>{back}<ErrorState message={error} onRetry={reload} /></>
  if (!form) return null

  return (
    <form onSubmit={save}>
      {back}
      <PageHeading title={isNew ? 'New collection' : form.name} subtitle={isNew ? 'Name it, then add the products.' : `/collections/${form.slug}`}>
        {!isNew && form.is_active && (
          <a href={`/collections/${form.slug}`} target="_blank" rel="noreferrer" className={btnGhost}><IconExternalLink size={16} /> View in store</a>
        )}
        <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Saving…' : isNew ? 'Create collection' : 'Save collection'}</button>
      </PageHeading>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section className={`${cardCls} space-y-4`}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Name *" error={errors.name}>
                <input required maxLength={80} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} />
              </Field>
              <Field label="Web address" error={errors.slug} help={isNew ? 'Leave empty to make it from the name.' : 'Changing this breaks links people have already shared.'}>
                <input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase() })} placeholder="diwali-edit" className={inputCls} />
              </Field>
            </div>
            <Field label="Description" help="One or two lines shown at the top of the collection page." error={errors.description}>
              <textarea rows={2} maxLength={500} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inputCls} />
            </Field>
            <Toggle label="Visible in the store" checked={form.is_active} onChange={(on) => setForm({ ...form, is_active: on })} />
          </section>

          <section className={cardCls} aria-label="Products in this collection">
            <h2 className="mb-1 font-medium text-gray-900">Products in this collection ({products.length})</h2>
            <p className="mb-4 text-xs text-gray-500">Shown in this order. {errors.product_ids && <span className="text-red-700">{errors.product_ids}</span>}</p>
            {products.length === 0 ? <p className="text-sm text-gray-500">None yet. Search on the right and press Add.</p> : (
              <ol className="divide-y divide-gray-100">
                {products.map((p, index) => (
                  <li key={p.id} className="flex items-center gap-3 py-2">
                    <span className="w-6 text-right text-xs tabular-nums text-gray-500">{index + 1}</span>
                    <div className="h-10 w-10 shrink-0 overflow-hidden rounded bg-gray-100">
                      {p.image_url && <img src={p.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm text-gray-900">{p.name}</div>
                      <div className="text-xs text-gray-500">{inr(p.selling_price)}{p.is_active ? '' : ' · inactive, not shown in the store'}</div>
                    </div>
                    <MoveButtons index={index} count={products.length} onMove={(from, to) => setProducts(moveItem(products, from, to))} label={p.name} />
                    <button type="button" onClick={() => setProducts(products.filter((x) => x.id !== p.id))} aria-label={`Remove ${p.name}`} title="Remove" className="rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600"><IconTrash size={16} /></button>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        <div className="space-y-6">
          <section className={cardCls}>
            <h2 className="mb-3 font-medium text-gray-900">Add products</h2>
            <ProductPicker chosen={products} onAdd={(p) => setProducts([...products, p])} />
          </section>
          <section className={`${cardCls} space-y-4`}>
            <h2 className="font-medium text-gray-900">Picture, search and sharing</h2>
            <ImageField label="Collection picture" value={form.image_url} error={errors.image_url} onChange={(url) => setForm({ ...form, image_url: url })} />
            <Field label="Title in search results" help="Up to 70 characters." error={errors.meta_title}>
              <input maxLength={70} value={form.meta_title} onChange={(e) => setForm({ ...form, meta_title: e.target.value })} className={inputCls} />
            </Field>
            <Field label="Description in search results" error={errors.meta_description}>
              <textarea rows={2} maxLength={200} value={form.meta_description} onChange={(e) => setForm({ ...form, meta_description: e.target.value })} className={inputCls} />
            </Field>
            <ImageField label="Image when shared" value={form.share_image_url} error={errors.share_image_url} onChange={(url) => setForm({ ...form, share_image_url: url })} />
          </section>
        </div>
      </div>
    </form>
  )
}

export default function AdminCollections() {
  const { id } = useParams()
  return id ? <CollectionEditor key={id} id={id} /> : <CollectionList />
}
