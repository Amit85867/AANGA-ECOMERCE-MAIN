import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'
import ProductCard from '@/components/ui/ProductCard'
import { useSetting } from '@/store/useSettingsStore'

export default function ProductGrid() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const s = useSetting()

  // The heading promises curation ("Best Sellers"), so ask for the products the
  // admin actually flagged as featured. Falls back to newest so a catalogue
  // with nothing featured yet still fills the grid instead of vanishing.
  useEffect(() => {
    let cancelled = false
    apiClient
      .get('/products', { params: { per_page: 8, featured: true } })
      .then(({ data }) =>
        data.products.length
          ? data.products
          : apiClient
              .get('/products', { params: { per_page: 8, sort: 'newest' } })
              .then(({ data: fallback }) => fallback.products)
      )
      .then((items) => {
        if (!cancelled) setProducts(items)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <section className="px-8 lg:px-12 pb-14">
        <div className="mb-10">
          <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold mb-2">{s('section_products_tag', 'Trending Now')}</div>
          <h2 className="font-serif text-[34px] font-bold">{s('section_products_title', 'Best Sellers')}</h2>
        </div>
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
      </section>
    )
  }

  if (products.length === 0) return null

  return (
    <section className="px-8 lg:px-12 pb-14">
      <div className="mb-10">
        <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold mb-2">{s('section_products_tag', 'Trending Now')}</div>
        <h2 className="font-serif text-[34px] font-bold">{s('section_products_title', 'Best Sellers')}</h2>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
      <div className="text-center mt-8">
        <Link to="/shop" className="inline-flex items-center gap-2 px-7 py-3 text-xs tracking-[1.5px] uppercase font-semibold border-[1.5px] border-ink text-ink hover:border-gold hover:text-gold transition-colors rounded-sm">
          View All Products →
        </Link>
      </div>
    </section>
  )
}
