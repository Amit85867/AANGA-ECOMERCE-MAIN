import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  IconHeart, IconTruck, IconRefresh, IconShieldCheck,
  IconStarFilled, IconMinus, IconPlus, IconChevronDown,
} from '@tabler/icons-react'
import { useProductStore } from '@/store/useProductStore'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'
import { toast } from '@/components/ui/Toast'
import apiClient from '@/services/apiClient'
import ProductCard from '@/components/ui/ProductCard'
import Button from '@/components/ui/Button'
import Chip from '@/components/ui/Chip'
import Seo from '@/components/Seo'

function Accordion({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-t border-hairline">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between py-5 text-left"
      >
        <span className="text-xs font-semibold uppercase tracking-[0.1em] text-fg">{title}</span>
        <IconChevronDown
          size={18}
          stroke={1.5}
          className={`text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && <div className="pb-6 -mt-1">{children}</div>}
    </div>
  )
}

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
  const [related, setRelated] = useState([])
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    fetchProduct(slug)
  }, [slug, fetchProduct])

  useEffect(() => {
    if (product?.category_slug) {
      apiClient
        .get('/products', { params: { category: product.category_slug, per_page: 5 } })
        .then(({ data }) => setRelated(data.products.filter((p) => p.slug !== slug)))
        .catch(() => {})
    }
  }, [product?.category_slug, slug])

  useEffect(() => {
    if (product?.variants?.length) {
      const sizes = [...new Set(product.variants.map((v) => v.size).filter(Boolean))]
      if (sizes.length && !selectedSize) setSelectedSize(sizes[0])
      const colors = [...new Map(
        product.variants.filter((v) => v.color_hex).map((v) => [v.color_hex, v]),
      ).values()]
      if (colors.length && !selectedColor) setSelectedColor(colors[0].color_hex)
    }
  }, [product])

  if (loading) {
    return (
      <section className="max-w-[1280px] mx-auto px-4 md:px-8 lg:px-12 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 animate-pulse">
          <div className="aspect-[3/4] bg-fill rounded-card" />
          <div className="space-y-4 pt-4">
            <div className="h-3 bg-fill rounded w-1/4" />
            <div className="h-10 bg-fill rounded w-3/4" />
            <div className="h-6 bg-fill rounded w-1/4" />
            <div className="h-24 bg-fill rounded" />
          </div>
        </div>
      </section>
    )
  }

  if (error || !product) {
    return (
      <section className="max-w-[1280px] mx-auto px-4 py-24 text-center">
        <h2 className="display text-3xl text-fg">Product not found</h2>
        <p className="text-muted mt-3">This product may have been removed or never existed.</p>
        <Button to="/shop" className="mt-8">Browse products</Button>
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
  const activeColorName = colors.find((c) => c.hex === selectedColor)?.name

  const primaryImage =
    images.find((i) => i.is_primary)?.image_url || images[0]?.image_url
  const inStock = (product.variants || []).some((v) => v.stock_qty > 0)
  const seoDescription = (product.description || `${product.name} — shop now at AANGA.`)
    .replace(/\s+/g, ' ')
    .slice(0, 160)
  const productJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    ...(product.description ? { description: product.description } : {}),
    ...(images.length ? { image: images.map((i) => i.image_url) } : {}),
    brand: { '@type': 'Brand', name: 'AANGA' },
    ...(product.category_name ? { category: product.category_name } : {}),
    offers: {
      '@type': 'Offer',
      priceCurrency: 'INR',
      price: Number(product.selling_price),
      availability: inStock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
      ...(typeof window !== 'undefined' ? { url: window.location.href } : {}),
    },
    ...(product.review_count > 0
      ? {
          aggregateRating: {
            '@type': 'AggregateRating',
            ratingValue: Number(product.avg_rating),
            reviewCount: product.review_count,
          },
        }
      : {}),
  }

  const resolveVariant = () => {
    const variants = product.variants || []
    if (!variants.length) return null
    return variants.find(
      (v) =>
        (sizes.length === 0 || v.size === selectedSize) &&
        (colors.length === 0 || v.color_hex === selectedColor),
    ) || null
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
      toast.info('Please sign in to add items to your bag')
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
    <div className="bg-bg">
      <Seo
        title={product.name}
        description={seoDescription}
        image={primaryImage}
        type="product"
        jsonLd={productJsonLd}
      />
      <section className="max-w-[1280px] mx-auto px-4 md:px-8 lg:px-12 py-8 lg:py-12">
        {/* Breadcrumb — kept slim for navigation and SEO */}
        <nav aria-label="Breadcrumb" className="text-xs text-subtle mb-8">
          <Link to="/" className="hover:text-fg transition-colors">Home</Link>
          <span className="mx-2">/</span>
          <Link to="/shop" className="hover:text-fg transition-colors">Shop</Link>
          <span className="mx-2">/</span>
          <span className="text-muted">{product.name}</span>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14">
          {/* Gallery — image-first grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {images.length > 0 ? (
              images.map((img, i) => (
                <div
                  key={img.id}
                  className={`relative aspect-[3/4] rounded-card overflow-hidden bg-fill ${
                    images.length === 1 ? 'sm:col-span-2' : ''
                  }`}
                >
                  <img
                    src={img.image_url}
                    alt={`${product.name} — view ${i + 1}`}
                    loading={i === 0 ? 'eager' : 'lazy'}
                    className="w-full h-full object-cover"
                  />
                  {i === 0 && product.badge_label && (
                    <span className="absolute top-4 left-4 px-2.5 py-1 rounded-full bg-accent
                                     text-white text-[10px] tracking-[0.05em] uppercase font-semibold">
                      {product.badge_label}
                    </span>
                  )}
                </div>
              ))
            ) : (
              <div className="sm:col-span-2 aspect-[3/4] rounded-card bg-fill flex items-center justify-center text-subtle text-sm">
                No image
              </div>
            )}
          </div>

          {/* Info — sticky on desktop */}
          <div className="lg:sticky lg:top-28 lg:self-start">
            {product.category_name && (
              <div className="text-[11px] tracking-[0.15em] text-accent uppercase font-semibold">
                {product.category_name}
              </div>
            )}

            <h1 className="display text-3xl lg:text-[40px] leading-tight text-fg mt-2">
              {product.name}
            </h1>

            {product.avg_rating > 0 && (
              <div className="flex items-center gap-2 mt-3">
                <IconStarFilled size={14} className="text-accent" />
                <span className="text-sm font-medium text-fg">
                  {Number(product.avg_rating).toFixed(1)}
                </span>
                <span className="text-sm text-subtle">({product.review_count} reviews)</span>
              </div>
            )}

            <div className="flex items-baseline gap-3 mt-4">
              <span className="text-2xl font-semibold text-fg">
                &#8377;{product.selling_price?.toLocaleString('en-IN')}
              </span>
              {product.mrp > product.selling_price && (
                <>
                  <span className="text-base text-subtle line-through">
                    &#8377;{product.mrp?.toLocaleString('en-IN')}
                  </span>
                  <span className="text-sm text-accent font-semibold">
                    {product.discount_percent}% off
                  </span>
                </>
              )}
            </div>

            {/* Colour */}
            {colors.length > 0 && (
              <div className="mt-8">
                <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted mb-3">
                  Colour: <span className="text-fg">{activeColorName}</span>
                </div>
                <div className="flex gap-3">
                  {colors.map((c) => (
                    <Chip
                      key={c.hex}
                      color={c.hex}
                      selected={selectedColor === c.hex}
                      onClick={() => setSelectedColor(c.hex)}
                      aria-label={c.name}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Size */}
            {sizes.length > 0 && (
              <div className="mt-7">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">
                    Select size
                  </span>
                  <Link to="/faq" className="text-xs text-muted underline underline-offset-2 hover:text-fg">
                    Size guide
                  </Link>
                </div>
                <div className="flex flex-wrap gap-3">
                  {sizes.map((s) => (
                    <Chip key={s} selected={selectedSize === s} onClick={() => setSelectedSize(s)}>
                      {s}
                    </Chip>
                  ))}
                </div>
              </div>
            )}

            {/* Quantity + actions */}
            <div className="flex items-center gap-3 mt-8">
              <div className="flex items-center rounded-card border border-hairline h-14">
                <button
                  onClick={() => setQty(Math.max(1, qty - 1))}
                  aria-label="Decrease quantity"
                  className="w-11 h-full flex items-center justify-center text-muted hover:text-fg"
                >
                  <IconMinus size={15} />
                </button>
                <span className="w-8 text-center text-sm font-medium text-fg">{qty}</span>
                <button
                  onClick={() => setQty(qty + 1)}
                  aria-label="Increase quantity"
                  className="w-11 h-full flex items-center justify-center text-muted hover:text-fg"
                >
                  <IconPlus size={15} />
                </button>
              </div>

              <Button size="lg" onClick={handleAddToCart} disabled={adding} className="flex-1">
                {adding ? 'Adding…' : 'Add to Bag'}
              </Button>

              <button
                onClick={() => toggleWishlist(product.id)}
                aria-label={inWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
                aria-pressed={inWishlist}
                className="w-14 h-14 rounded-card border border-hairline flex items-center
                           justify-center hover:border-primary transition-colors"
              >
                <IconHeart
                  size={20}
                  stroke={1.5}
                  className={inWishlist ? 'text-accent' : 'text-muted'}
                  fill={inWishlist ? 'currentColor' : 'none'}
                />
              </button>
            </div>

            <Button
              variant="secondary"
              size="lg"
              full
              onClick={handleBuyNow}
              disabled={adding}
              className="mt-3"
            >
              Buy Now
            </Button>

            {/* Details */}
            <div className="mt-10">
              {product.description && (
                <Accordion title="Description" defaultOpen>
                  <p className="text-sm leading-relaxed text-muted">{product.description}</p>
                </Accordion>
              )}
              <Accordion title="Delivery & Returns">
                <ul className="space-y-3">
                  <li className="flex items-center gap-3 text-sm text-muted">
                    <IconTruck size={18} stroke={1.5} className="text-fg shrink-0" />
                    Free delivery on orders above &#8377;999
                  </li>
                  <li className="flex items-center gap-3 text-sm text-muted">
                    <IconRefresh size={18} stroke={1.5} className="text-fg shrink-0" />
                    Easy 7-day return &amp; exchange
                  </li>
                  <li className="flex items-center gap-3 text-sm text-muted">
                    <IconShieldCheck size={18} stroke={1.5} className="text-fg shrink-0" />
                    100% authentic products guaranteed
                  </li>
                </ul>
              </Accordion>
            </div>
          </div>
        </div>
      </section>

      {/* Complete the Look */}
      {related.length > 0 && (
        <section className="max-w-[1280px] mx-auto px-4 md:px-8 lg:px-12 pb-20">
          <h2 className="display text-2xl lg:text-3xl text-fg mb-8">Complete the Look</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
            {related.slice(0, 4).map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
