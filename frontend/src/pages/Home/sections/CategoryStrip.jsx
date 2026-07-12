import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'

export default function CategoryStrip() {
  const [categories, setCategories] = useState([])

  useEffect(() => {
    apiClient.get('/categories')
      .then((r) => {
        const roots = r.data.categories || []
        const flat = []
        const flatten = (cats) => {
          for (const c of cats) {
            flat.push(c)
            if (c.children?.length) flatten(c.children)
          }
        }
        flatten(roots)
        setCategories(flat)
      })
      .catch(() => {})
  }, [])

  const chips = ['All', ...categories.map((c) => c.name)]

  return (
    <div className="flex gap-4 px-8 lg:px-12 py-10 overflow-x-auto scrollbar-none">
      {chips.map((c, i) => (
        <Link
          key={c}
          to={i === 0 ? '/shop' : `/shop?category=${categories[i - 1]?.slug || ''}`}
          className={`shrink-0 px-6 py-2.5 border-[1.5px] rounded-full text-xs font-medium transition-colors ${
            i === 0
              ? 'border-gold bg-gold text-white'
              : 'border-line text-ink hover:border-gold hover:bg-gold hover:text-white'
          }`}
        >
          {c}
        </Link>
      ))}
    </div>
  )
}
