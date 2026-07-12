import { Link } from 'react-router-dom'
import {
  IconBrandInstagram, IconBrandFacebook, IconBrandWhatsapp, IconBrandYoutube,
} from '@tabler/icons-react'
import logoImg from '@/assets/images/logo-main.png'
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

const PAYMENTS = ['UPI', 'Visa', 'MC', 'COD']

function FooterCol({ title, links }) {
  return (
    <div>
      <h4 className="text-[10px] tracking-[2px] uppercase text-white font-semibold mb-4">{title}</h4>
      <ul className="space-y-2">
        {links.map(({ label, to }) => (
          <li key={label}>
            <Link to={to} className="text-xs text-white/40 hover:text-gold transition-colors">{label}</Link>
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
    { icon: IconBrandInstagram, href: s('instagram_url') },
    { icon: IconBrandFacebook, href: s('facebook_url') },
    { icon: IconBrandWhatsapp, href: waNumber ? `https://wa.me/${waNumber}` : '' },
    { icon: IconBrandYoutube, href: s('youtube_url') },
  ].filter((soc) => soc.href)

  return (
    <footer className="bg-[#050505] px-6 md:px-12 pt-12 pb-6 text-white/60">
      <div className="max-w-[1400px] mx-auto">
        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr] gap-9 pb-10 border-b border-white/[0.07]">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <img src={logoImg} alt="AANGA" className="h-9 w-9 brightness-0 invert" />
              <span className="font-serif text-[22px] font-bold text-white tracking-[3px]">AANGA</span>
            </div>
            <p className="text-xs leading-[1.8] text-white/40 max-w-[260px]">
              {s('footer_tagline', "Bihar's premium fashion destination for men, women & kids. Wholesale and retail clothing with 1,200+ styles.")}
            </p>
            {socials.length > 0 && (
              <div className="flex gap-2.5 mt-5">
                {socials.map(({ icon: Icon, href }) => (
                  <a
                    key={href + Icon.displayName}
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="w-[34px] h-[34px] border border-white/[0.12] flex items-center justify-center text-white/40 hover:border-gold hover:text-gold transition-colors"
                  >
                    <Icon size={16} stroke={1.5} />
                  </a>
                ))}
              </div>
            )}
          </div>

          <FooterCol title="Shop" links={SHOP_LINKS} />
          <FooterCol title="Help" links={HELP_LINKS} />
          <FooterCol title="Legal" links={LEGAL_LINKS} />
        </div>

        {/* Bottom */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-5">
          <p className="text-[11px] text-white/20">
            © {new Date().getFullYear()} AANGA — Amit Enterprises, Patna. All rights reserved.
          </p>
          <div className="flex gap-1.5">
            {PAYMENTS.map((p) => (
              <span key={p} className="bg-white/[0.07] px-2.5 py-1 text-[9px] tracking-[1px] text-white/35 uppercase">{p}</span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
