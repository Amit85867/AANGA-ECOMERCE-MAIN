import { useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import { useSetting } from '@/store/useSettingsStore'

function ReviewCard({ r }) {
  const initials = r.name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div className="bg-surface p-7 relative">
      <div className="font-serif text-5xl text-gold leading-none mb-3 opacity-30">"</div>
      <p className="text-[13px] leading-[1.8] italic">{r.quote}</p>
      <div className="flex items-center gap-2.5 mt-5">
        {r.avatar_url ? (
          <img src={r.avatar_url} alt={r.name} className="w-10 h-10 rounded-full object-cover shrink-0" />
        ) : (
          <div className="w-10 h-10 rounded-full bg-ink flex items-center justify-center text-gold font-bold text-xs shrink-0">{initials}</div>
        )}
        <div>
          <div className="font-semibold text-[13px]">{r.name}</div>
          {r.location && <div className="text-[11px] text-gray">{r.location}</div>}
          <div className="text-gold text-[11px] mt-0.5">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</div>
        </div>
      </div>
    </div>
  )
}

export default function Reviews() {
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [showMore, setShowMore] = useState(false)
  const s = useSetting()

  useEffect(() => {
    apiClient.get('/cms/testimonials')
      .then(({ data }) => setItems(data.testimonials || []))
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [])

  if (!loaded || items.length === 0) return null

  // Best reviews (4–5★) shown up front; the rest sit behind "View more".
  const featured = items.filter((r) => r.rating >= 4)
  const rest = items.filter((r) => r.rating < 4)
  const primary = featured.length > 0 ? featured : items
  const secondary = featured.length > 0 ? rest : []

  return (
    <section className="px-8 lg:px-12 py-14">
      <div className="text-center mb-10">
        <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold mb-2">{s('testimonials_tag', 'Testimonials')}</div>
        <h2 className="font-serif text-[34px] font-bold">{s('testimonials_title', 'What Customers Say')}</h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {primary.map((r) => <ReviewCard key={r.id} r={r} />)}
      </div>

      {showMore && secondary.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          {secondary.map((r) => <ReviewCard key={r.id} r={r} />)}
        </div>
      )}

      {secondary.length > 0 && (
        <div className="text-center mt-8">
          <button
            onClick={() => setShowMore((v) => !v)}
            className="inline-flex items-center gap-2 px-7 py-3 text-xs tracking-[1.5px] uppercase font-semibold border-[1.5px] border-ink text-ink hover:border-gold hover:text-gold transition-colors rounded-sm"
          >
            {showMore ? 'Show Less' : `View More Reviews (${secondary.length})`}
          </button>
        </div>
      )}
    </section>
  )
}
