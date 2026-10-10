import { Link } from 'react-router-dom'
import { IconHome, IconSearch } from '@tabler/icons-react'

export default function NotFound() {
  return (
    <div className="flex-1 flex items-center justify-center py-20 px-6">
      <div className="text-center max-w-md">
        <div className="text-8xl display font-bold text-fg">404</div>
        <h1 className="display text-2xl font-bold mt-3">Page Not Found</h1>
        <p className="text-sm text-muted mt-2 leading-relaxed">
          The page you're looking for doesn't exist or has been moved. Let's get you back on track.
        </p>
        <div className="flex items-center justify-center gap-3 mt-6">
          <Link to="/" className="flex items-center gap-2 px-6 py-3 bg-primary text-on-primary text-xs tracking-[0.08em] uppercase font-bold hover:bg-primary/90 transition-colors">
            <IconHome size={14} /> Go Home
          </Link>
          <Link to="/shop" className="flex items-center gap-2 px-6 py-3 border border-hairline/60 text-xs tracking-[0.08em] uppercase font-bold hover:border-primary transition-colors">
            <IconSearch size={14} /> Browse Shop
          </Link>
        </div>
      </div>
    </div>
  )
}
