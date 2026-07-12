import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'

export default function SaleBanner() {
  const [promo, setPromo] = useState(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    apiClient.get('/cms/promo-banners')
      .then((r) => {
        if (r.data.promo_banners?.length) setPromo(r.data.promo_banners[0])
      })
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [])

  if (!loaded || !promo) return null

  const p = promo
  const items = p.items || []

  const titleParts = p.subtitle
    ? p.title.split(p.subtitle)
    : [p.title]

  return (
    <div className="bg-ink text-white px-8 lg:px-12 py-14 grid grid-cols-1 lg:grid-cols-2 gap-14 items-center">
      <div>
        {p.badge_text && (
          <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold">{p.badge_text}</div>
        )}
        <h2 className="font-serif text-4xl lg:text-[44px] leading-[1.1] mt-3">
          {p.subtitle && titleParts.length > 1 ? (
            <>
              {titleParts[0]}<span className="text-gold-light">{p.subtitle}</span>{titleParts[1]}
            </>
          ) : (
            p.title
          )}
        </h2>
        {p.description && (
          <p className="text-[13px] text-white/55 leading-[1.8] mt-3 max-w-[360px]">{p.description}</p>
        )}
        {p.link_url && (
          <Link
            to={p.link_url}
            className="inline-flex items-center gap-2 px-7 py-3 mt-6 text-xs tracking-[1.5px] uppercase font-semibold bg-gold text-ink hover:bg-gold-light transition-colors rounded-sm"
          >
            {p.link_text || 'Shop Now'}
          </Link>
        )}
      </div>
      {items.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {items.map((item, i) => (
            <div key={i} className="bg-white/5 border border-white/10 p-5 text-center">
              <div className="font-serif text-[32px] font-bold text-gold-light">{item.pct}</div>
              <div className="text-[10px] text-white/45 tracking-[1px] mt-0.5 uppercase">{item.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
