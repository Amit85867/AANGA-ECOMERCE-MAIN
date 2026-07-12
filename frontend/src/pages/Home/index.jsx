import HeroSection from './sections/HeroSection'
import CategoryStrip from './sections/CategoryStrip'
import CategoryGrid from './sections/CategoryGrid'
import ProductGrid from './sections/ProductGrid'
import SaleBanner from './sections/SaleBanner'
import WhyChoose from './sections/WhyChoose'
import Reviews from './sections/Reviews'
import Newsletter from './sections/Newsletter'

export default function Home() {
  return (
    <>
      <HeroSection />
      <CategoryStrip />
      <CategoryGrid />
      <ProductGrid />
      <SaleBanner />
      <WhyChoose />
      <Reviews />
      <Newsletter />
    </>
  )
}
