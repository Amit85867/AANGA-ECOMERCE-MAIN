import { Link } from 'react-router-dom'
import { IconHeart } from '@tabler/icons-react'
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
      className="group border border-line rounded overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_16px_40px_rgba(0,0,0,0.07)]"
    >
      <div className="aspect-[3/4] bg-surface flex items-center justify-center relative overflow-hidden">
        {primary_image ? (
          <img src={primary_image} alt={name} className="w-full h-full object-cover" />
        ) : (
          <div className="text-gray text-xs">No Image</div>
        )}
        {badge_label && (
          <span className="absolute top-2.5 left-2.5 px-2 py-0.5 text-[9px] tracking-[1px] uppercase font-bold bg-maroon-light text-white">
            {badge_label}
          </span>
        )}
        <button
          onClick={handleWishlist}
          aria-label={inWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
          className="absolute top-2.5 right-2.5 w-[30px] h-[30px] bg-white rounded-full flex items-center justify-center shadow-[0_2px_8px_rgba(0,0,0,0.1)]"
        >
          <IconHeart size={14} className={inWishlist ? 'text-maroon-light' : 'text-gray'} fill={inWishlist ? 'currentColor' : 'none'} />
        </button>
      </div>
      <div className="p-3.5">
        {category_name && (
          <div className="text-[9px] tracking-[2px] text-gold uppercase font-semibold">{category_name}</div>
        )}
        <div className="font-serif text-sm mt-1 font-medium">{name}</div>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[15px] font-semibold">&#8377;{selling_price?.toLocaleString('en-IN')}</span>
          {mrp > selling_price && (
            <>
              <span className="text-xs text-gray line-through">&#8377;{mrp?.toLocaleString('en-IN')}</span>
              <span className="text-[10px] text-maroon-light font-semibold">{discount_percent}% off</span>
            </>
          )}
        </div>
        {colors.length > 0 && (
          <div className="flex gap-1.5 mt-2">
            {colors.map((c, i) => (
              <span
                key={i}
                className="w-3 h-3 rounded-full border-2 border-white shadow-[0_0_0_1px_#e8e4dc]"
                style={{ background: c }}
              />
            ))}
          </div>
        )}
      </div>
    </Link>
  )
}
