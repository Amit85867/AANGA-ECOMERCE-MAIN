import { useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { Container, Rating } from '@/components/ui/Display'
import SectionHeading from './SectionHeading'
import { useSetting } from '@/store/useSettingsStore'

const INITIAL = 3

/* Testimonials set up under Admin → Testimonials. */
export default function Reviews({ heading }) {
  const [items, setItems] = useState([])
  const [expanded, setExpanded] = useState(false)
  const s = useSetting()

  useEffect(() => {
    apiClient.get('/cms/testimonials')
      .then(({ data }) => setItems(data.testimonials || []))
      .catch(() => {})
  }, [])

  if (items.length === 0) return null
  const shown = expanded ? items : items.slice(0, INITIAL)

  return (
    <section className="bg-fill py-14 lg:py-20" aria-labelledby="testimonials-heading">
      <Container>
        <SectionHeading
          id="testimonials-heading"
          eyebrow={heading?.subtitle || s('reviews_tag', 'Testimonials')}
          title={heading?.title || s('reviews_title', 'What our customers say')}
        />
        <ul className="grid gap-4 md:grid-cols-3">
          {shown.map((r) => (
            <li key={r.id}>
              <Card className="flex h-full flex-col p-6">
                <Rating value={r.rating} />
                <blockquote className="mt-4 flex-1 text-sm leading-relaxed text-fg">“{r.quote}”</blockquote>
                <div className="mt-5 flex items-center gap-3">
                  {r.avatar_url ? (
                    <img src={r.avatar_url} alt="" width="40" height="40" loading="lazy" className="h-10 w-10 rounded-full object-cover" />
                  ) : (
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-xs font-semibold text-on-primary" aria-hidden="true">
                      {r.name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-semibold text-fg">{r.name}</p>
                    {r.location && <p className="text-xs text-muted">{r.location}</p>}
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>
        {items.length > INITIAL && (
          <div className="mt-8 text-center">
            <Button variant="secondary" size="sm" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
              {expanded ? 'Show fewer' : `Show all ${items.length}`}
            </Button>
          </div>
        )}
      </Container>
    </section>
  )
}
