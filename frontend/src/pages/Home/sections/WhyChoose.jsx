import { useEffect, useState } from 'react'
import { IconShieldCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { Container } from '@/components/ui/Display'
import { FEATURE_ICONS } from '@/utils/featureIcons'

/*
 * The store's promises (delivery, returns, authenticity…), set up under
 * Admin → Why Choose. A compact strip rather than a full section: it sits
 * right under the hero to answer the first objections without pushing the
 * products down the page.
 */
export default function WhyChoose() {
  const [features, setFeatures] = useState([])

  useEffect(() => {
    apiClient.get('/cms/features')
      .then(({ data }) => setFeatures(data.features || []))
      .catch(() => {})
  }, [])

  if (features.length === 0) return null

  return (
    <Container as="section" className="pt-10 lg:pt-14" aria-label="Why shop with us">
      <ul className="grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">
        {features.slice(0, 8).map((f) => {
          const Icon = FEATURE_ICONS[f.icon] || IconShieldCheck
          return (
            <li key={f.id} className="flex gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-fill text-fg">
                {f.image_url
                  ? <img src={f.image_url} alt="" width="44" height="44" loading="lazy" className="h-full w-full object-cover" />
                  : <Icon size={20} stroke={1.5} aria-hidden="true" />}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-fg">{f.title}</h3>
                {f.description && <p className="mt-1 text-xs leading-relaxed text-muted">{f.description}</p>}
              </div>
            </li>
          )
        })}
      </ul>
    </Container>
  )
}
