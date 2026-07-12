import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconHeart, IconShoppingCart } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import { useWishlistStore } from '@/store/useWishlistStore'
import { useAuthStore } from '@/store/useAuthStore'

const inr = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

export default function Wishlist() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const { items, loading, fetchWishlist, remove } = useWishlistStore()

  useEffect(() => {
    if (isAuthenticated) fetchWishlist()
  }, [isAuthenticated, fetchWishlist])

  if (!isAuthenticated) {
    return (
      <>
        <PageHeader title="My Wishlist" crumbs={[{ label: 'Home', to: '/' }, { label: 'Wishlist' }]} />
        <section className="px-6 lg:px-12 py-20 text-center">
          <p className="text-gray text-sm">Please sign in to view your wishlist</p>
          <Link to="/login" className="inline-block mt-4 px-8 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Sign In</Link>
        </section>
      </>
    )
  }

  return (
    <>
      <PageHeader title="My Wishlist" crumbs={[{ label: 'Home', to: '/' }, { label: 'Wishlist' }]} />
      <section className="px-6 lg:px-12 py-10">
        {loading && items.length === 0 ? (
          <div className="py-20 text-center text-gray text-sm">Loading…</div>
        ) : items.length === 0 ? (
          <div className="text-center py-20">
            <IconHeart size={40} className="text-line mx-auto" />
            <p className="text-gray text-sm mt-4">Your wishlist is empty</p>
            <Link to="/shop" className="inline-block mt-4 px-8 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Discover Products</Link>
          </div>
        ) : (
          <>
            <p className="text-xs text-gray mb-6">{items.length} item{items.length !== 1 ? 's' : ''} saved</p>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {items.map((p) => (
                <div key={p.wishlist_id} className="group border border-line rounded overflow-hidden">
                  <Link to={`/product/${p.slug}`} className="block aspect-[3/4] bg-surface flex items-center justify-center relative overflow-hidden">
                    {p.primary_image ? (
                      <img src={p.primary_image} alt={p.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="text-gray text-xs">No Image</div>
                    )}
                    <button
                      onClick={(e) => { e.preventDefault(); remove(p.product_id) }}
                      aria-label="Remove from wishlist"
                      className="absolute top-2.5 right-2.5 w-[30px] h-[30px] bg-white rounded-full flex items-center justify-center shadow-[0_2px_8px_rgba(0,0,0,0.1)]"
                    >
                      <IconHeart size={14} className="text-maroon-light" fill="currentColor" />
                    </button>
                  </Link>
                  <div className="p-3.5">
                    {p.category_name && <div className="text-[9px] tracking-[2px] text-gold uppercase font-semibold">{p.category_name}</div>}
                    <Link to={`/product/${p.slug}`} className="font-serif text-sm mt-1 font-medium block hover:text-gold transition-colors">{p.name}</Link>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-[15px] font-semibold">{inr(p.selling_price)}</span>
                      {p.mrp > p.selling_price && <span className="text-xs text-gray line-through">{inr(p.mrp)}</span>}
                    </div>
                    <button onClick={() => navigate(`/product/${p.slug}`)} className="w-full mt-3 py-2 flex items-center justify-center gap-2 bg-ink text-white text-[10px] tracking-[1px] uppercase font-bold hover:bg-ink/90 transition-colors">
                      <IconShoppingCart size={13} /> Add to Cart
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </>
  )
}
