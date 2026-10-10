import { Link, Outlet } from 'react-router-dom'
import { IconArrowLeft } from '@tabler/icons-react'
import { ROUTES } from '@/utils/constants'
import logoTitle from '@/assets/images/logo-title.png'
import MaintenanceGate from '@/components/layout/MaintenanceGate'

/* Sign-in pages: just the logo, a way back, and the form. */
export default function AuthLayout() {
  return (
    <MaintenanceGate>
      <div className="min-h-screen flex flex-col bg-bg">
        <header className="flex h-16 items-center justify-between px-4 sm:px-8">
          <Link to={ROUTES.HOME} aria-label="AANGA home">
            <img src={logoTitle} alt="AANGA" width="120" height="40" className="h-10 w-auto object-contain" />
          </Link>
          <Link
            to={ROUTES.HOME}
            className="inline-flex items-center gap-1.5 rounded text-sm text-muted hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <IconArrowLeft size={16} aria-hidden="true" /> Back to store
          </Link>
        </header>
        <main className="flex flex-1 items-center justify-center px-4 py-8 sm:py-12">
          <Outlet />
        </main>
      </div>
    </MaintenanceGate>
  )
}
