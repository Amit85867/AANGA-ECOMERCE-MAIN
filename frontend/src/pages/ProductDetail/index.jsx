import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { IconHeart, IconTruck, IconRefresh, IconShieldCheck, IconStar, IconMinus, IconPlus } from '@tabler/icons-react'
import { useProductStore } from '@/store/useProductStore'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'
import { toast } from '@/components/ui/Toast'
import apiClient from '@/services/apiClient'
import ProductCard from '@/components/ui/ProductCard'
import PageHeader from '@/components/ui/PageHeader'

export default function ProductDetail() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { product, loading, error, fetchProduct } = useProductStore()
  const addItem = useCartStore((s) => s.addItem)
  const wishlistIds = useWishlistStore((s) => s.productIds)
  const toggleWishlist = useWishlistStore((s) => s.toggle)
  const [selectedSize, setSelectedSize] = useState(null)
  const [selectedColor, setSelectedColor] = useState(null)
  const [qty, setQty] = useState(1)
  const [activeThumb, setActiveThumb] = useState(0)
  const [related, setRelated] = useState([])
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    fetchProduct(slug)
  }, [slug, fetchProduct])

  useEffect(() => {
    if (product?.category_slug) {
      apiClient
        .get('/products', { params: { category: product.category_slug, per_page: 4 } })
        .then(({ data }) => setRelated(data.products.filter((p) => p.slug !== slug)))
        .catch(() => {})
    }
  }, [product?.category_slug, slug])

  useEffect(() => {
    if (product?.variants?.length) {
      const sizes = [...new Set(product.variants.map((v) => v.size).filter(Boolean))]
      if (sizes.length && !selectedSize) setSelectedSize(sizes[0])
      const colors = [...new Map(product.variants.filter((v) => v.color_hex).map((v) => [v.color_hex, v])).values()]
      if (colors.length && !selectedColor) setSelectedColor(colors[0].color_hex)
    }
  }, [product])

  if (loading) {
    return (
      <section className="px-6 lg:px-12 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 animate-pulse">
          <div className="aspect-[3/4] bg-surface rounded" />
          <div className="space-y-4">
            <div className="h-4 bg-surface rounded w-1/3" />
            <div className="h-8 bg-surface rounded w-2/3" />
            <div className="h-6 bg-surface rounded w-1/4" />
            <div className="h-20 bg-surface rounded" />
          </div>
        </div>
      </section>
    )
  }

  if (error || !product) {
    return (
      <section className="px-6 lg:px-12 py-20 text-center">
        <h2 className="font-serif text-2xl font-bold">Product Not Found</h2>
        <p className="text-sm text-gray mt-2">This product may have been removed or doesn't exist.</p>
        <Link to="/shop" className="inline-block mt-4 px-6 py-2.5 bg-ink text-white text-xs tracking-[1.5px] uppercase font-bold">Browse Products</Link>
      </section>
    )
  }

  const sizes = [...new Set(product.variants?.map((v) => v.size).filter(Boolean))]
  const colorMap = new Map()
  product.variants?.forEach((v) => {
    if (v.color_hex && !colorMap.has(v.color_hex)) {
      colorMap.set(v.color_hex, { name: v.color_name, hex: v.color_hex })
    }
  })
  const colors = [...colorMap.values()]
  const images = product.images || []

  const resolveVariant = () => {
    const variants = product.variants || []
    if (!variants.length) return null
    return (
      variants.find(
        (v) =>
          (sizes.length === 0 || v.size === selectedSize) &&
          (colors.length === 0 || v.color_hex === selectedColor),
      ) || null
    )
  }

  const handleAddToCart = async () => {
    if (sizes.length > 0 && !selectedSize) return toast.error('Please select a size')
    if (colors.length > 0 && !selectedColor) return toast.error('Please select a colour')
    const variant = resolveVariant()
    if (!variant) return toast.error('This combination is unavailable')

    setAdding(true)
    const res = await addItem({ variant_id: variant.id, quantity: qty })
    setAdding(false)
    if (res?.needsAuth) {
      toast.info('Please sign in to add items to your cart')
      navigate('/login')
      return false
    }
    return res?.ok
  }

  const handleBuyNow = async () => {
    const ok = await handleAddToCart()
    if (ok) navigate('/checkout')
  }

  const inWishlist = wishlistIds.includes(product.id)

  return (
    <>
      <PageHeader
        title="Product Details"
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Shop', to: '/shop' },
          { label: product.name },
        ]}
      />

      <section className="px-6 lg:px-12 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          {/* Gallery */}
          <div className="flex gap-3">
            {images.length > 1 && (
              <div className="flex flex-col gap-2">
                {images.map((img, i) => (
                  <button
                    key={img.id}
                    onClick={() => setActiveThumb(i)}
                    className={`w-16 h-20 border flex items-center justify-center overflow-hidden ${activeThumb === i ? 'border-gold' : 'border-line'}`}
                  >
                    <img src={img.image_url} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
            <div className="flex-1 aspect-[3/4] bg-surface flex items-center justify-center relative overflow-hidden">
              {images.length > 0 ? (
                <img src={images[activeThumb]?.image_url} alt={product.name} className="w-full h-full object-cover" />
              ) : (
                <div className="text-gray text-sm">No Image</div>
              )}
              {product.badge_label && (
                <span className="absolute top-4 left-4 px-2.5 py-1 text-[9px] tracking-[1px] uppercase font-bold bg-maroon-light text-white">
                  {product.badge_label}
                </span>
              )}
            </div>
          </div>

          {/* Info */}
          <div>
            {product.category_name && (
              <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold">{product.category_name}</div>
            )}
            <h1 className="font-serif text-3xl font-bold mt-1">{product.name}</h1>
            {product.avg_rating && (
              <div className="flex items-center gap-3 mt-2">
                <div className="flex text-gold text-sm">
                  {[...Array(5)].map((_, i) => (
                    <IconStar key={i} size={14} fill={i < Math.round(product.avg_rating) ? 'currentColor' : 'none'} />
                  ))}
                </div>
                <span className="text-xs text-gray">{product.avg_rating} ({product.review_count} reviews)</span>
              </div>
            )}

            <div className="flex items-baseline gap-3 mt-4">
              <span className="text-3xl font-bold">&#8377;{product.selling_price?.toLocaleString('en-IN')}</span>
              {product.mrp > product.selling_price && (
                <>
                  <span className="text-lg text-gray line-through">&#8377;{product.mrp?.toLocaleString('en-IN')}</span>
                  <span className="text-sm text-maroon-light font-semibold">{product.discount_percent}% off</span>
                </>
              )}
            </div>

            {product.description && (
              <p className="text-[13px] text-gray leading-[1.8] mt-4">{product.description}</p>
            )}

            {/* Color */}
            {colors.length > 0 && (
              <div className="mt-6">
                <h4 className="text-[11px] font-semibold tracking-[0.5px] uppercase mb-2">
                  Colour — <span className="text-gold">{colors.find((c) => c.hex === selectedColor)?.name}</span>
                </h4>
                <div className="flex gap-2.5">
                  {colors.map((c) => (
                    <button
                      key={c.hex}
                      onClick={() => setSelectedColor(c.hex)}
                      className={`w-8 h-8 rounded-full border-[3px] transition-colors ${selectedColor === c.hex ? 'border-gold' : 'border-transparent'}`}
                      style={{ background: c.hex, boxShadow: c.hex === '#F5F0E8' ? 'inset 0 0 0 1px #ddd' : 'none' }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Size */}
            {sizes.length > 0 && (
              <div className="mt-5">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-[11px] font-semibold tracking-[0.5px] uppercase">Size</h4>
                </div>
                <div className="flex gap-2">
                  {sizes.map((s) => (
                    <button
                      key={s}
                      onClick={() => setSelectedSize(s)}
                      className={`w-11 h-11 text-xs font-medium border transition-colors ${selectedSize === s ? 'border-gold bg-gold text-ink' : 'border-line hover:border-gold'}`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Qty + Buttons */}
            <div className="flex items-center gap-4 mt-7">
              <div className="flex items-center border border-line">
                <button onClick={() => setQty(Math.max(1, qty - 1))} className="w-10 h-10 flex items-center justify-center hover:bg-surface transition-colors"><IconMinus size={14} /></button>
                <span className="w-10 h-10 flex items-center justify-center text-sm font-medium border-x border-line">{qty}</span>
                <button onClick={() => setQty(qty + 1)} className="w-10 h-10 flex items-center justify-center hover:bg-surface transition-colors"><IconPlus size={14} /></button>
              </div>
              <button onClick={handleAddToCart} disabled={adding} className="flex-1 h-11 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-60">{adding ? 'Adding…' : 'Add to Cart'}</button>
              <button onClick={() => toggleWishlist(product.id)} className={`h-11 px-4 border transition-colors ${inWishlist ? 'border-gold bg-gold/10' : 'border-line hover:border-gold'}`}>
                <IconHeart size={18} className={inWishlist ? 'text-maroon-light' : 'text-gray'} fill={inWishlist ? 'currentColor' : 'none'} />
              </button>
            </div>

            <button onClick={handleBuyNow} disabled={adding} className="w-full h-11 mt-3 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-gold-light transition-colors disabled:opacity-60">Buy Now</button>

            {/* Meta */}
            <div className="mt-7 pt-5 border-t border-line space-y-3">
              <div className="flex items-center gap-3 text-xs text-gray"><IconTruck size={16} className="text-gold" /> Free delivery on orders above &#8377;999</div>
              <div className="flex items-center gap-3 text-xs text-gray"><IconRefresh size={16} className="text-gold" /> Easy 7-day return & exchange</div>
              <div className="flex items-center gap-3 text-xs text-gray"><IconShieldCheck size={16} className="text-gold" /> 100% authentic products guaranteed</div>
            </div>
          </div>
        </div>
      </section>

      {/* Related */}
      {related.length > 0 && (
        <section className="px-6 lg:px-12 py-10 border-t border-line">
          <h2 className="font-serif text-2xl font-bold mb-6">You May Also Like</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {related.slice(0, 4).map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </>
  )
}
