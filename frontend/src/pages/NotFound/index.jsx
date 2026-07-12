import { Link } from 'react-router-dom'
import { IconHome, IconSearch } from '@tabler/icons-react'

export default function NotFound() {
  return (
    <div className="flex-1 flex items-center justify-center py-20 px-6">
      <div className="text-center max-w-md">
        <div className="text-8xl font-serif font-bold text-gold">404</div>
        <h1 className="font-serif text-2xl font-bold mt-3">Page Not Found</h1>
        <p className="text-[13px] text-gray mt-2 leading-[1.8]">
          The page you're looking for doesn't exist or has been moved. Let's get you back on track.
        </p>
        <div className="flex items-center justify-center gap-3 mt-6">
          <Link to="/" className="flex items-center gap-2 px-6 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">
            <IconHome size={14} /> Go Home
          </Link>
          <Link to="/shop" className="flex items-center gap-2 px-6 py-3 border border-line text-[11px] tracking-[2px] uppercase font-bold hover:border-ink transition-colors">
            <IconSearch size={14} /> Browse Shop
          </Link>
        </div>
      </div>
    </div>
  )
}
