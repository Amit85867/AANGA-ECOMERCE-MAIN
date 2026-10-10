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
  IconX,
  IconPhoto,
  IconSpeakerphone,
  IconAd2,
  IconAdjustments,
  IconQuote,
  IconSparkles,
  IconBuildingBank,
} from '@tabler/icons-react'
import { useState, useEffect } from 'react'
import logoImg from '@/assets/images/logo-main.png'

const NAV = [
  { to: '/admin', icon: IconDashboard, label: 'Dashboard', end: true },
  { to: '/admin/products', icon: IconPackage, label: 'Products' },
  { to: '/admin/categories', icon: IconCategory, label: 'Categories' },
  { to: '/admin/orders', icon: IconShoppingCart, label: 'Orders' },
  { to: '/admin/returns', icon: IconArrowBackUp, label: 'Returns' },
  { to: '/admin/settlements', icon: IconBuildingBank, label: 'Settlements' },
  { to: '/admin/users', icon: IconUsers, label: 'Users' },
  { to: '/admin/coupons', icon: IconTicket, label: 'Coupons' },
  { to: '/admin/offers', icon: IconGift, label: 'Offers' },
  { to: '/admin/banners', icon: IconPhoto, label: 'Hero Banners' },
  { to: '/admin/announcements', icon: IconSpeakerphone, label: 'Announcements' },
  { to: '/admin/promo-banners', icon: IconAd2, label: 'Promo Banners' },
  { to: '/admin/testimonials', icon: IconQuote, label: 'Testimonials' },
  { to: '/admin/features', icon: IconSparkles, label: 'Why Choose' },
  { to: '/admin/site-settings', icon: IconAdjustments, label: 'Site Settings' },
  { to: '/admin/inquiries', icon: IconBuildingStore, label: 'Inquiries' },
  { to: '/admin/messages', icon: IconMail, label: 'Messages' },
  { to: '/admin/newsletter', icon: IconNews, label: 'Newsletter' },
  { to: '/admin/settings', icon: IconSettings, label: 'Settings', masterOnly: true },
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

  const links = NAV.filter((n) => !n.masterOnly || admin?.role === 'master')

  return (
    <div className="flex h-screen bg-gray-50">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#0A0A0A] text-white transition-transform lg:static lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex h-16 items-center justify-between border-b border-white/10 px-6">
          <div className="flex items-center gap-2.5">
            <img src={logoImg} alt="AANGA" className="h-8 w-8 brightness-0 invert" />
            <span className="font-serif text-xl tracking-widest text-[#C8963E]">AANGA</span>
          </div>
          <span className="text-[11px] uppercase tracking-wider text-white/40">Admin</span>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {links.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `mb-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${isActive ? 'bg-[#C8963E]/20 text-[#C8963E]' : 'text-white/60 hover:bg-white/5 hover:text-white'}`
              }
            >
              <Icon size={20} stroke={1.5} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="mb-3 text-xs text-white/40">
            Signed in as{' '}
            <span className="text-white/70">{admin?.full_name}</span>
            <br />
            <span className="capitalize text-[#C8963E]">{admin?.role}</span>
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
            className="text-gray-500 lg:hidden"
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
    </div>
  )
}
