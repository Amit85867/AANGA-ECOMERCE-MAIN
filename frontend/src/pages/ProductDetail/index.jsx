import { useState, useEffect } from 'react'
import { useCampaignEpoch } from '@/store/useLayoutStore'
import { useSetting } from '@/store/useSettingsStore'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  IconHeart, IconTruck, IconRefresh, IconShieldCheck, IconChevronDown,
} from '@tabler/icons-react'
import { useProductStore } from '@/store/useProductStore'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'
import { toast } from '@/components/ui/toastStore'
import apiClient from '@/services/apiClient'
import ProductCard from '@/components/ui/ProductCard'
import Button from '@/components/ui/Button'
import Chip from '@/components/ui/Chip'
import Seo from '@/components/Seo'
import { QuantityStepper } from '@/components/ui/Field'
import { Breadcrumbs, Container, Price, Rating } from '@/components/ui/Display'
import { useFeatures } from '@/store/useFeaturesStore'
import Reviews from './Reviews'
import { SIZES, responsive } from '@/utils/image'

function Accordion({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-t border-hairline">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between py-5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
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
  const epoch = useCampaignEpoch()
  const setting = useSetting()

  // Loaded again when a campaign starts or ends: the price may have changed.
  useEffect(() => {
    fetchProduct(slug)
  }, [slug, fetchProduct, epoch])

  useEffect(() => {
    if (product?.category_slug) {
      apiClient
        .get('/products', { params: { category: product.category_slug, per_page: 5 } })
        .then(({ data }) => setRelated(data.products.filter((p) => p.slug !== slug)))
        .catch(() => {})
    }
  }, [product?.category_slug, slug])

  // A different product starts from a clean selection.
  useEffect(() => {
    setSelectedSize(null)
    setSelectedColor(null)
    setQty(1)
  }, [slug])

  // Preselect something that can actually be bought: the first variant in
  // stock, falling back to the first variant when everything is sold out.
  useEffect(() => {
    if (!product?.variants?.length || product.slug !== slug) return
    if (selectedSize || selectedColor) return
    const first = product.variants.find((v) => v.stock_qty > 0) || product.variants[0]
    setSelectedSize(first.size || null)
    setSelectedColor(first.color_hex || null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product, slug])

  if (loading) {
    return (
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 py-12" aria-busy="true" aria-label="Loading product">
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
  const seoDescription = (product.meta_description || product.description || `${product.name} — shop now at ${setting('store_name', 'AANGA')}.`)
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

  const variants = product.variants || []
  const variantFor = (size, colorHex) =>
    variants.find(
      (v) => (sizes.length === 0 || v.size === size) && (colors.length === 0 || v.color_hex === colorHex),
    ) || null
  const variant = variantFor(selectedSize, selectedColor)
  const available = variant?.stock_qty ?? 0
  const soldOut = !inStock
  // What the Add button would do right now, in words.
  const blocked = soldOut
    ? 'Sold out'
    : !variant
      ? 'Not available in this size and colour'
      : available === 0
        ? 'This size is sold out'
        : null
  // A size is offered as unavailable (struck through) when the chosen colour
  // has none of it left, instead of failing after the click.
  const sizeAvailable = (size) => (variantFor(size, selectedColor)?.stock_qty ?? 0) > 0

  const handleAddToCart = async () => {
    if (sizes.length > 0 && !selectedSize) return toast.error('Please select a size')
    if (colors.length > 0 && !selectedColor) return toast.error('Please select a colour')
    if (blocked) return toast.error(blocked)

    setAdding(true)
    const res = await addItem({ variant_id: variant.id, quantity: Math.min(qty, available) })
    setAdding(false)
    if (res?.needsAuth) {
      toast.info('Please sign in to add items to your bag')
      // come back to this product after signing in
      navigate('/login', { state: { from: window.location.pathname } })
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
        title={product.meta_title || product.name}
        description={seoDescription}
        image={product.share_image_url || primaryImage}
        type="product"
        jsonLd={productJsonLd}
        breadcrumbs={[
          { name: 'Home', path: '/' },
          { name: 'Shop', path: '/shop' },
          ...(product.category_slug
            ? [{ name: product.category_name, path: `/shop?category=${product.category_slug}` }]
            : []),
          { name: product.name },
        ]}
      />
      <Container as="section" className="py-6 lg:py-10">
        <Breadcrumbs
          className="mb-6"
          items={[
            { label: 'Home', to: '/' },
            { label: 'Shop', to: '/shop' },
            ...(product.category_slug ? [{ label: product.category_name, to: `/shop?category=${product.category_slug}` }] : []),
            { label: product.name },
          ]}
        />

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
                    {...responsive(img.image_url, SIZES.gallery)}
                    alt={`${product.name} — view ${i + 1}`}
                    loading={i === 0 ? 'eager' : 'lazy'}
                    fetchPriority={i === 0 ? 'high' : undefined}
                    decoding="async"
                    width="900"
                    height="1200"
                    className="w-full h-full object-cover"
                  />
                  {i === 0 && product.on_sale && (
                    <span className="sale-badge absolute top-4 left-4 px-2.5 py-1 rounded-full
                                     text-xs tracking-[0.05em] uppercase font-semibold">
                      {product.sale_name}{product.sale_percent ? ` · ${Math.round(product.sale_percent)}% off` : ''}
                    </span>
                  )}
                  {i === 0 && !product.on_sale && product.badge_label && (
                    <span className="absolute top-4 left-4 px-2.5 py-1 rounded-full bg-primary
                                     text-on-primary text-xs tracking-[0.05em] uppercase font-semibold">
                      {product.badge_label}
                    </span>
                  )}
                </div>
              ))
            ) : (
              <div className="sm:col-span-2 aspect-[3/4] rounded-card bg-fill flex items-center justify-center text-muted text-sm">
                No image
              </div>
            )}
          </div>

          {/* Info — sticky on desktop */}
          <div className="lg:sticky lg:top-28 lg:self-start">
            {product.category_name && (
              <div className="text-xs tracking-[0.12em] text-muted uppercase font-semibold">
                {product.category_name}
              </div>
            )}

            <h1 className="display text-3xl lg:text-[40px] leading-tight text-fg mt-2">
              {product.name}
            </h1>

            {product.review_count > 0 && (
              <a href="#reviews-heading" className="mt-3 inline-flex items-center gap-2 text-sm text-muted hover:text-fg">
                <Rating value={product.avg_rating} />
                <span className="underline underline-offset-2">
                  {Number(product.avg_rating).toFixed(1)} · {product.review_count} review{product.review_count === 1 ? '' : 's'}
                </span>
              </a>
            )}

            <div className="mt-4">
              <Price price={product.selling_price} mrp={product.mrp} size="lg" />
              <p className="mt-1 text-xs text-muted">Inclusive of all taxes</p>
            </div>

            {/* Colour */}
            {colors.length > 0 && (
              <div className="mt-8">
                <div className="text-xs font-semibold uppercase tracking-[0.1em] text-muted mb-3">
                  Colour: <span className="text-fg">{activeColorName}</span>
                </div>
                <div className="flex gap-3">
                  {colors.map((c) => (
                    <Chip
                      key={c.hex}
                      color={c.hex}
                      selected={selectedColor === c.hex}
                      onClick={() => { setSelectedColor(c.hex); setQty(1) }}
                      aria-label={c.name}
                      title={c.name}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Size */}
            {sizes.length > 0 && (
              <div className="mt-7">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
                    Select size
                  </span>
                  <Link to="/faq" className="text-xs text-muted underline underline-offset-2 hover:text-fg">
                    Size guide
                  </Link>
                </div>
                <div className="flex flex-wrap gap-3">
                  {sizes.map((s) => (
                    <Chip
                      key={s}
                      selected={selectedSize === s}
                      disabled={!sizeAvailable(s)}
                      aria-label={sizeAvailable(s) ? `Size ${s}` : `Size ${s}, sold out`}
                      onClick={() => { setSelectedSize(s); setQty(1) }}
                    >
                      {s}
                    </Chip>
                  ))}
                </div>
              </div>
            )}

            {/* Stock message: says so before the click, not after it. */}
            <p className="mt-6 text-sm min-h-5" aria-live="polite">
              {blocked ? (
                <span className="font-medium text-danger">{blocked}</span>
              ) : available <= 5 ? (
                <span className="font-medium text-fg">Only {available} left</span>
              ) : (
                <span className="text-muted">In stock</span>
              )}
            </p>

            {/* Quantity + actions */}
            <div className="flex items-center gap-3 mt-3">
              <QuantityStepper
                value={Math.min(qty, Math.max(available, 1))}
                max={Math.max(available, 1)}
                disabled={Boolean(blocked)}
                onChange={setQty}
              />

              <Button size="lg" onClick={handleAddToCart} disabled={adding || Boolean(blocked)} className="flex-1 !h-11">
                {adding ? 'Adding…' : soldOut ? 'Sold out' : 'Add to bag'}
              </Button>

              <button
                type="button"
                onClick={() => toggleWishlist(product.id)}
                aria-label={inWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
                aria-pressed={inWishlist}
                className="w-11 h-11 shrink-0 rounded-card border border-hairline flex items-center
                           justify-center hover:border-primary transition-colors
                           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
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
              full
              onClick={handleBuyNow}
              disabled={adding || Boolean(blocked)}
              className="mt-3"
            >
              Buy now
            </Button>

            <DeliveryCheck />

            {/* Details */}
            <div className="mt-10">
              {product.description && (
                <Accordion title="Description" defaultOpen>
                  <p className="text-sm leading-relaxed text-muted">{product.description}</p>
                </Accordion>
              )}
              {product.care_details && (
                <Accordion title="Fabric & Care">
                  <p className="whitespace-pre-line text-sm leading-relaxed text-muted">{product.care_details}</p>
                </Accordion>
              )}
              <Accordion title="Delivery & Returns">
                <ul className="space-y-3">
                  <li className="flex items-center gap-3 text-sm text-muted">
                    <IconTruck size={18} stroke={1.5} className="text-fg shrink-0" />
                    {Number(setting('free_shipping_threshold', '999')) > 0
                      ? `Free delivery on orders above ₹${Number(setting('free_shipping_threshold', '999')).toLocaleString('en-IN')}`
                      : 'Free delivery on every order'}
                  </li>
                  <li className="flex items-center gap-3 text-sm text-muted">
                    <IconRefresh size={18} stroke={1.5} className="text-fg shrink-0" />
                    {Number(setting('return_window_days', '7')) > 0
                      ? `Easy ${setting('return_window_days', '7')}-day return & exchange`
                      : 'This store does not accept returns'}
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
      </Container>

      <Container className="pb-16">
        <Reviews
          productId={product.id}
          productName={product.name}
          onChanged={() => fetchProduct(slug)}
        />
      </Container>

      {related.length > 0 && (
        <Container as="section" className="pb-20" aria-labelledby="related-heading">
          <h2 id="related-heading" className="display text-2xl lg:text-3xl text-fg mb-8">You may also like</h2>
          <ul className="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-8 sm:gap-x-6">
            {related.slice(0, 4).map((p) => (
              <li key={p.id}><ProductCard product={p} /></li>
            ))}
          </ul>
        </Container>
      )}
    </div>
  )
}

/**
 * PIN-code delivery check.
 *
 * Hidden entirely when the API reports itself unconfigured, so a store without
 * Shiprocket credentials simply does not show the widget rather than showing
 * one that never works.
 */
function DeliveryCheck() {
  const [pincode, setPincode] = useState('')
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const [hidden, setHidden] = useState(false)
  const { delivery_check: enabled } = useFeatures()

  const check = async (e) => {
    e.preventDefault()
    if (!/^[1-9]\d{5}$/.test(pincode)) {
      setError('Enter a valid 6-digit PIN code')
      setResult(null)
      return
    }
    setChecking(true)
    setError('')
    try {
      const { data } = await apiClient.get('/shipping/serviceability', { params: { pincode } })
      if (!data.configured) { setHidden(true); return }
      setResult(data)
    } catch {
      setError('Could not check delivery right now. Please try again.')
    } finally {
      setChecking(false)
    }
  }

  if (hidden || !enabled) return null

  return (
    <div className="mt-6 rounded-card border border-hairline p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <IconTruck size={18} stroke={1.5} className="text-fg shrink-0" />
        Check delivery
      </div>

      <form onSubmit={check} className="mt-3 flex gap-2">
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={pincode}
          onChange={(e) => setPincode(e.target.value.replace(/\D/g, ''))}
          placeholder="Enter PIN code"
          aria-label="PIN code"
          className="flex-1 min-w-0 h-11 rounded-card border border-hairline px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <button
          type="submit"
          disabled={checking}
          className="h-11 rounded-card border border-hairline px-4 text-xs font-semibold uppercase tracking-wider hover:border-primary transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {checking ? 'Checking…' : 'Check'}
        </button>
      </form>

      {error && <p role="alert" className="mt-2 text-xs text-danger">{error}</p>}

      {result && !error && (
        result.serviceable ? (
          <p className="mt-3 text-sm text-muted">
            Delivers to <span className="text-fg font-medium">{result.pincode}</span>
            {result.estimated_days != null && (
              <> in about <span className="text-fg font-medium">{result.estimated_days} day{result.estimated_days === 1 ? '' : 's'}</span></>
            )}
            {result.cod_available && <> · Cash on delivery available</>}
          </p>
        ) : (
          <p className="mt-3 text-sm text-muted">
            Sorry, we don&apos;t deliver to {result.pincode} yet.
          </p>
        )
      )}
    </div>
  )
}
