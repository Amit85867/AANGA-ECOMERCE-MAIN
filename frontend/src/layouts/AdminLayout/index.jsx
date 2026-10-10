import { Outlet, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { useAdminStore } from '@/store/useAdminStore'
import {
  IconDashboard,
  IconPackage,
  IconCategory,
  IconShoppingCart,
  IconArrowBackUp,
  IconUsers,
  IconTicket,
  IconGift,
  IconBuildingStore,
  IconMail,
  IconNews,
  IconSettings,
  IconLogout,
  IconMenu2,
  IconPhoto,
  IconSpeakerphone,
  IconAd2,
  IconAdjustments,
  IconQuote,
  IconSparkles,
  IconBuildingBank,
  IconStar,
  IconHeartRateMonitor,
  IconHistory,
} from '@tabler/icons-react'
import { useState, useEffect } from 'react'
import logoImg from '@/assets/images/logo-main.png'
import ConfirmDialog from '@/components/admin/ConfirmDialog'

const NAV = [
  {
    items: [{ to: '/admin', icon: IconDashboard, label: 'Dashboard', end: true }],
  },
  {
    heading: 'Sales',
    items: [
      { to: '/admin/orders', icon: IconShoppingCart, label: 'Orders' },
      { to: '/admin/returns', icon: IconArrowBackUp, label: 'Returns' },
      { to: '/admin/users', icon: IconUsers, label: 'Customers' },
      { to: '/admin/settlements', icon: IconBuildingBank, label: 'Settlements' },
    ],
  },
  {
    heading: 'Catalogue',
    items: [
      { to: '/admin/products', icon: IconPackage, label: 'Products' },
      { to: '/admin/categories', icon: IconCategory, label: 'Categories' },
      { to: '/admin/reviews', icon: IconStar, label: 'Reviews' },
      { to: '/admin/coupons', icon: IconTicket, label: 'Coupons' },
      { to: '/admin/offers', icon: IconGift, label: 'Offers' },
    ],
  },
  {
    heading: 'Storefront content',
    items: [
      { to: '/admin/banners', icon: IconPhoto, label: 'Hero banners' },
      { to: '/admin/announcements', icon: IconSpeakerphone, label: 'Announcements' },
      { to: '/admin/promo-banners', icon: IconAd2, label: 'Promo banners' },
      { to: '/admin/testimonials', icon: IconQuote, label: 'Testimonials' },
      { to: '/admin/features', icon: IconSparkles, label: 'Why choose us' },
      { to: '/admin/site-settings', icon: IconAdjustments, label: 'Site settings' },
    ],
  },
  {
    heading: 'Inbox',
    items: [
      { to: '/admin/inquiries', icon: IconBuildingStore, label: 'Wholesale inquiries' },
      { to: '/admin/messages', icon: IconMail, label: 'Messages' },
      { to: '/admin/newsletter', icon: IconNews, label: 'Newsletter' },
    ],
  },
  {
    heading: 'System',
    items: [
      { to: '/admin/system', icon: IconHeartRateMonitor, label: 'System health' },
      { to: '/admin/audit-log', icon: IconHistory, label: 'Audit log' },
      { to: '/admin/settings', icon: IconSettings, label: 'Admins', masterOnly: true },
    ],
  },
]

export default function AdminLayout() {
  const { admin, isAuthenticated, initializing, restoreSession, logout } = useAdminStore()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // The admin token is no longer persisted, so on a reload we exchange the
  // httpOnly refresh cookie for a new access token before deciding to redirect.
  useEffect(() => {
    if (initializing) restoreSession()
  }, [initializing, restoreSession])

  if (initializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/admin/login" replace />

  const handleLogout = async () => {
    await logout()
    navigate('/admin/login')
  }

  const groups = NAV
    .map((g) => ({ ...g, items: g.items.filter((n) => !n.masterOnly || admin?.role === 'master') }))
    .filter((g) => g.items.length > 0)

  return (
    <div className="flex h-screen bg-gray-50">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-ink text-white transition-transform lg:static lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex h-16 items-center justify-between border-b border-white/10 px-6">
          <div className="flex items-center gap-2.5">
            <img src={logoImg} alt="AANGA" className="h-8 w-8 brightness-0 invert" />
            <span className="display text-xl tracking-widest text-gold">AANGA</span>
          </div>
          <span className="text-[11px] uppercase tracking-wider text-white/40">Admin</span>
        </div>

        <nav aria-label="Admin" className="flex-1 overflow-y-auto px-3 py-4">
          {groups.map((group) => (
            <div key={group.heading || 'top'} className="mb-4">
              {group.heading && (
                <p className="mb-1 px-3 text-[11px] font-medium uppercase tracking-wider text-white/40">
                  {group.heading}
                </p>
              )}
              {group.items.map(({ to, icon: Icon, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    `mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold ${isActive ? 'bg-gold/20 text-gold' : 'text-white/70 hover:bg-white/5 hover:text-white'}`
                  }
                >
                  <Icon size={18} stroke={1.5} aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="mb-3 text-xs text-white/40">
            Signed in as{' '}
            <span className="text-white/70">{admin?.full_name}</span>
            <br />
            <span className="capitalize text-gold">{admin?.role}</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-white/50 transition-colors hover:bg-white/5 hover:text-white"
          >
            <IconLogout size={18} stroke={1.5} />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center gap-4 border-b border-gray-200 bg-white px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="rounded p-1 text-gray-500 lg:hidden"
          >
            <IconMenu2 size={24} />
          </button>
          <div className="flex-1" />
          <span className="text-sm text-gray-500">{admin?.email}</span>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
      <ConfirmDialog />
    </div>
  )
}
