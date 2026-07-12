import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'
import { useSetting } from '@/store/useSettingsStore'

const FALLBACK_BG = [
  'from-[#1a1a2e] to-[#16213e]',
  'from-[#4a1942] to-[#8B1A1A]',
  'from-[#1a3a1a] to-[#2d5a2d]',
  'from-[#222] to-[#444]',
]

export default function CategoryGrid() {
  const [categories, setCategories] = useState([])
  const s = useSetting()

  useEffect(() => {
    apiClient.get('/categories')
      .then((r) => {
        const roots = r.data.categories || []
        setCategories(roots.slice(0, 8))
      })
      .catch(() => {})
  }, [])

  if (!categories.length) return null

  return (
    <section className="px-8 lg:px-12 py-14">
      <div className="mb-10">
        <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold mb-2">{s('section_categories_tag', 'Explore')}</div>
        <h2 className="font-serif text-[34px] font-bold">{s('section_categories_title', 'Shop by Category')}</h2>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {categories.map((cat, i) => (
          <Link key={cat.id} to={`/shop?category=${cat.slug}`} className="group rounded overflow-hidden relative aspect-[3/4]">
            {cat.image_url ? (
              <img src={cat.image_url} alt={cat.name} className="w-full h-full object-cover" />
            ) : (
              <div className={`w-full h-full bg-gradient-to-b ${FALLBACK_BG[i % FALLBACK_BG.length]}`} />
            )}
            <div className="absolute bottom-0 inset-x-0 p-5 bg-gradient-to-t from-black/80 to-transparent group-hover:from-maroon/90 transition-colors">
              <div className="font-serif text-xl text-white font-bold">{cat.name}</div>
              {cat.children?.length > 0 && (
                <div className="text-[10px] text-white/55 tracking-[1px] mt-0.5">
                  {cat.children.length} subcategories
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}
