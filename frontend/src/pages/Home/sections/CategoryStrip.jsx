import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Container } from '@/components/ui/Display'
import { useProductStore } from '@/store/useProductStore'

const chip =
  'shrink-0 rounded-full border px-5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'

/* A quick-jump row of every category, scrollable on small screens. */
export default function CategoryStrip() {
  const categories = useProductStore((s) => s.categories)
  const fetchCategories = useProductStore((s) => s.fetchCategories)

  useEffect(() => { fetchCategories() }, [fetchCategories])

  const flat = categories.flatMap((c) => [c, ...(c.children || [])])

  // The bar is always rendered at its final height, so the page below it does
  // not jump when the categories arrive.
  return (
    <nav aria-label="Categories" className="border-y border-hairline/60 bg-card">
      <Container className="flex min-h-[4.75rem] items-center gap-2 overflow-x-auto py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <Link to="/shop" className={`${chip} border-primary bg-primary text-on-primary`}>All</Link>
        {flat.map((c) => (
          <Link key={c.id} to={`/shop?category=${c.slug}`} className={`${chip} border-hairline text-fg hover:border-primary`}>
            {c.name}
          </Link>
        ))}
      </Container>
    </nav>
  )
}
