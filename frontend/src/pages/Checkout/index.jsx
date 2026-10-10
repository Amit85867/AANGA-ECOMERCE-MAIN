import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { IconCash, IconCreditCard, IconLock, IconPlus, IconShoppingBag } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { orderService } from '@/services/orderService'
import { useCartStore } from '@/store/useCartStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useFeatures } from '@/store/useFeaturesStore'
import { toast } from '@/components/ui/toastStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import OrderSummary from '@/components/ui/OrderSummary'
import AddressForm from '@/components/account/AddressForm'
import AddressBlock from '@/components/account/AddressBlock'
import {
  Badge, Container, EmptyState, ErrorState, PageTitle, Skeleton, Stepper,
} from '@/components/ui/Display'
import { inr } from '@/utils/format'
import Seo from '@/components/Seo'

const STEPS = ['Address', 'Payment', 'Review']
const RAZORPAY_SCRIPT = 'https://checkout.razorpay.com/v1/checkout.js'

function loadRazorpay() {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true)
    const s = document.createElement('script')
    s.src = RAZORPAY_SCRIPT
    s.onload = () => resolve(true)
    s.onerror = () => resolve(false)
    document.body.appendChild(s)
  })
}

/* A selectable card backed by a real radio input. */
function Choice({ name, checked, onChange, disabled, children }) {
  return (
    <label
      className={`flex gap-4 rounded-card border p-4 transition-colors ${
        disabled
          ? 'cursor-not-allowed border-hairline/60 opacity-60'
          : checked
            ? 'cursor-pointer border-primary ring-1 ring-primary'
            : 'cursor-pointer border-hairline hover:border-subtle'
      }`}
    >
      <input
        type="radio" name={name} checked={checked} onChange={onChange} disabled={disabled}
        className="mt-1 h-4 w-4 shrink-0 accent-black"
      />
      <div className="min-w-0 flex-1">{children}</div>
    </label>
  )
}

