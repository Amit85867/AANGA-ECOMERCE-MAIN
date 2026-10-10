import { useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import ProductCard from '@/components/ui/ProductCard'
import Button from '@/components/ui/Button'
import { Container, ProductCardSkeleton } from '@/components/ui/Display'
import SectionHeading from './SectionHeading'
import { useSetting } from '@/store/useSettingsStore'

export default function ProductGrid() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const s = useSetting()

  // The heading promises curation ("Best sellers"), so ask for the products the
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
              .then(({ data: fallback }) => fallback.products),
      )
      .then((items) => { if (!cancelled) setProducts(items) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (!loading && products.length === 0) return null

  return (
    <Container as="section" className="pb-14 lg:pb-20" aria-labelledby="products-heading">
      <SectionHeading
        id="products-heading"
        eyebrow={s('section_products_tag', 'Trending now')}
        title={s('section_products_title', 'Best sellers')}
      >
        <Button to="/shop" variant="secondary" size="sm">View all</Button>
      </SectionHeading>

      <ul className="grid grid-cols-2 gap-x-4 gap-y-8 sm:gap-x-6 lg:grid-cols-4">
        {loading
          ? Array.from({ length: 8 }).map((_, i) => <li key={i}><ProductCardSkeleton /></li>)
          : products.map((p) => <li key={p.id}><ProductCard product={p} /></li>)}
      </ul>
    </Container>
  )
}
