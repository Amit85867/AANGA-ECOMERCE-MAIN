import { Link, Outlet } from 'react-router-dom'
import { IconArrowLeft } from '@tabler/icons-react'
import { ROUTES } from '@/utils/constants'
import logoMain from '@/assets/images/logo-main.png'
import logoTitle from '@/assets/images/logo-title.png'

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <nav className="bg-paper border-b border-line h-[60px] flex items-center px-6">
        <Link to={ROUTES.HOME} className="flex items-center gap-2">
          <img src={logoMain} alt="" className="h-9 w-9 object-contain" />
          <img src={logoTitle} alt="AANGA" className="h-8 object-contain" />
        </Link>
        <Link to={ROUTES.HOME} className="ml-auto flex items-center gap-2 text-xs">
          <IconArrowLeft size={18} />
          Back to Home
        </Link>
      </nav>
      <div className="flex-1 flex items-center justify-center py-10 px-5">
        <Outlet />
      </div>
    </div>
  )
}