export default function Checkout() {
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const initializing = useAuthStore((s) => s.initializing)
  const user = useAuthStore((s) => s.user)
  const { cart, loading: cartLoading, fetchCart, clearLocal } = useCartStore()
  const { online_payments: onlineAvailable, loaded: featuresLoaded } = useFeatures()
  const idempotencyKey = useRef(null)

  const [step, setStep] = useState(0)
  const [addresses, setAddresses] = useState(null)   // null = not loaded yet
  const [addressError, setAddressError] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [editing, setEditing] = useState(null)       // null | 'new' | address
  const [payment, setPayment] = useState('cod')
  const [placing, setPlacing] = useState(false)

  const loadAddresses = useCallback(() => {
    setAddressError(false)
    return apiClient.get('/addresses')
      .then(({ data }) => {
        setAddresses(data.addresses)
        setSelectedId((current) =>
          data.addresses.some((a) => a.id === current)
            ? current
            : (data.addresses.find((a) => a.is_default) || data.addresses[0])?.id ?? null,
        )
        if (data.addresses.length === 0) setEditing('new')
      })
      .catch(() => setAddressError(true))
  }, [])

  useEffect(() => {
    if (!isAuthenticated) return
    fetchCart()
    loadAddresses()
  }, [isAuthenticated, fetchCart, loadAddresses])

  if (initializing) {
    return <Container className="py-16"><Skeleton className="h-96" /></Container>
  }
  // Checkout is only reachable signed in; come back here afterwards.
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: '/checkout' }} />

  const items = cart?.items || []
  const selected = addresses?.find((a) => a.id === selectedId)

  if (cart && items.length === 0 && !placing) {
    return (
      <Container className="pb-20">
        <PageTitle title="Checkout" />
        <EmptyState
          icon={IconShoppingBag} title="Your bag is empty"
          hint="Add something to your bag before checking out."
          action={<Button to="/shop">Start shopping</Button>}
        />
      </Container>
    )
  }

  const finish = (order) => {
    idempotencyKey.current = null
    clearLocal()
    navigate(`/order-confirmed/${order.order_id}`, { replace: true })
  }

  const placeCod = async () => {
    // One key for every retry of this checkout, so a double submit or a retry
    // after a dropped connection resolves to a single order on the server.
    if (!idempotencyKey.current) {
      idempotencyKey.current = crypto.randomUUID?.() || `cod-${Date.now()}-${Math.random()}`
    }
    const { data } = await orderService.create(
      { address_id: selectedId, payment_method: 'cod' }, idempotencyKey.current,
    )
    finish(data)
  }

  const placeOnline = async () => {
    if (!(await loadRazorpay())) {
      toast.error('Could not load the payment page. Check your connection and try again.')
      return
    }
    let init
    try {
      ({ data: init } = await apiClient.post('/payments/create-order', { address_id: selectedId }))
    } catch (err) {
      toast.error(
        err.response?.status === 503
          ? 'Online payment is not available right now. Please choose cash on delivery.'
          : err.response?.data?.error || 'Could not start the payment.',
      )
      return
    }

    await new Promise((resolve) => {
      const rzp = new window.Razorpay({
        key: init.key_id,
        amount: init.amount,
        currency: init.currency,
        order_id: init.razorpay_order_id,
        name: 'AANGA',
        description: 'Order payment',
        prefill: { name: user?.full_name || '', email: user?.email || '', contact: user?.phone || '' },
        theme: { color: '#000000' },
        handler: async (resp) => {
          try {
            const { data } = await apiClient.post('/payments/verify', {
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
              address_id: selectedId,
            })
            finish(data)
          } catch (err) {
            // The API's message says whether the money was refunded.
            toast.error(err.response?.data?.error || 'We could not confirm your payment. If money was taken it will be refunded.')
          }
          resolve()
        },
        modal: { ondismiss: resolve },
      })
      rzp.open()
    })
  }

  const placeOrder = async () => {
    if (placing) return
    if (!selected) {
      setStep(0)
      toast.error('Choose a delivery address.')
      return
    }
    setPlacing(true)
    try {
      if (payment === 'online') await placeOnline()
      else await placeCod()
    } catch (err) {
      toast.error(err.response?.data?.error || 'We could not place your order. Please try again.')
      // Stock or prices may have changed underneath us; show the truth.
      fetchCart()
    }
    setPlacing(false)
  }

  return (
    <>
      <Seo title="Checkout" noindex />
      <Container className="pb-20">
        <PageTitle title="Checkout" crumbs={[{ label: 'Bag', to: '/cart' }, { label: 'Checkout' }]} />

        <div className="mb-8 overflow-x-auto"><Stepper steps={STEPS} current={step} /></div>

        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <div>
            {/* ── 1. Address ─────────────────────────────── */}
            {step === 0 && (
              <section aria-labelledby="step-address">
                <div className="mb-5 flex items-center justify-between gap-4">
                  <h2 id="step-address" className="display text-xl text-fg">Delivery address</h2>
                  {!editing && addresses?.length > 0 && (
                    <Button variant="ghost" size="sm" onClick={() => setEditing('new')}>
                      <IconPlus size={14} /> Add address
                    </Button>
                  )}
                </div>

                {addressError ? (
                  <ErrorState message="We could not load your addresses." onRetry={loadAddresses} />
                ) : addresses === null ? (
                  <div className="space-y-3"><Skeleton className="h-28" /><Skeleton className="h-28" /></div>
                ) : editing ? (
                  <Card className="p-6">
                    <h3 className="mb-4 text-sm font-semibold text-fg">
                      {editing === 'new' ? 'New address' : 'Edit address'}
                    </h3>
                    <AddressForm
                      address={editing === 'new' ? null : editing}
                      forceDefault={addresses.length === 0}
                      onCancel={addresses.length > 0 ? () => setEditing(null) : undefined}
                      onSaved={async (saved) => {
                        setEditing(null)
                        await loadAddresses()
                        setSelectedId(saved.id)
                      }}
                    />
                  </Card>
                ) : (
                  <>
                    <fieldset className="space-y-3">
                      <legend className="sr-only">Choose a delivery address</legend>
                      {addresses.map((a) => (
                        <Choice key={a.id} name="address" checked={selectedId === a.id} onChange={() => setSelectedId(a.id)}>
                          <div className="flex items-start justify-between gap-3">
                            <AddressBlock address={a} />
                            <div className="flex shrink-0 flex-col items-end gap-2">
                              {a.is_default && <Badge>Default</Badge>}
                              <button
                                type="button" onClick={() => setEditing(a)}
                                className="text-xs font-medium text-muted underline underline-offset-2 hover:text-fg"
                              >
                                Edit
                              </button>
                            </div>
                          </div>
                        </Choice>
                      ))}
                    </fieldset>
                    <Button className="mt-6" size="lg" disabled={!selected} onClick={() => setStep(1)}>
                      Continue to payment
                    </Button>
                  </>
                )}
              </section>
            )}

            {/* ── 2. Payment ─────────────────────────────── */}
            {step === 1 && (
              <section aria-labelledby="step-payment">
                <h2 id="step-payment" className="display text-xl text-fg mb-5">Payment method</h2>
                <fieldset className="space-y-3">
                  <legend className="sr-only">Choose how to pay</legend>
                  <Choice name="payment" checked={payment === 'cod'} onChange={() => setPayment('cod')}>
                    <div className="flex items-center gap-3">
                      <IconCash size={22} stroke={1.5} className="text-fg" aria-hidden="true" />
                      <div>
                        <div className="text-sm font-medium text-fg">Cash on delivery</div>
                        <div className="text-xs text-muted">Pay in cash when your order arrives.</div>
                      </div>
                    </div>
                  </Choice>
                  <Choice
                    name="payment" checked={payment === 'online'} disabled={!onlineAvailable}
                    onChange={() => setPayment('online')}
                  >
                    <div className="flex items-center gap-3">
                      <IconCreditCard size={22} stroke={1.5} className="text-fg" aria-hidden="true" />
                      <div>
                        <div className="text-sm font-medium text-fg">Pay online</div>
                        <div className="text-xs text-muted">
                          {onlineAvailable
                            ? 'UPI, credit or debit card, net banking — securely through Razorpay.'
                            : featuresLoaded
                              ? 'Not available at the moment.'
                              : 'Checking availability…'}
                        </div>
                      </div>
                    </div>
                  </Choice>
                </fieldset>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                  <Button size="lg" onClick={() => setStep(2)}>Review order</Button>
                </div>
              </section>
            )}

            {/* ── 3. Review ──────────────────────────────── */}
            {step === 2 && (
              <section aria-labelledby="step-review">
                <h2 id="step-review" className="display text-xl text-fg mb-5">Review your order</h2>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Card className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">Deliver to</h3>
                      <button type="button" onClick={() => setStep(0)} className="text-xs font-medium text-muted underline underline-offset-2 hover:text-fg">Change</button>
                    </div>
                    <AddressBlock address={selected} />
                  </Card>
                  <Card className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">Payment</h3>
                      <button type="button" onClick={() => setStep(1)} className="text-xs font-medium text-muted underline underline-offset-2 hover:text-fg">Change</button>
                    </div>
                    <p className="text-sm font-medium text-fg">{payment === 'online' ? 'Pay online' : 'Cash on delivery'}</p>
                    <p className="mt-1 text-sm text-muted">
                      {payment === 'online'
                        ? 'You will be taken to Razorpay to complete the payment.'
                        : `Keep ${cart ? inr(cart.total) : 'the amount'} ready in cash.`}
                    </p>
                  </Card>
                </div>

                <Card className="mt-4 p-5">
                  <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Items</h3>
                  <ul className="divide-y divide-hairline/60">
                    {items.map((item) => (
                      <li key={item.id} className="flex items-center gap-4 py-3">
                        <div className="h-16 w-12 shrink-0 overflow-hidden rounded-lg bg-fill">
                          {item.image_url && <img src={item.image_url} alt="" width="96" height="128" loading="lazy" className="h-full w-full object-cover" />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-fg">{item.product_name}</p>
                          <p className="text-xs text-muted">
                            {[item.size && `Size ${item.size}`, item.color_name, `Qty ${item.quantity}`].filter(Boolean).join(' · ')}
                          </p>
                        </div>
                        <p className="text-sm font-medium tabular-nums text-fg">{inr(item.line_total)}</p>
                      </li>
                    ))}
                  </ul>
                </Card>

                <div className="mt-6 flex flex-wrap items-center gap-3">
                  <Button variant="ghost" onClick={() => setStep(1)} disabled={placing}>Back</Button>
                  <Button size="lg" onClick={placeOrder} disabled={placing || !cart}>
                    {placing
                      ? 'Placing your order…'
                      : payment === 'online'
                        ? `Pay ${cart ? inr(cart.total) : ''}`
                        : 'Place order'}
                  </Button>
                </div>
                <p className="mt-3 flex items-center gap-1.5 text-xs text-subtle">
                  <IconLock size={12} aria-hidden="true" />
                  By placing this order you agree to our terms and returns policy.
                </p>
              </section>
            )}
          </div>

          <aside aria-label="Order summary">
            <Card className="p-6 lg:sticky lg:top-28">
              <h2 className="display text-xl text-fg mb-5">Order summary</h2>
              {cart ? <OrderSummary cart={cart} /> : cartLoading ? <Skeleton className="h-48" /> : null}
            </Card>
          </aside>
        </div>
      </Container>
    </>
  )
}
