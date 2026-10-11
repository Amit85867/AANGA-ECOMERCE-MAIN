import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  IconArrowBackUp, IconHeart, IconLogout, IconMapPin, IconPackage, IconUser,
} from '@tabler/icons-react'
import AnnounceBar from '@/components/layout/AnnounceBar'
import Navbar from '@/components/layout/Navbar'
import Footer from '@/components/layout/Footer'
import MaintenanceGate from '@/components/layout/MaintenanceGate'
import { Container, Skeleton } from '@/components/ui/Display'
import { useAuthStore } from '@/store/useAuthStore'

const NAV = [
  { to: '/account/orders', icon: IconPackage, label: 'Orders' },
  { to: '/account/returns', icon: IconArrowBackUp, label: 'Returns' },
  { to: '/account/addresses', icon: IconMapPin, label: 'Addresses' },
  { to: '/account/profile', icon: IconUser, label: 'Profile' },
  { to: '/wishlist', icon: IconHeart, label: 'Wishlist' },
]

const linkCls = ({ isActive }) =>
  `flex items-center gap-3 rounded-card px-4 py-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
    isActive ? 'bg-primary text-on-primary font-medium' : 'text-muted hover:bg-fill hover:text-fg'
  }`

const tabCls = ({ isActive }) =>
  `shrink-0 rounded-full px-4 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
    isActive ? 'bg-primary text-on-primary font-medium' : 'bg-fill text-muted'
  }`

/*
 * The signed-in account area: a sidebar on desktop, a scrolling row of tabs on
 * phones. Each section is its own URL, so Back, refresh and links from emails
 * all land where they should.
 */
export default function DashboardLayout() {
  const { user, isAuthenticated, initializing, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  const signOut = async () => {
    await logout()
    navigate('/')
  }

  let content
  if (initializing) {
    // The session is restored from a cookie on load; wait for the answer
    // rather than bouncing a signed-in customer to the login page.
    content = <Container className="py-16"><Skeleton className="h-80" /></Container>
  } else if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  } else {
    content = (
      <Container className="py-8 lg:py-12">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-8 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-12">
          <aside className="min-w-0">
            <div className="mb-6">
              <p className="text-xs uppercase tracking-[0.08em] text-muted">Signed in as</p>
              <p className="mt-1 truncate text-sm font-semibold text-fg">{user?.full_name}</p>
              <p className="truncate text-xs text-muted">{user?.email}</p>
            </div>

            <nav aria-label="Account" className="hidden lg:block space-y-1">
              {NAV.map(({ to, icon: Icon, label }) => (
                <NavLink key={to} to={to} className={linkCls}>
                  <Icon size={18} stroke={1.5} aria-hidden="true" /> {label}
                </NavLink>
              ))}
              <button
                type="button" onClick={signOut}
                className="flex w-full items-center gap-3 rounded-card px-4 py-3 text-sm text-muted hover:bg-fill hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <IconLogout size={18} stroke={1.5} aria-hidden="true" /> Sign out
              </button>
            </nav>

            <nav aria-label="Account" className="lg:hidden -mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
              {NAV.map(({ to, label }) => (
                <NavLink key={to} to={to} className={tabCls}>{label}</NavLink>
              ))}
              <button type="button" onClick={signOut} className="shrink-0 rounded-full bg-fill px-4 py-2 text-sm text-muted">
                Sign out
              </button>
            </nav>
          </aside>

          <div className="min-w-0"><Outlet /></div>
        </div>
      </Container>
    )
  }

  return (
    <MaintenanceGate>
      <div className="min-h-screen flex flex-col bg-bg">
        <AnnounceBar />
        <Navbar />
        <main className="min-h-screen flex-1">{content}</main>
        <Footer />
      </div>
    </MaintenanceGate>
  )
}
