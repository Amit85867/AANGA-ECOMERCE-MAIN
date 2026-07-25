import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'

export default function HeroSection() {
  const [banners, setBanners] = useState([])
  const [current, setCurrent] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    apiClient.get('/cms/banners')
      .then((r) => setBanners(r.data.banners || []))
      .catch(() => {})
      .finally(() => setLoaded(true))

    apiClient.get('/cms/settings')
      .then((r) => {
        const s = r.data.settings
        if (s) setStats({
          happy_customers: s.happy_customers || '50K+',
          styles_available: s.styles_available || '1200+',
          wholesale_partners: s.wholesale_partners || '500+',
        })
      })
      .catch(() => {})
  }, [])

  const next = useCallback(() => {
    if (banners.length > 1) setCurrent((c) => (c + 1) % banners.length)
  }, [banners.length])

  useEffect(() => {
    if (banners.length <= 1) return
    const timer = setInterval(next, 5000)
    return () => clearInterval(timer)
  }, [next, banners.length])

  if (!loaded) {
    return (
      <div className="min-h-[calc(100vh-60px-36px)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!banners.length) return null

  const slide = banners[current]
  const titleLines = (slide.title || '').split('\n')
  const st = stats || { happy_customers: '50K+', styles_available: '1200+', wholesale_partners: '500+' }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[calc(100vh-60px-36px)]">
      {/* Content */}
      <div className="flex flex-col justify-center px-8 py-12 lg:px-12 lg:py-16">
        {slide.subtitle && (
          <div className="text-[10px] tracking-[4px] uppercase text-gold font-semibold mb-4 flex items-center gap-2.5">
            <span className="w-7 h-px bg-gold" />
            {slide.subtitle}
          </div>
        )}
        <h1 className="font-serif text-4xl sm:text-[52px] leading-[1.1] font-bold mb-5">
          {titleLines.map((line, i) => (
            <span key={i}>
              {i === 1 ? <em className="italic text-maroon">{line}</em> : line}
              {i < titleLines.length - 1 && <br />}
            </span>
          ))}
        </h1>
        {slide.description && (
          <p className="text-sm leading-[1.8] text-gray max-w-[400px] mb-8">{slide.description}</p>
        )}
        <div className="flex gap-3 flex-wrap">
          {slide.link_url && (
            <Link to={slide.link_url} className="inline-flex items-center gap-2 px-7 py-3 text-xs tracking-[1.5px] uppercase font-semibold bg-ink text-white hover:bg-maroon transition-colors rounded-sm">
              {slide.link_text || 'Shop Now'}
            </Link>
          )}
          {slide.secondary_link_url && (
            <Link to={slide.secondary_link_url} className="inline-flex items-center gap-2 px-7 py-3 text-xs tracking-[1.5px] uppercase font-semibold border-[1.5px] border-ink text-ink hover:border-gold hover:text-gold transition-colors rounded-sm">
              {slide.secondary_link_text || 'View Offers'}
            </Link>
          )}
        </div>
        <div className="flex gap-8 mt-12 pt-8 border-t border-line">
          {[
            [st.happy_customers, 'Happy Customers'],
            [st.styles_available, 'Styles Available'],
            [st.wholesale_partners, 'Wholesale Partners'],
          ].map(([n, l]) => (
            <div key={l}>
              <div className="font-serif text-[26px] font-bold">{n}</div>
              <div className="text-[10px] text-gray tracking-[1px] uppercase mt-0.5">{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Visual */}
      <div className="hidden lg:flex bg-surface items-center justify-center relative overflow-hidden">
        {slide.image_url ? (
          <img src={slide.image_url} alt={slide.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-[260px] h-[400px] rounded-[140px_140px_80px_80px] bg-gradient-to-br from-maroon to-gold opacity-[0.18]" />
        )}

        {/* Decorative "pill" badge — small label + value */}
        {slide.pill_value && (
          <div className="absolute bottom-[60px] left-10 bg-white px-[18px] py-3.5 border-l-[3px] border-gold shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
            {slide.pill_label && (
              <div className="text-[9px] tracking-[2px] uppercase text-gray">{slide.pill_label}</div>
            )}
            <div className="font-serif text-base font-bold mt-[3px]">{slide.pill_value}</div>
          </div>
        )}

        {/* Decorative "chip" badge — big value + small label */}
        {slide.chip_value && (
          <div className="absolute top-12 right-8 bg-ink text-white px-5 py-4 text-center">
            <div className="font-serif text-[32px] font-bold text-gold leading-none">{slide.chip_value}</div>
            {slide.chip_label && (
              <div className="text-[9px] tracking-[2px] uppercase opacity-60 mt-0.5">{slide.chip_label}</div>
            )}
          </div>
        )}

        {/* Slider dots */}
        {banners.length > 1 && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2">
            {banners.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`w-2.5 h-2.5 rounded-full transition-colors ${i === current ? 'bg-gold' : 'bg-white/40 hover:bg-white/70'}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
