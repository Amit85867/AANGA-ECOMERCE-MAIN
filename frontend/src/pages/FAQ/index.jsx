import { useState } from 'react'
import { IconChevronDown } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'

const FAQS = [
  { q: 'How long does delivery take?', a: 'Standard delivery takes 4-7 business days across India. Metro cities usually receive orders within 3-5 days.' },
  { q: 'What is your return policy?', a: 'We offer a hassle-free 7-day return/exchange policy. Items must be unused, unwashed, and in original packaging with tags intact. Refunds are processed within 5-7 business days after we receive the returned item.' },
  { q: 'Do you offer Cash on Delivery?', a: 'Yes. You can choose Cash on Delivery at checkout and pay when your order arrives.' },
  { q: 'How can I track my order?', a: 'Once your order is shipped, you\'ll receive a tracking ID via SMS and email. You can also track your order on our Track Order page using your order ID.' },
  { q: 'Are the products original/authentic?', a: 'Absolutely! All products sold on AANGA are 100% authentic and sourced directly from manufacturers. We guarantee quality and authenticity on every purchase.' },
  { q: 'Do you offer wholesale pricing?', a: 'Yes, we offer special wholesale rates for bulk orders (10+ items). Visit our Wholesale page or email wholesale@aanga.in for custom quotes.' },
  { q: 'What payment methods do you accept?', a: 'We accept UPI (GPay, PhonePe, Paytm), Credit/Debit Cards (Visa, Mastercard, RuPay), Net Banking, and Cash on Delivery.' },
  { q: 'How do I contact customer support?', a: 'You can reach us via email at support@aanga.in, call us at +91 98765 43210 (Mon-Sat, 10 AM - 8 PM), or use the Contact form on our website.' },
]

export default function FAQ() {
  const [open, setOpen] = useState(0)

  return (
    <>
      <PageHeader title="Frequently Asked Questions" crumbs={[{ label: 'Home', to: '/' }, { label: 'FAQ' }]} />
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 py-10 max-w-3xl mx-auto">
        <div className="space-y-2">
          {FAQS.map((f, i) => (
            <div key={i} className="border border-hairline/60">
              <button onClick={() => setOpen(open === i ? -1 : i)} className="w-full flex items-center justify-between p-4 text-left">
                <span className="font-medium text-sm pr-4">{f.q}</span>
                <IconChevronDown size={16} className={`shrink-0 text-muted transition-transform duration-200 ${open === i ? 'rotate-180' : ''}`} />
              </button>
              <div className={`overflow-hidden transition-all duration-200 ${open === i ? 'max-h-40' : 'max-h-0'}`}>
                <p className="px-4 pb-4 text-sm text-muted leading-relaxed">{f.a}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
