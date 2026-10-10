import { useCallback, useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import { Container } from '@/components/ui/Display'
import { useSetting } from '@/store/useSettingsStore'

const ROTATE_MS = 6000

// What the hero shows before the CMS answers, and if no banner is published.
// The page's largest element must not wait on a network request to exist.
const FALLBACK = {
  subtitle: 'New season',
  title: 'Style that speaks for itself',
  description: 'Thoughtfully made clothing for men, women and kids — delivered across India.',
  link_url: '/shop',
  link_text: 'Shop the collection',
}

export default function HeroSection() {
  const [banners, setBanners] = useState([])
  const [current, setCurrent] = useState(0)
  const [paused, setPaused] = useState(false)
  const s = useSetting()

  useEffect(() => {
    apiClient.get('/cms/banners')
      .then((r) => setBanners(r.data.banners || []))
      .catch(() => {}) // the fallback hero stays
  }, [])

  const next = useCallback(
    () => setCurrent((c) => (banners.length ? (c + 1) % banners.length : 0)),
    [banners.length],
  )

  // Auto-advance, but not while someone is reading or interacting with it, and
  // not at all for visitors who asked their system to reduce motion.
  useEffect(() => {
    if (banners.length <= 1 || paused) return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const timer = setInterval(next, ROTATE_MS)
    return () => clearInterval(timer)
  }, [next, banners.length, paused])

  const slide = banners[current] || FALLBACK
  const stats = [
    [s('happy_customers', '50K+'), 'Happy customers'],
    [s('styles_available', '1200+'), 'Styles'],
    [s('wholesale_partners', '500+'), 'Wholesale partners'],
  ]

  return (
    <section
      aria-roledescription="carousel" aria-label="Featured"
      className="bg-bg"
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}
    >
      <Container className="grid items-center gap-8 py-8 lg:grid-cols-2 lg:gap-14 lg:py-14">
        <div className="order-2 lg:order-1">
          {slide.subtitle && (
            <p className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">{slide.subtitle}</p>
          )}
          <h1 className="display mt-3 text-4xl leading-[1.05] text-fg sm:text-5xl lg:text-6xl">
            {(slide.title || '').split('\n').map((line, i) => (
              <span key={i} className="block">{line}</span>
            ))}
          </h1>
          {slide.description && (
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted">{slide.description}</p>
          )}
          <div className="mt-8 flex flex-wrap gap-3">
            <Button to={slide.link_url || '/shop'} size="lg">{slide.link_text || 'Shop now'}</Button>
            {slide.secondary_link_url && (
              <Button to={slide.secondary_link_url} size="lg" variant="secondary">
                {slide.secondary_link_text || 'View offers'}
              </Button>
            )}
          </div>

          <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-hairline/60 pt-6">
            {stats.map(([value, label]) => (
              <div key={label}>
                <dd className="display text-2xl text-fg">{value}</dd>
                <dt className="mt-1 text-xs text-muted">{label}</dt>
              </div>
            ))}
          </dl>
        </div>

        {/* Fixed aspect ratio: the space is reserved before the image arrives. */}
        <div className="relative order-1 aspect-[4/5] overflow-hidden rounded-block bg-fill sm:aspect-[16/11] lg:order-2 lg:aspect-[4/5]">
          {slide.image_url && (
            <img
              key={slide.image_url}
              src={slide.image_url} alt="" width="960" height="1200"
              fetchPriority="high" decoding="async"
              className="h-full w-full object-cover"
            />
          )}

          {slide.pill_value && (
            <div className="absolute bottom-5 left-5 rounded-card bg-card/95 px-4 py-3 shadow-card backdrop-blur">
              {slide.pill_label && <p className="text-xs uppercase tracking-[0.08em] text-muted">{slide.pill_label}</p>}
              <p className="display text-base text-fg">{slide.pill_value}</p>
            </div>
          )}
          {slide.chip_value && (
            <div className="absolute right-5 top-5 rounded-card bg-accent px-4 py-3 text-center text-on-primary shadow-card">
              <p className="display text-2xl leading-none">{slide.chip_value}</p>
              {slide.chip_label && <p className="mt-1 text-xs font-medium">{slide.chip_label}</p>}
            </div>
          )}

          {banners.length > 1 && (
            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-1 rounded-full bg-black/40 px-2 py-1.5 backdrop-blur">
              {banners.map((b, i) => (
                <button
                  key={b.id} type="button" onClick={() => setCurrent(i)}
                  aria-label={`Show slide ${i + 1} of ${banners.length}`}
                  aria-current={i === current ? 'true' : undefined}
                  className="flex h-6 w-6 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                >
                  <span className={`h-2 rounded-full transition-all ${i === current ? 'w-5 bg-white' : 'w-2 bg-white/60'}`} />
                </button>
              ))}
            </div>
          )}
        </div>
      </Container>
    </section>
  )
}
