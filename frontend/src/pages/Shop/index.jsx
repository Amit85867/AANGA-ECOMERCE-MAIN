import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { IconAdjustmentsHorizontal } from '@tabler/icons-react'
import { useProductStore } from '@/store/useProductStore'
import ProductCard from '@/components/ui/ProductCard'
import PageHeader from '@/components/ui/PageHeader'
import Seo from '@/components/Seo'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const FILTER_COLORS = ['#0A0A0A', '#fff', '#8B1A1A', '#1a2a4a', '#C8963E', '#1a3a1a']

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest First' },
  { value: 'popular', label: 'Most Popular' },
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc', label: 'Price: High to Low' },
]

// Upper bound of the price filter. Must stay above the dearest product or that
// product becomes unreachable from Shop -- raise it when the catalogue does.
const PRICE_CEILING = 15000

export default function Shop() {
  const [searchParams] = useSearchParams()
  const { products, loading, loadingMore, total, page, pages, fetchProducts, categories, fetchCategories } = useProductStore()

  const [sort, setSort] = useState('newest')
  // Start at the ceiling so the filter is inert until the shopper moves it.
  // Defaulting mid-range silently hid every product above it -- the premium
  // end of the catalogue was unreachable from Shop at all.
  const [priceRange, setPriceRange] = useState(PRICE_CEILING)
  const [activeSize, setActiveSize] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)

  const buildParams = (pageNum) => {
    const params = { page: pageNum, per_page: 12, sort }
    if (priceRange < PRICE_CEILING) params.max_price = priceRange
    const q = searchParams.get('q')
    if (q) params.q = q
    if (selectedCategory) params.category = selectedCategory
    return params
  }

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  // Any filter/sort/search change resets back to the first page (replace).
  useEffect(() => {
    fetchProducts(buildParams(1))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort, priceRange, selectedCategory, searchParams, fetchProducts])

  const loadMore = () => fetchProducts(buildParams(page + 1), true)

  return (
    <>
      <Seo
        title="Shop All Products"
        description="Browse the full AANGA collection — clothing, accessories and more for men, women and kids, with fast delivery across India."
      />
      <PageHeader title="All Products" crumbs={[{ label: 'Home', to: '/' }, { label: 'Shop' }]} />
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] flex-1">
        {/* Sidebar */}
        <aside className="border-r border-line p-5 bg-white hidden lg:block">
          <div className="text-[11px] tracking-[2px] uppercase font-bold mb-4 pb-3 border-b border-line flex items-center gap-1.5">
            <IconAdjustmentsHorizontal size={14} /> Filters
          </div>

          <div className="mb-5">
            <h4 className="text-[11px] font-semibold mb-2.5 tracking-[0.5px] uppercase text-gray">Category</h4>
            <label className="flex items-center gap-2 mb-1.5 text-xs cursor-pointer">
              <input
                type="radio"
                name="category"
                checked={!selectedCategory}
                onChange={() => setSelectedCategory(null)}
                className="accent-gold"
              /> All
            </label>
            {categories.map((c) => (
              <label key={c.id} className="flex items-center gap-2 mb-1.5 text-xs cursor-pointer">
                <input
                  type="radio"
                  name="category"
                  checked={selectedCategory === c.slug}
                  onChange={() => setSelectedCategory(c.slug)}
                  className="accent-gold"
                /> {c.name}
              </label>
            ))}
          </div>

          <div className="mb-5">
            <h4 className="text-[11px] font-semibold mb-2.5 tracking-[0.5px] uppercase text-gray">Price Range</h4>
            <input type="range" min="0" max={PRICE_CEILING} step="100" value={priceRange} onChange={(e) => setPriceRange(Number(e.target.value))} className="w-full accent-gold mb-1.5" />
            <div className="flex justify-between text-[11px] text-gray">
              <span>&#8377;0</span>
              <span>{priceRange >= PRICE_CEILING ? 'Any' : `₹${priceRange.toLocaleString('en-IN')}`}</span>
            </div>
          </div>

          <div className="mb-5">
            <h4 className="text-[11px] font-semibold mb-2.5 tracking-[0.5px] uppercase text-gray">Size</h4>
            <div className="flex flex-wrap gap-1.5">
              {SIZES.map((s) => (
                <button key={s} onClick={() => setActiveSize(activeSize === s ? null : s)} className={`w-9 h-9 text-[11px] font-medium border transition-colors ${activeSize === s ? 'border-gold bg-gold text-ink' : 'border-line hover:border-gold'}`}>{s}</button>
              ))}
            </div>
          </div>

          <div className="mb-5">
            <h4 className="text-[11px] font-semibold mb-2.5 tracking-[0.5px] uppercase text-gray">Colour</h4>
            <div className="flex flex-wrap gap-2">
              {FILTER_COLORS.map((c) => (
                <button key={c} className="w-6 h-6 rounded-full border-[3px] border-transparent hover:border-gold transition-colors" style={{ background: c, boxShadow: c === '#fff' ? 'inset 0 0 0 1px #ddd' : 'none' }} />
              ))}
            </div>
          </div>
        </aside>

        {/* Main */}
        <div className="p-6 lg:p-8">
          <div className="flex items-center justify-between mb-5">
            <span className="text-xs text-gray">
              {loading ? 'Loading…' : `Showing ${products.length} of ${total} products`}
            </span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="py-2 px-3 border border-line text-xs bg-white text-ink cursor-pointer"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {loading ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="border border-line rounded overflow-hidden animate-pulse">
                  <div className="aspect-[3/4] bg-surface" />
                  <div className="p-3.5 space-y-2">
                    <div className="h-3 bg-surface rounded w-1/2" />
                    <div className="h-4 bg-surface rounded w-3/4" />
                    <div className="h-4 bg-surface rounded w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-gray text-sm">No products found.</p>
              <p className="text-xs text-gray mt-1">Try adjusting your filters or add products from the admin dashboard.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {products.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          )}

          {/* Load more */}
          {!loading && page < pages && (
            <div className="flex justify-center mt-10">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="px-8 py-3 text-xs font-semibold uppercase tracking-[1px] border border-ink text-ink hover:bg-ink hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loadingMore ? 'Loading…' : `Load More (${total - products.length} left)`}
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
