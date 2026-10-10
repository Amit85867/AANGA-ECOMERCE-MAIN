import { IconDiamond, IconUsers, IconHeart, IconLeaf } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'

const VALUES = [
  { icon: IconDiamond, title: 'Premium Quality', desc: 'Every piece undergoes strict quality checks before reaching you.' },
  { icon: IconUsers, title: 'Customer First', desc: 'Your satisfaction drives every decision we make.' },
  { icon: IconHeart, title: 'Passion for Fashion', desc: 'We live and breathe style — curating only the best.' },
  { icon: IconLeaf, title: 'Sustainable Choice', desc: 'Committed to ethical sourcing and eco-friendly packaging.' },
]

export default function About() {
  return (
    <>
      <PageHeader title="About AANGA" crumbs={[{ label: 'Home', to: '/' }, { label: 'About' }]} />

      {/* Hero */}
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 py-14 text-center max-w-3xl mx-auto">
        <div className="text-xs tracking-[0.15em] text-muted uppercase font-semibold mb-3">Our Story</div>
        <h2 className="display text-3xl font-bold leading-tight">Bihar's Premium Fashion Destination</h2>
        <p className="text-sm text-muted leading-relaxed mt-4">
          AANGA was born from a simple belief — everyone deserves access to premium fashion without the premium price tag.
          Founded in Patna by Amit Enterprises, we've grown from a small local shop to Bihar's most trusted online fashion brand,
          serving over 50,000 happy customers across India.
        </p>
        <p className="text-sm text-muted leading-relaxed mt-3">
          Our name "AANGA" comes from the ancient Anga kingdom of Bihar — a tribute to our roots and the rich cultural heritage
          we carry forward through modern fashion.
        </p>
      </section>

      {/* Mission */}
      <section className="bg-primary mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 py-14 text-center">
        <div className="text-xs tracking-[0.15em] text-muted uppercase font-semibold mb-3">Our Mission</div>
        <h2 className="display text-3xl text-white font-bold">Style That Speaks For Itself</h2>
        <p className="text-sm text-white/80 leading-relaxed mt-4 max-w-2xl mx-auto">
          To make premium, trendy fashion accessible to every Indian — from metro cities to small towns.
          We combine quality fabrics, modern designs, and fair pricing to deliver fashion that makes you feel confident every day.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-10 max-w-2xl mx-auto">
          {[
            { num: '50K+', label: 'Happy Customers' },
            { num: '5,000+', label: 'Products' },
            { num: '500+', label: 'Cities Served' },
            { num: '4.8★', label: 'Average Rating' },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-2xl font-bold text-fg">{s.num}</div>
              <div className="text-xs text-white/80 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Values */}
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 py-14">
        <div className="text-center mb-10">
          <div className="text-xs tracking-[0.15em] text-muted uppercase font-semibold mb-2">Our Values</div>
          <h2 className="display text-3xl font-bold">What We Stand For</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {VALUES.map((v) => (
            <div key={v.title} className="bg-fill p-6 text-center">
              <div className="w-12 h-12 bg-fill mx-auto flex items-center justify-center mb-4"><v.icon size={22} className="text-fg" /></div>
              <h3 className="display text-lg font-bold">{v.title}</h3>
              <p className="text-xs text-muted leading-relaxed mt-2">{v.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
