import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { IconEdit, IconEyeOff, IconPackage, IconPlus } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/Toast'
import { confirm } from '@/components/admin/confirm'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { inputCls, inr, notifyError } from '@/components/admin/helpers'

const SORTS = [
  ['created_at:desc', 'Newest first'],
  ['created_at:asc', 'Oldest first'],
  ['name:asc', 'Name A–Z'],
  ['selling_price:asc', 'Price low to high'],
  ['selling_price:desc', 'Price high to low'],
]

function flatten(categories, depth = 0, out = []) {
  for (const c of categories) {
    out.push({ id: c.id, name: `${'— '.repeat(depth)}${c.name}` })
    if (c.children?.length) flatten(c.children, depth + 1, out)
  }
  return out
}

export default function AdminProducts() {
  // The search term lives in the URL so a filtered list can be bookmarked and
  // survives going into a product and back.
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') || ''
  const [categoryId, setCategoryId] = useState('')
  const [active, setActive] = useState('')
  const [stock, setStock] = useState('')
  const [sort, setSort] = useState('created_at:desc')
  const [categories, setCategories] = useState([])
  const [busy, setBusy] = useState(null)

  useEffect(() => {
    adminApi.get('/admin/categories')
      .then((r) => setCategories(flatten(r.data.categories)))
      .catch(() => {}) // the filter is optional; the list still works without it
  }, [])

  const [sortBy, dir] = sort.split(':')
  const list = useAdminList('/admin/products', 'products', {
    q, category_id: categoryId, active, stock, sort: sortBy, dir,
  })
  const filtered = Boolean(q || categoryId || active || stock)

  const setSearch = (term) => setSearchParams(term ? { q: term } : {}, { replace: true })

  const deactivate = async (product) => {
    const sure = await confirm({
      title: `Deactivate “${product.name}”?`,
      message: 'It is hidden from the storefront but kept for past orders. You can reactivate it from the product page.',
      confirmLabel: 'Deactivate',
      danger: true,
    })
    if (!sure) return
    setBusy(product.id)
    try {
      await adminApi.delete(`/admin/products/${product.id}`)
      toast.success(`“${product.name}” deactivated.`)
      list.reload()
    } catch (err) {
      notifyError(err, 'Could not deactivate this product.')
    }
    setBusy(null)
  }

  return (
    <div>
      <PageHeading title="Products" subtitle={`${list.total.toLocaleString('en-IN')} matching products`}>
        <Link
          to="/admin/products/new"
          className="inline-flex items-center gap-2 rounded-lg bg-[#C8963E] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#b88534]"
        >
          <IconPlus size={18} /> Add product
        </Link>
      </PageHeading>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto]">
        <SearchInput value={q} onChange={setSearch} placeholder="Search by product name" />
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} aria-label="Category" className={`${inputCls} w-auto`}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select value={active} onChange={(e) => setActive(e.target.value)} aria-label="Visibility" className={`${inputCls} w-auto`}>
          <option value="">Active and inactive</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </select>
        <select value={stock} onChange={(e) => setStock(e.target.value)} aria-label="Stock" className={`${inputCls} w-auto`}>
          <option value="">Any stock level</option>
          <option value="low">Low stock (5 or fewer)</option>
          <option value="out">Out of stock</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className={`${inputCls} w-auto`}>
          {SORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={filtered}
        skeleton={<TableSkeleton rows={8} columns={6} />}
        emptyIcon={IconPackage}
        emptyTitle="No products yet"
        emptyHint="Add your first product to start selling."
        emptyAction={
          <Link to="/admin/products/new" className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black">
            Add product
          </Link>
        }
      >
        <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white ${list.loading ? 'opacity-60' : ''}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="px-6 py-3 font-medium">Product</th>
                <th className="px-6 py-3 font-medium">Category</th>
                <th className="px-6 py-3 text-right font-medium">Price</th>
                <th className="px-6 py-3 text-right font-medium">Stock</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {list.rows.map((p) => {
                const outOfStock = p.total_stock === 0
                const hasEmptyVariant = !outOfStock && p.variants.some((v) => v.stock_qty === 0)
                return (
                  <tr key={p.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                    <td className="px-6 py-3">
                      <Link to={`/admin/products/${p.id}`} className="flex items-center gap-3">
                        {p.images[0] ? (
                          <img
                            src={p.images[0].image_url} alt="" width="40" height="40" loading="lazy"
                            className="h-10 w-10 shrink-0 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-300">
                            <IconPackage size={18} />
                          </div>
                        )}
                        <div className="min-w-0">
                          <div className="truncate font-medium text-gray-900 hover:underline">{p.name}</div>
                          <div className="text-xs text-gray-500">
                            {p.variant_count} variant{p.variant_count === 1 ? '' : 's'}
                            {p.image_count === 0 && <span className="text-amber-700"> · no image</span>}
                            {p.is_featured && <span> · featured</span>}
                          </div>
                        </div>
                      </Link>
                    </td>
                    <td className="px-6 py-3 text-gray-600">{p.category_name || '—'}</td>
                    <td className="px-6 py-3 text-right">
                      <div className="tabular-nums text-gray-900">{inr(p.selling_price)}</div>
                      {p.discount_percent > 0 && (
                        <div className="text-xs tabular-nums text-gray-400 line-through">{inr(p.mrp)}</div>
                      )}
                    </td>
                    <td className="px-6 py-3 text-right">
                      <span className={`tabular-nums ${outOfStock ? 'font-semibold text-red-600' : 'text-gray-900'}`}>
                        {p.total_stock}
                      </span>
                      {hasEmptyVariant && <div className="text-xs text-amber-700">a variant is out</div>}
                    </td>
                    <td className="px-6 py-3">
                      <Badge tone={p.is_active ? 'green' : 'gray'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          to={`/admin/products/${p.id}`} aria-label={`Edit ${p.name}`}
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                        >
                          <IconEdit size={16} />
                        </Link>
                        {p.is_active && (
                          <button
                            type="button" onClick={() => deactivate(p)} disabled={busy === p.id}
                            aria-label={`Deactivate ${p.name}`}
                            className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                          >
                            <IconEyeOff size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="products" />
      </DataState>
    </div>
  )
}
