import Seo from '@/components/Seo'
import HeroSection from './sections/HeroSection'
import CategoryStrip from './sections/CategoryStrip'
import CategoryGrid from './sections/CategoryGrid'
import ProductGrid from './sections/ProductGrid'
import SaleBanner from './sections/SaleBanner'
import WhyChoose from './sections/WhyChoose'
import Reviews from './sections/Reviews'
import Newsletter from './sections/Newsletter'

export default function Home() {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        name: 'AANGA',
        url: origin || undefined,
        logo: origin ? `${origin}/favicon.svg` : undefined,
      },
      {
        '@type': 'WebSite',
        name: 'AANGA',
        url: origin || undefined,
        potentialAction: {
          '@type': 'SearchAction',
          target: origin ? `${origin}/shop?search={search_term_string}` : undefined,
          'query-input': 'required name=search_term_string',
        },
      },
    ],
  }

  return (
    <>
      <Seo jsonLd={jsonLd} />
      {/* Order: hook, then reassure, then sell, then prove, then capture.
          WhyChoose carries the delivery/returns promises, so it sits directly
          under the hero where it answers the first objection instead of at the
          bottom where most visitors never reach it. Reviews follow the promo
          so the social proof lands next to the call to action. */}
      <HeroSection />
      <CategoryStrip />
      <WhyChoose />
      <CategoryGrid />
      <ProductGrid />
      <SaleBanner />
      <Reviews />
      <Newsletter />
    </>
  )
}
