import PageHeader from '@/components/ui/PageHeader'

const SECTIONS = [
  { title: 'Acceptance of Terms', content: 'By accessing and using the AANGA website (www.aanga.in), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our services. These terms apply to all users, including browsers, customers, and wholesale partners.' },
  { title: 'Account Registration', content: 'You must provide accurate and complete information when creating an account. You are responsible for maintaining the confidentiality of your account credentials and for all activities under your account. You must be at least 18 years old or have parental consent to create an account.' },
  { title: 'Orders & Pricing', content: 'All prices are listed in Indian Rupees (₹) and include applicable taxes unless stated otherwise. We reserve the right to modify prices without prior notice. Orders are confirmed only after successful payment processing. We may cancel orders due to pricing errors, stock unavailability, or suspected fraud.' },
  { title: 'Shipping & Delivery', content: 'Delivery timelines are estimates and not guaranteed. AANGA is not liable for delays caused by shipping partners, natural disasters, or circumstances beyond our control. Risk of loss transfers to you upon delivery to the shipping carrier.' },
  { title: 'Returns & Refunds', content: 'Returns are accepted within 7 days of delivery subject to our Return Policy conditions. Refunds are processed to the original payment method within 5-7 business days after inspection. Shipping charges are non-refundable unless the return is due to our error.' },
  { title: 'Intellectual Property', content: 'All content on this website — including logos, images, text, graphics, and software — is the property of Amit Enterprises and protected by Indian intellectual property laws. You may not reproduce, distribute, or create derivative works without written permission.' },
  { title: 'Limitation of Liability', content: 'AANGA shall not be liable for any indirect, incidental, or consequential damages arising from your use of our services. Our total liability shall not exceed the amount paid by you for the specific order in question.' },
  { title: 'Governing Law', content: 'These terms are governed by the laws of India. Any disputes shall be subject to the exclusive jurisdiction of courts in Patna, Bihar. We encourage resolving disputes through our customer support before pursuing legal action.' },
]

export default function Terms() {
  return (
    <>
      <PageHeader title="Terms of Service" crumbs={[{ label: 'Home', to: '/' }, { label: 'Terms' }]} />
      <section className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8 py-10 max-w-3xl mx-auto">
        <p className="text-xs text-muted mb-6">Effective date: 1 January 2026</p>
        <p className="text-sm text-muted leading-relaxed mb-8">
          Welcome to AANGA. These Terms of Service govern your use of our website, mobile app, and all related services
          operated by Amit Enterprises, Patna, Bihar.
        </p>
        <div className="space-y-6">
          {SECTIONS.map((s, i) => (
            <div key={i}>
              <h3 className="display text-lg font-bold mb-2">{i + 1}. {s.title}</h3>
              <p className="text-sm text-muted leading-relaxed">{s.content}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 pt-6 border-t border-hairline/60">
          <p className="text-xs text-muted">For legal queries, contact: <span className="text-fg">legal@aanga.in</span></p>
        </div>
      </section>
    </>
  )
}
