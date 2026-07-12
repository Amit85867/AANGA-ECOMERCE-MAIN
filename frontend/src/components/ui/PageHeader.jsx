import { Link } from 'react-router-dom'

export default function PageHeader({ title, crumbs = [], className = '' }) {
  return (
    <div className={`bg-ink text-white px-8 lg:px-12 py-10 text-center ${className}`}>
      <h1 className="font-serif text-4xl font-bold">{title}</h1>
      {crumbs.length > 0 && (
        <div className="flex items-center justify-center gap-2 text-[11px] text-white/40 mt-2">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-2">
              {i > 0 && <span>›</span>}
              {c.to ? (
                <Link to={c.to} className="text-white/40 hover:text-gold transition-colors">{c.label}</Link>
              ) : (
                <span className="text-white/60">{c.label}</span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
