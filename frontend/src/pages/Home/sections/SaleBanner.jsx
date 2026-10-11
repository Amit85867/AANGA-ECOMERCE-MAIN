import { useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import { Container } from '@/components/ui/Display'
import { useCampaignEpoch } from '@/store/useLayoutStore'

/* The promotional block set up under Admin → Promo Banners. */
export default function SaleBanner() {
  const [promo, setPromo] = useState(null)
  const epoch = useCampaignEpoch()

  useEffect(() => {
    apiClient.get('/cms/promo-banners')
      .then((r) => setPromo(r.data.promo_banners?.[0] || null))
      .catch(() => {})
  }, [epoch])

  if (!promo) return null
  const items = promo.items || []

  return (
    <Container as="section" className="pb-14 lg:pb-20" aria-labelledby="promo-heading">
      <div className="grid items-center gap-10 rounded-block bg-primary px-6 py-10 text-on-primary sm:px-10 lg:grid-cols-2 lg:px-14 lg:py-14">
        <div>
          {promo.badge_text && (
            <p className="inline-block rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold uppercase tracking-[0.08em] text-fg">
              {promo.badge_text}
            </p>
          )}
          <h2 id="promo-heading" className="display mt-4 text-3xl leading-tight sm:text-4xl lg:text-5xl">{promo.title}</h2>
          {promo.description && (
            <p className="mt-4 max-w-md text-sm leading-relaxed text-white/80">{promo.description}</p>
          )}
          {promo.link_url && (
            <Button to={promo.link_url} size="lg" className="mt-7 !bg-white !text-black hover:!bg-white/90">
              {promo.link_text || 'Shop now'}
            </Button>
          )}
        </div>

        {items.length > 0 && (
          <ul className="grid grid-cols-2 gap-3">
            {items.map((item) => (
              <li key={item.label} className="rounded-card border border-white/15 bg-white/5 p-5 text-center">
                <p className="display text-3xl">{item.pct}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.08em] text-white/80">{item.label}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Container>
  )
}
