import { Link } from 'react-router-dom'
import {
  IconBrandInstagram, IconBrandFacebook, IconBrandWhatsapp, IconBrandYoutube,
} from '@tabler/icons-react'
import { useSetting } from '@/store/useSettingsStore'

const SHOP_LINKS = [
  { label: 'New Arrivals', to: '/shop' },
  { label: "Men's Clothing", to: '/shop' },
  { label: "Women's Clothing", to: '/shop' },
  { label: 'Kids Wear', to: '/shop' },
  { label: 'Current Offers', to: '/offers' },
]

const HELP_LINKS = [
  { label: 'Track Order', to: '/track-order' },
  { label: 'Returns & Exchange', to: '/returns' },
  { label: 'FAQ', to: '/faq' },
  { label: 'Contact Us', to: '/contact' },
  { label: 'Wholesale Inquiry', to: '/wholesale' },
]

const LEGAL_LINKS = [
  { label: 'About AANGA', to: '/about' },
  { label: 'Privacy Policy', to: '/privacy-policy' },
  { label: 'Terms of Service', to: '/terms' },
  { label: 'Returns Policy', to: '/returns' },
]

const PAYMENTS = ['UPI', 'Visa', 'Mastercard', 'COD']

function FooterCol({ title, links }) {
  return (
    <div>
      <h2 className="text-xs tracking-[0.1em] uppercase text-fg font-semibold mb-4">
        {title}
      </h2>
      <ul className="space-y-2.5">
        {links.map(({ label, to }) => (
          <li key={label}>
            <Link to={to} className="text-sm text-muted hover:text-fg transition-colors">
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Footer() {
  const s = useSetting()

  const waNumber = s('whatsapp_number', '').replace(/\D/g, '')
  const socials = [
    { icon: IconBrandInstagram, label: 'Instagram', href: s('instagram_url') },
    { icon: IconBrandFacebook, label: 'Facebook', href: s('facebook_url') },
    { icon: IconBrandWhatsapp, label: 'WhatsApp', href: waNumber ? `https://wa.me/${waNumber}` : '' },
    { icon: IconBrandYoutube, label: 'YouTube', href: s('youtube_url') },
  ].filter((soc) => soc.href)

  return (
    <footer className="bg-bg border-t border-hairline px-4 md:px-8 lg:px-12 pt-16 pb-8">
      <div className="max-w-[1280px] mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr] gap-10 pb-12">
          {/* Brand */}
          <div>
            <div className="display text-3xl text-fg mb-4">AANGA</div>
            <p className="text-sm leading-relaxed text-muted max-w-[280px]">
              {s(
                'footer_tagline',
                "Bihar's premium fashion destination for men, women & kids. Wholesale and retail clothing with 1,200+ styles.",
              )}
            </p>
            {socials.length > 0 && (
              <div className="flex gap-3 mt-6">
                {socials.map(({ icon: Icon, label, href }) => (
                  <a
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={label}
                    className="w-10 h-10 rounded-full border border-hairline flex items-center
                               justify-center text-muted hover:border-primary hover:text-fg
                               transition-colors"
                  >
                    <Icon size={18} stroke={1.5} />
                  </a>
                ))}
              </div>
            )}
          </div>

          <FooterCol title="Shop" links={SHOP_LINKS} />
          <FooterCol title="Help" links={HELP_LINKS} />
          <FooterCol title="Legal" links={LEGAL_LINKS} />
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-8 border-t border-hairline">
          <p className="text-xs text-muted">
            © {new Date().getFullYear()} AANGA — Amit Enterprises, Patna. All rights reserved.
          </p>
          <div className="flex gap-2">
            {PAYMENTS.map((p) => (
              <span
                key={p}
                className="bg-fill px-3 py-1.5 rounded text-xs tracking-[0.05em] text-muted uppercase"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
