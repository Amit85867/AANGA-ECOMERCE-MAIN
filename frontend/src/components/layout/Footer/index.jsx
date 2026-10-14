import { Link } from 'react-router-dom'
import {
  IconBrandInstagram, IconBrandFacebook, IconBrandWhatsapp, IconBrandYoutube,
} from '@tabler/icons-react'
import { useSetting } from '@/store/useSettingsStore'
import { useLayoutStore } from '@/store/useLayoutStore'

// Shown until the menus have loaded (and if they never do). The real links
// are edited under Admin → Menus.
const FALLBACK_COLUMNS = [
  ['Shop', [{ label: 'All Products', url: '/shop' }, { label: 'Offers', url: '/offers' }, { label: 'Wholesale', url: '/wholesale' }]],
  ['Help', [{ label: 'Track Order', url: '/track-order' }, { label: 'Returns & Exchanges', url: '/returns' }, { label: 'FAQ', url: '/faq' }]],
  ['Company', [{ label: 'About Us', url: '/about' }, { label: 'Contact', url: '/contact' }, { label: 'Privacy Policy', url: '/privacy-policy' }, { label: 'Terms & Conditions', url: '/terms' }]],
]

const PAYMENTS = ['UPI', 'Visa', 'Mastercard', 'COD']

function FooterCol({ title, links }) {
  return (
    <div>
      <h2 className="text-xs tracking-[0.1em] uppercase text-fg font-semibold mb-4">
        {title}
      </h2>
      <ul className="space-y-2.5">
        {links.map(({ label, url }) => (
          <li key={`${label}-${url}`}>
            {/^https?:|^mailto:|^tel:/.test(url) ? (
              <a href={url} target={url.startsWith('http') ? '_blank' : undefined} rel="noreferrer" className="text-sm text-muted hover:text-fg transition-colors">{label}</a>
            ) : (
              <Link to={url} className="text-sm text-muted hover:text-fg transition-colors">{label}</Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Footer() {
  const s = useSetting()
  const footerLinks = useLayoutStore((st) => st.navigation.footer)
  const storeName = s('store_name', 'AANGA')

  // Footer links grouped under their column heading, in the saved order.
  const columns = footerLinks.length
    ? footerLinks.reduce((groups, link) => {
        const group = groups.find(([name]) => name === link.group_name)
        if (group) group[1].push(link)
        else groups.push([link.group_name, [link]])
        return groups
      }, [])
    : FALLBACK_COLUMNS

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
            <div className="display text-3xl text-fg mb-4">{storeName}</div>
            <p className="text-sm leading-relaxed text-muted max-w-[280px]">
              {/* Store settings → Tagline wins; the older "Other text" entry is the fallback. */}
              {s('store_tagline', '') || s(
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

          {columns.slice(0, 3).map(([title, links]) => <FooterCol key={title} title={title} links={links} />)}
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-8 border-t border-hairline">
          <p className="text-xs text-muted">
            © {new Date().getFullYear()} {storeName}. All rights reserved.
            {s('gstin') && <span className="ml-2">GSTIN {s('gstin')}</span>}
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
