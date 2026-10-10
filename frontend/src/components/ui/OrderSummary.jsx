import { inr } from '@/utils/format'

// Must match FREE_SHIPPING_THRESHOLD in backend/app/services/order_service.py.
// Only used for the "add ₹X more" nudge; the charge itself comes from the API.
const FREE_DELIVERY_FROM = 999

/* The money lines of a cart, identical on the cart and checkout pages. */
export default function OrderSummary({ cart, children }) {
  const short = FREE_DELIVERY_FROM - cart.subtotal
  return (
    <div>
      <dl className="space-y-3 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Subtotal ({cart.item_count} item{cart.item_count === 1 ? '' : 's'})</dt>
          <dd className="tabular-nums text-fg">{inr(cart.subtotal)}</dd>
        </div>
        {cart.discount > 0 && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Discount{cart.coupon_code ? ` (${cart.coupon_code})` : ''}</dt>
            <dd className="tabular-nums font-medium text-fg">−{inr(cart.discount)}</dd>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <dt className="text-muted">GST (5%)</dt>
          <dd className="tabular-nums text-fg">{inr(cart.gst)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted">Delivery</dt>
          <dd className="tabular-nums text-fg">{cart.delivery_charge === 0 ? 'Free' : inr(cart.delivery_charge)}</dd>
        </div>
      </dl>

      {cart.delivery_charge > 0 && short > 0 && (
        <p className="mt-3 rounded-card bg-fill px-3 py-2 text-xs text-muted">
          Add <span className="font-semibold text-fg">{inr(short)}</span> more for free delivery.
        </p>
      )}

      {children}

      <div className="mt-5 flex items-baseline justify-between gap-4 border-t border-hairline/60 pt-5">
        <span className="text-sm font-semibold text-fg">Total</span>
        <span className="display text-2xl text-fg tabular-nums">{inr(cart.total)}</span>
      </div>
      {cart.savings > 0 && (
        <p className="mt-1 text-right text-xs text-muted">You save {inr(cart.savings)} on this order</p>
      )}
    </div>
  )
}
