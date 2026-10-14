import Seo from '@/components/Seo'
import HeroSection from './sections/HeroSection'
import CategoryStrip from './sections/CategoryStrip'
import CategoryGrid from './sections/CategoryGrid'
import ProductGrid from './sections/ProductGrid'
import SaleBanner from './sections/SaleBanner'
import WhyChoose from './sections/WhyChoose'
import Reviews from './sections/Reviews'
import Newsletter from './sections/Newsletter'
import { useLayoutStore } from '@/store/useLayoutStore'
import { useSetting } from '@/store/useSettingsStore'

const SECTIONS = {
  hero: HeroSection,
  category_strip: CategoryStrip,
  features: WhyChoose,
  category_tiles: CategoryGrid,
  featured: ProductGrid,
  promo: SaleBanner,
  testimonials: Reviews,
  newsletter: Newsletter,
}

export default function Home() {
  const sections = useLayoutStore((st) => st.homepage)
  const st = useSetting()
  const storeName = st('store_name', 'AANGA')
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        name: storeName,
        url: origin || undefined,
        logo: origin ? `${origin}/favicon.svg` : undefined,
      },
      {
        '@type': 'WebSite',
        name: storeName,
        url: origin || undefined,
        potentialAction: {
          '@type': 'SearchAction',
          target: origin ? `${origin}/shop?q={search_term_string}` : undefined,
          'query-input': 'required name=search_term_string',
        },
      },
    ],
  }

  return (
    <>
      <Seo jsonLd={jsonLd} />
      {/* Which sections show, and in what order, is the owner's choice
          (Admin → Homepage). The default order is: hook, reassure, sell,
          prove, capture. */}
      {sections.map((section) => {
        const Section = SECTIONS[section.key]
        return Section ? <Section key={section.key} heading={section} collection={section.collection} /> : null
      })}
    </>
  )
}
