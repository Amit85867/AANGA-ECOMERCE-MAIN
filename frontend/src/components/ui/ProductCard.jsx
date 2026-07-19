import { Link } from 'react-router-dom'
import { IconHeart, IconStarFilled } from '@tabler/icons-react'
import { useWishlistStore } from '@/store/useWishlistStore'

export default function ProductCard({ product }) {
  const {
    id,
    slug,
    name,
    category_name,
    mrp,
    selling_price,
    discount_percent,
    badge_label,
    primary_image,
    colors = [],
    avg_rating,
    review_count,
  } = product

  const wishlistIds = useWishlistStore((s) => s.productIds)
  const toggleWishlist = useWishlistStore((s) => s.toggle)
  const inWishlist = wishlistIds.includes(id)

  const handleWishlist = (e) => {
    e.preventDefault()
    e.stopPropagation()
    toggleWishlist(id)
  }

  return (
    <Link to={`/product/${slug}`} className="group block">
      {/* Image — image-first with minimal padding, per the design system */}
      <div className="relative aspect-[3/4] rounded-card overflow-hidden bg-fill">
        {primary_image ? (
          <img
            src={primary_image}
            alt={name}
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-subtle text-xs">
            No Image
          </div>
        )}

        {badge_label && (
          <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-accent text-white
                           text-[10px] tracking-[0.05em] uppercase font-semibold">
            {badge_label}
          </span>
        )}

        <button
          onClick={handleWishlist}
          aria-label={inWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
          aria-pressed={inWishlist}
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-card/90 backdrop-blur
                     flex items-center justify-center shadow-card
                     transition-transform duration-200 hover:scale-110"
        >
          <IconHeart
            size={17}
            stroke={1.5}
            className={inWishlist ? 'text-accent' : 'text-muted'}
            fill={inWishlist ? 'currentColor' : 'none'}
          />
        </button>
      </div>

      {/* Metadata — generous padding below the photo */}
      <div className="pt-4">
        {category_name && (
          <div className="text-[11px] tracking-[0.1em] text-subtle uppercase font-medium">
            {category_name}
          </div>
        )}

        <div className="flex items-start justify-between gap-3 mt-1">
          <h3 className="text-sm font-medium text-fg leading-snug">{name}</h3>
          <span className="text-sm font-semibold text-fg whitespace-nowrap">
            &#8377;{selling_price?.toLocaleString('en-IN')}
          </span>
        </div>

        {mrp > selling_price && (
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-subtle line-through">
              &#8377;{mrp?.toLocaleString('en-IN')}
            </span>
            <span className="text-xs text-accent font-semibold">{discount_percent}% off</span>
          </div>
        )}

        {avg_rating > 0 && (
          <div className="flex items-center gap-1.5 mt-2">
            <IconStarFilled size={12} className="text-accent" />
            <span className="text-xs font-medium text-fg">{Number(avg_rating).toFixed(1)}</span>
            {review_count > 0 && (
              <span className="text-xs text-subtle">({review_count})</span>
            )}
          </div>
        )}

        {colors.length > 0 && (
          <div className="flex gap-1.5 mt-2.5">
            {colors.map((c, i) => (
              <span
                key={i}
                className="w-3.5 h-3.5 rounded-full ring-1 ring-hairline"
                style={{ background: c }}
              />
            ))}
          </div>
        )}
      </div>
    </Link>
  )
}
