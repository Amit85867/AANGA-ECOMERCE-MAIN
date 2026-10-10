import { Link } from 'react-router-dom'
import { IconArrowUpRight } from '@tabler/icons-react'
import { Container } from '@/components/ui/Display'
import SectionHeading from './SectionHeading'
import { useProductStore } from '@/store/useProductStore'
import { useSetting } from '@/store/useSettingsStore'

export default function CategoryGrid() {
  // Loaded by CategoryStrip above; shared through the store, not fetched twice.
  const categories = useProductStore((s) => s.categories).slice(0, 8)
  const s = useSetting()

  if (categories.length === 0) return null

  return (
    <Container as="section" className="py-14 lg:py-20" aria-labelledby="categories-heading">
      <SectionHeading
        id="categories-heading"
        eyebrow={s('section_categories_tag', 'Explore')}
        title={s('section_categories_title', 'Shop by category')}
      />
      <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        {categories.map((cat) => (
          <li key={cat.id}>
            <Link
              to={`/shop?category=${cat.slug}`}
              className="group relative block aspect-[3/4] overflow-hidden rounded-card bg-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            >
              {cat.image_url && (
                <img
                  src={cat.image_url} alt="" width="600" height="800" loading="lazy" decoding="async"
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                />
              )}
              <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 bg-gradient-to-t from-black/80 via-black/30 to-transparent p-4 pt-16">
                <div>
                  <h3 className="display text-lg text-white">{cat.name}</h3>
                  {cat.children?.length > 0 && (
                    <p className="text-xs text-white/80">{cat.children.length} collections</p>
                  )}
                </div>
                <IconArrowUpRight size={20} className="shrink-0 text-white transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </Container>
  )
}
