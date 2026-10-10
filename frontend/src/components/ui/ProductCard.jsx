import { Link } from 'react-router-dom'
import { IconHeart, IconStarFilled } from '@tabler/icons-react'
import { useWishlistStore } from '@/store/useWishlistStore'
import { Price } from '@/components/ui/Display'

export default function ProductCard({ product }) {
  const {
    id,
    slug,
    name,
    category_name,
    mrp,
    selling_price,
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
    <Link
      to={`/product/${slug}`}
      className="group block rounded-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-4"
    >
      {/* Image — image-first with minimal padding, per the design system */}
      <div className="relative aspect-[3/4] rounded-card overflow-hidden bg-fill">
        {primary_image ? (
          <img
            src={primary_image}
            alt={name}
            loading="lazy"
            decoding="async"
            width="600"
            height="800"
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-subtle text-xs">
            No Image
          </div>
        )}

        {badge_label && (
          <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-primary text-on-primary
                           text-xs tracking-[0.05em] uppercase font-semibold">
            {badge_label}
          </span>
        )}

        <button
          onClick={handleWishlist}
          aria-label={inWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
          aria-pressed={inWishlist}
          className="absolute top-2 right-2 w-11 h-11 rounded-full bg-card/90 backdrop-blur
                     flex items-center justify-center shadow-card
                     transition-transform duration-200 hover:scale-110
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
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
          <div className="text-xs tracking-[0.08em] text-subtle uppercase font-medium">
            {category_name}
          </div>
        )}

        <h3 className="mt-1 text-sm font-medium text-fg leading-snug line-clamp-2">{name}</h3>
        <Price price={selling_price} mrp={mrp} size="sm" className="mt-1.5" />

        {avg_rating > 0 && (
          <div className="flex items-center gap-1.5 mt-2">
            <IconStarFilled size={12} className="text-fg" aria-hidden="true" />
            <span className="text-xs font-medium text-fg">{Number(avg_rating).toFixed(1)}</span>
            {review_count > 0 && (
              <span className="text-xs text-subtle">({review_count})</span>
            )}
          </div>
        )}

        {colors.length > 0 && (
          <div className="flex gap-1.5 mt-2.5" aria-hidden="true">
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
