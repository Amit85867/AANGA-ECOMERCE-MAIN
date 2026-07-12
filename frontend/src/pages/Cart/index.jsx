import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconMinus, IconPlus, IconX, IconTag } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import { useCartStore } from '@/store/useCartStore'
import { useAuthStore } from '@/store/useAuthStore'

const inr = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

export default function Cart() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const { cart, loading, fetchCart, updateItem, removeItem, applyCoupon, removeCoupon } = useCartStore()
  const [coupon, setCoupon] = useState('')
  const [applying, setApplying] = useState(false)

  useEffect(() => {
    if (isAuthenticated) fetchCart()
  }, [isAuthenticated, fetchCart])

  const handleApply = async () => {
    if (!coupon.trim()) return
    setApplying(true)
    const res = await applyCoupon(coupon)
    setApplying(false)
    if (res?.ok) setCoupon('')
  }

  if (!isAuthenticated) {
    return (
      <>
        <PageHeader title="Shopping Cart" crumbs={[{ label: 'Home', to: '/' }, { label: 'Cart' }]} />
        <section className="px-6 lg:px-12 py-20 text-center">
          <p className="text-gray text-sm">Please sign in to view your cart</p>
          <Link to="/login" className="inline-block mt-4 px-8 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Sign In</Link>
        </section>
      </>
    )
  }

  const items = cart?.items || []

  return (
    <>
      <PageHeader title="Shopping Cart" crumbs={[{ label: 'Home', to: '/' }, { label: 'Cart' }]} />
      <section className="px-6 lg:px-12 py-10">
        {loading && !cart ? (
          <div className="py-20 text-center text-gray text-sm">Loading your cart…</div>
        ) : items.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray text-sm">Your cart is empty</p>
            <Link to="/shop" className="inline-block mt-4 px-8 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Continue Shopping</Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
            {/* Items */}
            <div>
              <div className="hidden md:grid grid-cols-[2fr_1fr_1fr_1fr_40px] gap-4 text-[10px] tracking-[2px] uppercase text-gray font-semibold pb-3 border-b border-line">
                <span>Product</span><span className="text-center">Price</span><span className="text-center">Quantity</span><span className="text-center">Total</span><span />
              </div>
              {items.map((item) => (
                <div key={item.id} className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr_1fr_40px] gap-4 items-center py-5 border-b border-line">
                  <div className="flex items-center gap-4">
                    <Link to={`/product/${item.product_slug}`} className="w-20 h-24 bg-surface flex items-center justify-center shrink-0 overflow-hidden">
                      {item.image_url ? (
                        <img src={item.image_url} alt={item.product_name} className="w-full h-full object-cover" />
                      ) : (
                        <div className="text-[10px] text-gray">No image</div>
                      )}
                    </Link>
                    <div>
                      <Link to={`/product/${item.product_slug}`} className="font-serif text-sm font-medium hover:text-gold transition-colors">{item.product_name}</Link>
                      <div className="text-[11px] text-gray mt-0.5">
                        {item.size && `Size: ${item.size}`}{item.size && item.color_name && ' | '}{item.color_name && `Color: ${item.color_name}`}
                      </div>
                    </div>
                  </div>
                  <div className="text-center text-sm font-medium">{inr(item.unit_price)}</div>
                  <div className="flex items-center justify-center">
                    <div className="flex items-center border border-line">
                      <button onClick={() => updateItem(item.id, item.quantity - 1)} className="w-8 h-8 flex items-center justify-center hover:bg-surface disabled:opacity-40" disabled={item.quantity <= 1}><IconMinus size={12} /></button>
                      <span className="w-8 h-8 flex items-center justify-center text-xs font-medium border-x border-line">{item.quantity}</span>
                      <button onClick={() => updateItem(item.id, item.quantity + 1)} className="w-8 h-8 flex items-center justify-center hover:bg-surface"><IconPlus size={12} /></button>
                    </div>
                  </div>
                  <div className="text-center text-sm font-semibold">{inr(item.line_total)}</div>
                  <button onClick={() => removeItem(item.id)} className="justify-self-center text-gray hover:text-maroon-light transition-colors"><IconX size={16} /></button>
                </div>
              ))}
            </div>

            {/* Summary */}
            <div className="bg-surface p-6 h-fit">
              <h3 className="font-serif text-lg font-bold mb-4">Order Summary</h3>
              <div className="space-y-2.5 text-sm">
                <div className="flex justify-between"><span className="text-gray">Subtotal</span><span>{inr(cart.subtotal)}</span></div>
                {cart.discount > 0 && (
                  <div className="flex justify-between text-green-600"><span>Discount {cart.coupon_code && `(${cart.coupon_code})`}</span><span>−{inr(cart.discount)}</span></div>
                )}
                <div className="flex justify-between"><span className="text-gray">GST (5%)</span><span>{inr(cart.gst)}</span></div>
                <div className="flex justify-between"><span className="text-gray">Delivery</span><span className={cart.delivery_charge === 0 ? 'text-green-600 font-medium' : ''}>{cart.delivery_charge === 0 ? 'FREE' : inr(cart.delivery_charge)}</span></div>
                {cart.delivery_charge > 0 && cart.subtotal < 999 && <p className="text-[11px] text-gold">Add {inr(999 - cart.subtotal)} more for free delivery</p>}
              </div>

              {/* Coupon */}
              <div className="mt-4 pt-4 border-t border-line">
                {cart.coupon_code ? (
                  <div className="flex items-center justify-between bg-white border border-line px-3 py-2.5">
                    <span className="text-xs font-medium text-green-700 flex items-center gap-1.5"><IconTag size={14} /> {cart.coupon_code} applied</span>
                    <button onClick={removeCoupon} className="text-gray hover:text-maroon-light"><IconX size={14} /></button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 flex items-center border border-line bg-white">
                      <IconTag size={14} className="ml-3 text-gray" />
                      <input type="text" value={coupon} onChange={(e) => setCoupon(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleApply()} placeholder="Coupon code" className="flex-1 px-2 py-2.5 text-xs bg-transparent outline-none uppercase" />
                    </div>
                    <button onClick={handleApply} disabled={applying} className="px-4 py-2.5 bg-ink text-white text-[10px] tracking-[1px] uppercase font-bold disabled:opacity-60">{applying ? '…' : 'Apply'}</button>
                  </div>
                )}
              </div>

              <div className="flex justify-between font-bold text-lg mt-4 pt-4 border-t border-line">
                <span>Total</span><span>{inr(cart.total)}</span>
              </div>
              {cart.savings > 0 && <p className="text-[11px] text-green-600 mt-1">You save {inr(cart.savings)} on this order</p>}
              <button onClick={() => navigate('/checkout')} className="block w-full text-center mt-4 py-3.5 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-gold-light transition-colors">Proceed to Checkout</button>
              <Link to="/shop" className="block text-center mt-2 text-xs text-gray hover:text-ink transition-colors">← Continue Shopping</Link>
            </div>
          </div>
        )}
      </section>
    </>
  )
}
