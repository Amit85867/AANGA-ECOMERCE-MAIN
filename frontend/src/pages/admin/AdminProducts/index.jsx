import { useEffect, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { confirm } from '@/components/admin/confirm'
import { IconPlus, IconSearch, IconEdit, IconTrash } from '@tabler/icons-react'

export default function AdminProducts() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [products, setProducts] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState(searchParams.get('q') || '')
  const [loading, setLoading] = useState(true)

  const fetchProducts = useCallback(
    (pg = 1, q = search) => {
      setLoading(true)
      const params = { page: pg, per_page: 20 }
      if (q) params.q = q
      adminApi
        .get('/admin/products', { params })
        .then((r) => {
          setProducts(r.data.products)
          setPage(r.data.page)
          setPages(r.data.pages)
          setTotal(r.data.total)
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    },
    [search],
  )

  useEffect(() => {
    fetchProducts()
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    setSearchParams(search ? { q: search } : {})
    fetchProducts(1, search)
  }

  const handleDeactivate = async (id) => {
    if (!(await confirm({ title: 'Deactivate this product?', message: 'It is hidden from the storefront but kept for past orders. You can reactivate it later.', confirmLabel: 'Deactivate', danger: true }))) return
    await adminApi.delete(`/admin/products/${id}`)
    fetchProducts(page)
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Products ({total})</h1>
        <Link
          to="/admin/products/new"
          className="inline-flex items-center gap-2 rounded-lg bg-[#C8963E] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#b88534]"
        >
          <IconPlus size={18} />
          Add Product
        </Link>
      </div>

      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <div className="relative flex-1">
          <IconSearch size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products..."
            className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-[#C8963E]"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-gray-900 px-4 text-sm text-white hover:bg-gray-800"
        >
          Search
        </button>
      </form>

      {loading ? (
        <div className="py-20 text-center text-gray-400">Loading...</div>
      ) : products.length === 0 ? (
        <div className="py-20 text-center text-gray-400">No products found</div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                  <th className="px-6 py-3 font-medium">Product</th>
                  <th className="px-6 py-3 font-medium">Category</th>
                  <th className="px-6 py-3 font-medium">Price</th>
                  <th className="px-6 py-3 font-medium">Stock</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-b border-gray-50 last:border-0">
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-3">
                        {p.images[0] ? (
                          <img
                            src={p.images[0].image_url}
                            alt=""
                            className="h-10 w-10 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 text-xs text-gray-400">
                            N/A
                          </div>
                        )}
                        <div>
                          <div className="font-medium text-gray-900">{p.name}</div>
                          <div className="text-xs text-gray-400">{p.variant_count} variants</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3 text-gray-600">{p.category_name}</td>
                    <td className="px-6 py-3">
                      <div className="text-gray-900">₹{p.selling_price.toLocaleString('en-IN')}</div>
                      {p.discount_percent > 0 && (
                        <div className="text-xs text-gray-400 line-through">
                          ₹{p.mrp.toLocaleString('en-IN')}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`text-sm ${p.total_stock === 0 ? 'font-medium text-red-500' : 'text-gray-700'}`}
                      >
                        {p.total_stock}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}
                      >
                        {p.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-1">
                        <Link
                          to={`/admin/products/${p.id}`}
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                        >
                          <IconEdit size={16} />
                        </Link>
                        {p.is_active && (
                          <button
                            onClick={() => handleDeactivate(p.id)}
                            className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
                          >
                            <IconTrash size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => fetchProducts(p)}
                  className={`h-9 min-w-9 rounded-lg px-3 text-sm ${p === page ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
