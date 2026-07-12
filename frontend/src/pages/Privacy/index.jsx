import PageHeader from '@/components/ui/PageHeader'

const SECTIONS = [
  { title: 'Information We Collect', content: 'We collect information you provide directly: name, email, phone number, shipping address, and payment details when you make a purchase. We also automatically collect device information, IP address, browser type, and browsing patterns on our site through cookies and analytics tools.' },
  { title: 'How We Use Your Information', content: 'Your information is used to: process and deliver orders, send order confirmations and shipping updates, provide customer support, send promotional offers (with your consent), improve our website and services, prevent fraud and ensure security.' },
  { title: 'Information Sharing', content: 'We do not sell your personal information. We share data only with: payment processors (Razorpay) to complete transactions, shipping partners for delivery, analytics providers (Google Analytics) for site improvement, and legal authorities when required by law.' },
  { title: 'Data Security', content: 'We implement industry-standard security measures including SSL encryption, secure payment gateways, and regular security audits to protect your personal information from unauthorized access or disclosure.' },
  { title: 'Cookies', content: 'We use essential cookies for site functionality and optional cookies for analytics and personalization. You can manage cookie preferences through your browser settings. Disabling essential cookies may affect site functionality.' },
  { title: 'Your Rights', content: 'You have the right to: access your personal data, correct inaccurate information, request deletion of your data, opt out of marketing communications, and withdraw consent at any time. Contact us at privacy@aanga.in to exercise these rights.' },
  { title: 'Data Retention', content: 'We retain your personal information for as long as your account is active or as needed to provide services. Order data is retained for 5 years for legal and accounting purposes. You may request deletion of your account at any time.' },
  { title: 'Changes to This Policy', content: 'We may update this policy periodically. Changes will be posted on this page with an updated "Last Modified" date. Continued use of our services after changes constitutes acceptance of the revised policy.' },
]

export default function Privacy() {
  return (
    <>
      <PageHeader title="Privacy Policy" crumbs={[{ label: 'Home', to: '/' }, { label: 'Privacy Policy' }]} />
      <section className="px-6 lg:px-12 py-10 max-w-3xl mx-auto">
        <p className="text-xs text-gray mb-6">Last updated: 1 January 2026</p>
        <p className="text-[13px] text-gray leading-[1.8] mb-8">
          At AANGA (operated by Amit Enterprises, Patna), we are committed to protecting your privacy.
          This policy explains how we collect, use, and safeguard your personal information when you use our website and services.
        </p>
        <div className="space-y-6">
          {SECTIONS.map((s, i) => (
            <div key={i}>
              <h3 className="font-serif text-lg font-bold mb-2">{i + 1}. {s.title}</h3>
              <p className="text-[13px] text-gray leading-[1.8]">{s.content}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 pt-6 border-t border-line">
          <p className="text-xs text-gray">For privacy-related queries, contact: <span className="text-gold">privacy@aanga.in</span></p>
        </div>
      </section>
    </>
  )
}
