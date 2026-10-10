import { IconPackageOff, IconRefresh, IconCash } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'

const STEPS = [
  { icon: IconPackageOff, num: '01', title: 'Initiate Return', desc: 'Log into your account, go to My Orders, and click "Return" on the item within 7 days of delivery.' },
  { icon: IconRefresh, num: '02', title: 'Pack & Ship', desc: 'Pack the item in original packaging with tags. Our delivery partner will pick it up from your address.' },
  { icon: IconCash, num: '03', title: 'Get Refund', desc: 'Once received and inspected, refund is processed within 5-7 business days to your original payment method.' },
]

const CONDITIONS = [
  'Item must be unused, unwashed, and in original condition',
  'All tags and labels must be intact',
  'Item must be returned in original packaging',
  'Return request must be raised within 7 days of delivery',
  'Innerwear, swimwear, and customized items are non-returnable',
  'Items purchased during sale with 50%+ discount are exchange-only',
]

export default function Returns() {
  return (
    <>
      <PageHeader title="Returns & Exchange" crumbs={[{ label: 'Home', to: '/' }, { label: 'Returns' }]} />

      {/* Steps */}
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 py-10">
        <div className="text-center mb-8">
          <h2 className="display text-2xl font-bold">Easy 3-Step Process</h2>
          <p className="text-xs text-muted mt-1">Hassle-free returns within 7 days</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {STEPS.map((s) => (
            <div key={s.num} className="bg-fill p-6 text-center relative">
              <div className="absolute top-4 right-4 text-xs tracking-[0.08em] text-fg font-bold">{s.num}</div>
              <div className="w-12 h-12 bg-fill mx-auto flex items-center justify-center mb-4"><s.icon size={22} className="text-fg" /></div>
              <h3 className="display text-lg font-bold">{s.title}</h3>
              <p className="text-xs text-muted leading-relaxed mt-2">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Conditions */}
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 pb-10">
        <div className="border border-hairline/60 p-6 lg:p-8">
          <h3 className="display text-lg font-bold mb-4">Return Conditions</h3>
          <ul className="space-y-2.5">
            {CONDITIONS.map((c) => (
              <li key={c} className="flex items-start gap-3 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                {c}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Exchange Note */}
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 pb-10">
        <div className="bg-fill p-6 text-center">
          <h3 className="display text-lg font-bold">Prefer an Exchange?</h3>
          <p className="text-xs text-muted mt-1 max-w-lg mx-auto">
            If you'd like a different size or color, choose "Exchange" instead of "Return" in your order page.
            Exchanges are processed faster and don't incur any additional shipping charges.
          </p>
        </div>
      </section>
    </>
  )
}
