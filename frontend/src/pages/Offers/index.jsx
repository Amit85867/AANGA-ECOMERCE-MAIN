import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconTag } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import apiClient from '@/services/apiClient'

const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : null

const discountLabel = (o) => {
  if (o.offer_type === 'free_shipping') return 'FREE SHIP'
  if (o.offer_type === 'bogo') return 'BOGO'
  if (o.discount_percent) return `${Math.round(o.discount_percent)}% OFF`
  if (o.offer_type === 'flat_off') return 'FLAT OFF'
  return 'OFFER'
}

export default function Offers() {
  const [offers, setOffers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get('/offers')
      .then(({ data }) => setOffers(data.offers || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <PageHeader title="Offers & Deals" crumbs={[{ label: 'Home', to: '/' }, { label: 'Offers' }]} />

      {/* Sale Banner */}
      <section className="bg-ink mx-6 lg:mx-12 mt-8 p-8 text-center">
        <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold mb-2">Limited Time</div>
        <h2 className="font-serif text-3xl text-white font-bold">Season Sale is Live Now</h2>
        <p className="text-[13px] text-white/50 mt-2">Grab the latest deals below before they're gone.</p>
      </section>

      {/* Offers */}
      <section className="px-6 lg:px-12 py-10">
        <h2 className="font-serif text-2xl font-bold mb-6">Current Offers</h2>

        {loading ? (
          <div className="py-16 text-center text-gray text-sm">Loading offers…</div>
        ) : offers.length === 0 ? (
          <div className="py-16 text-center">
            <IconTag size={40} className="text-line mx-auto" />
            <p className="text-gray text-sm mt-4">No active offers right now — check back soon!</p>
            <Link to="/shop" className="inline-block mt-4 px-6 py-2.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Shop Now</Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {offers.map((o) => (
              <div key={o.id} className="border-2 border-gold bg-cream p-5 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-bold text-lg">{o.title}</div>
                  {o.description && <div className="text-sm mt-0.5 text-ink/80">{o.description}</div>}
                  {(o.starts_at || o.ends_at) && (
                    <div className="text-[11px] text-gray mt-1">
                      {o.ends_at ? `Valid till ${fmtDate(o.ends_at)}` : 'Ongoing'}
                    </div>
                  )}
                </div>
                <div className="shrink-0 text-center">
                  {o.image_url ? (
                    <img src={o.image_url} alt={o.title} className="w-20 h-20 object-cover rounded" />
                  ) : (
                    <div className="px-3 py-2 bg-ink text-gold-light font-bold text-sm rounded">{discountLabel(o)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Benefits */}
      <section className="px-6 lg:px-12 pb-10">
        <div className="bg-surface p-6 text-center">
          <h3 className="font-serif text-lg font-bold">Member Benefits</h3>
          <p className="text-xs text-gray mt-1 mb-4">Create an account to unlock exclusive perks</p>
          <div className="flex flex-wrap justify-center gap-4 text-xs">
            {['Early access to sales', 'Birthday discounts', 'Free shipping on ₹999+', 'Loyalty points'].map((b) => (
              <span key={b} className="px-3 py-1.5 bg-white border border-line">✓ {b}</span>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
