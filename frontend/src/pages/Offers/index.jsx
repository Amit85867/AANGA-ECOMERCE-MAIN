import { useCallback, useEffect, useState } from 'react'
import { IconTag } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { Badge, Container, EmptyState, ErrorState, PageTitle, Skeleton } from '@/components/ui/Display'
import { formatDate } from '@/utils/format'
import Seo from '@/components/Seo'

const headline = (offer) => {
  if (offer.offer_type === 'free_shipping') return 'Free shipping'
  if (offer.offer_type === 'bogo') return 'Buy one, get one'
  if (offer.discount_percent) return `${Math.round(offer.discount_percent)}% off`
  return 'Special offer'
}

export default function Offers() {
  const [offers, setOffers] = useState(null)
  const [failed, setFailed] = useState(false)

  const load = useCallback(() => {
    setFailed(false)
    return apiClient.get('/offers')
      .then(({ data }) => setOffers(data.offers || []))
      .catch(() => setFailed(true))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <>
      <Seo title="Offers" description="Current offers and deals at AANGA." />
      <Container className="pb-20">
        <PageTitle
          title="Offers"
          subtitle="What is on right now. Offers apply automatically or with the code shown."
          crumbs={[{ label: 'Home', to: '/' }, { label: 'Offers' }]}
        />

        {failed ? (
          <ErrorState message="We could not load the offers." onRetry={load} />
        ) : offers === null ? (
          <div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
        ) : offers.length === 0 ? (
          <EmptyState
            icon={IconTag} title="No offers right now"
            hint="New offers appear here as soon as they start."
            action={<Button to="/shop">Browse products</Button>}
          />
        ) : (
          <ul className="grid gap-4 md:grid-cols-2">
            {offers.map((o) => (
              <li key={o.id}>
                <Card className="flex h-full items-center gap-5 p-6">
                  {o.image_url && (
                    <img
                      src={o.image_url} alt="" width="96" height="96" loading="lazy"
                      className="h-24 w-24 shrink-0 rounded-card object-cover"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <Badge tone="accent">{headline(o)}</Badge>
                    <h2 className="display mt-3 text-xl text-fg">{o.title}</h2>
                    {o.description && <p className="mt-1.5 text-sm leading-relaxed text-muted">{o.description}</p>}
                    <p className="mt-3 text-xs text-subtle">
                      {o.ends_at ? `Ends ${formatDate(o.ends_at)}` : 'No end date'}
                    </p>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </Container>
    </>
  )
}
