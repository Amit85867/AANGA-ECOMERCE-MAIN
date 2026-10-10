import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconLock, IconShoppingBag, IconTag, IconTrash, IconX } from '@tabler/icons-react'
import { useCartStore } from '@/store/useCartStore'
import { useAuthStore } from '@/store/useAuthStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import OrderSummary from '@/components/ui/OrderSummary'
import { QuantityStepper } from '@/components/ui/Field'
import { Container, EmptyState, PageTitle, Skeleton } from '@/components/ui/Display'
import { inr } from '@/utils/format'
import Seo from '@/components/Seo'

function CartLine({ item, onQuantity, onRemove, busy }) {
  return (
    <li className="flex gap-4 py-5 sm:gap-6">
      <Link
        to={`/product/${item.product_slug}`}
        className="h-32 w-24 shrink-0 overflow-hidden rounded-card bg-fill sm:h-36 sm:w-28"
      >
        {item.image_url && (
          <img
            src={item.image_url} alt="" width="224" height="288" loading="lazy" decoding="async"
            className="h-full w-full object-cover"
          />
        )}
      </Link>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Link to={`/product/${item.product_slug}`} className="text-sm font-medium text-fg hover:underline underline-offset-2">
              {item.product_name}
            </Link>
            <p className="mt-1 text-xs text-muted">
              {[item.size && `Size ${item.size}`, item.color_name].filter(Boolean).join(' · ')}
            </p>
          </div>
          <p className="shrink-0 text-sm font-semibold tabular-nums text-fg">{inr(item.line_total)}</p>
        </div>

        {item.quantity > 1 && <p className="mt-1 text-xs text-subtle tabular-nums">{inr(item.unit_price)} each</p>}

        <div className="mt-auto flex items-center justify-between gap-3 pt-4">
          <QuantityStepper
            size="sm" value={item.quantity} disabled={busy}
            label={`Quantity of ${item.product_name}`}
            onChange={(next) => onQuantity(item, next)}
          />
          <button
            type="button" onClick={() => onRemove(item)} disabled={busy}
            className="inline-flex items-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium text-muted hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
          >
            <IconTrash size={14} aria-hidden="true" /> Remove
          </button>
        </div>
      </div>
    </li>
  )
}

export default function Cart() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const initializing = useAuthStore((s) => s.initializing)
  const { cart, loading, fetchCart, updateItem, removeItem, applyCoupon, removeCoupon } = useCartStore()
  const [coupon, setCoupon] = useState('')
  const [applying, setApplying] = useState(false)
  const [busyItem, setBusyItem] = useState(null)

  useEffect(() => {
    if (isAuthenticated) fetchCart()
  }, [isAuthenticated, fetchCart])

  const changeQuantity = async (item, quantity) => {
    setBusyItem(item.id)
    await updateItem(item.id, quantity)
    setBusyItem(null)
  }

  const remove = async (item) => {
    setBusyItem(item.id)
    await removeItem(item.id)
    setBusyItem(null)
  }

  const apply = async (e) => {
    e.preventDefault()
    if (!coupon.trim() || applying) return
    setApplying(true)
    const res = await applyCoupon(coupon)
    setApplying(false)
    if (res?.ok) setCoupon('')
  }

  const items = cart?.items || []
  const crumbs = [{ label: 'Home', to: '/' }, { label: 'Bag' }]

  let body
  if (initializing || (isAuthenticated && loading && !cart)) {
    body = (
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_24rem]" aria-busy="true">
        <div className="space-y-6">
          {[0, 1].map((i) => (
            <div key={i} className="flex gap-6"><Skeleton className="h-36 w-28" /><div className="flex-1 space-y-3"><Skeleton className="h-4 w-2/3" /><Skeleton className="h-3 w-1/3" /></div></div>
          ))}
        </div>
        <Skeleton className="h-72" />
      </div>
    )
  } else if (!isAuthenticated) {
    body = (
      <EmptyState
        icon={IconShoppingBag}
        title="Sign in to see your bag"
        hint="Your bag is saved to your account, so it follows you across devices."
        action={<Button to="/login">Sign in</Button>}
      />
    )
  } else if (items.length === 0) {
    body = (
      <EmptyState
        icon={IconShoppingBag}
        title="Your bag is empty"
        hint="Add something you like and it will show up here."
        action={<Button to="/shop">Start shopping</Button>}
      />
    )
  } else {
    body = (
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <section aria-label="Items in your bag">
          <ul className="divide-y divide-hairline/60 border-y border-hairline/60">
            {items.map((item) => (
              <CartLine
                key={item.id} item={item} busy={busyItem === item.id}
                onQuantity={changeQuantity} onRemove={remove}
              />
            ))}
          </ul>
          <Link to="/shop" className="mt-5 inline-block text-sm font-medium text-muted underline underline-offset-2 hover:text-fg">
            Continue shopping
          </Link>
        </section>

        <aside aria-label="Order summary">
          <Card className="p-6 lg:sticky lg:top-28">
            <h2 className="display text-xl text-fg mb-5">Order summary</h2>
            <OrderSummary cart={cart}>
              <div className="mt-5 border-t border-hairline/60 pt-5">
                {cart.coupon_code ? (
                  <div className="flex items-center justify-between gap-3 rounded-card bg-fill px-4 py-3">
                    <span className="inline-flex items-center gap-2 text-sm font-medium text-fg">
                      <IconTag size={16} aria-hidden="true" /> {cart.coupon_code} applied
                    </span>
                    <button
                      type="button" onClick={removeCoupon} aria-label={`Remove coupon ${cart.coupon_code}`}
                      className="rounded-full p-1 text-muted hover:bg-fill-strong hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    >
                      <IconX size={16} />
                    </button>
                  </div>
                ) : (
                  <form onSubmit={apply} className="flex items-end gap-2">
                    <Input
                      label="Coupon code" name="coupon" value={coupon} autoComplete="off"
                      onChange={(e) => setCoupon(e.target.value.toUpperCase())}
                      placeholder="Enter code"
                    />
                    <Button type="submit" variant="secondary" disabled={applying || !coupon.trim()}>
                      {applying ? 'Applying…' : 'Apply'}
                    </Button>
                  </form>
                )}
              </div>
            </OrderSummary>

            <Button to="/checkout" size="lg" full className="mt-6">Checkout</Button>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-subtle">
              <IconLock size={12} aria-hidden="true" /> Secure checkout · 7-day easy returns
            </p>
          </Card>
        </aside>
      </div>
    )
  }

  return (
    <>
      <Seo title="Your Bag" noindex />
      <Container className="pb-20">
        <PageTitle title="Your bag" crumbs={crumbs} />
        {body}
      </Container>
    </>
  )
}
