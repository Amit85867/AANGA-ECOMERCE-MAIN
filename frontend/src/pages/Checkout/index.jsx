import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconCheck, IconPlus, IconMapPin } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import apiClient from '@/services/apiClient'
import { orderService } from '@/services/orderService'
import { useCartStore } from '@/store/useCartStore'
import { useAuthStore } from '@/store/useAuthStore'
import { toast } from '@/components/ui/Toast'

const STEPS = ['Address', 'Payment', 'Confirm']
const inr = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

const PAYMENT_METHODS = [
  { id: 'cod', backend: 'cod', label: 'Cash on Delivery', desc: 'Pay when your order arrives', online: false },
  { id: 'upi', backend: 'upi', label: 'UPI (GPay / PhonePe / Paytm)', desc: 'Pay securely via Razorpay', online: true },
  { id: 'card', backend: 'credit_card', label: 'Credit / Debit Card', desc: 'Visa, Mastercard, RuPay', online: true },
  { id: 'netbanking', backend: 'net_banking', label: 'Net Banking', desc: 'All major banks', online: true },
]

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

const emptyAddr = { full_name: '', phone: '', line1: '', line2: '', city: '', state: '', pin_code: '' }

export default function Checkout() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()
  const { cart, fetchCart, clearLocal } = useCartStore()

  const [step, setStep] = useState(0)
  const [payment, setPayment] = useState('cod')
  const [addresses, setAddresses] = useState([])
  const [selectedAddr, setSelectedAddr] = useState(null)
  const [showAddrForm, setShowAddrForm] = useState(false)
  const [addrForm, setAddrForm] = useState(emptyAddr)
  const [savingAddr, setSavingAddr] = useState(false)
  const [placing, setPlacing] = useState(false)
  const [placedOrder, setPlacedOrder] = useState(null)

  const loadAddresses = () => {
    apiClient.get('/addresses').then(({ data }) => {
      setAddresses(data.addresses)
      const def = data.addresses.find((a) => a.is_default) || data.addresses[0]
      if (def) setSelectedAddr(def.id)
      setShowAddrForm(data.addresses.length === 0)
    }).catch(() => {})
  }

  useEffect(() => {
    if (!isAuthenticated) return
    fetchCart()
    loadAddresses()
  }, [isAuthenticated, fetchCart])

  if (!isAuthenticated) {
    return (
      <>
        <PageHeader title="Checkout" crumbs={[{ label: 'Home', to: '/' }, { label: 'Checkout' }]} />
        <section className="px-6 lg:px-12 py-20 text-center">
          <p className="text-gray text-sm">Please sign in to checkout</p>
          <Link to="/login" className="inline-block mt-4 px-8 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Sign In</Link>
        </section>
      </>
    )
  }

  // Order success screen
  if (placedOrder) {
    return (
      <>
        <PageHeader title="Order Confirmed" crumbs={[{ label: 'Home', to: '/' }, { label: 'Order Confirmed' }]} />
        <section className="px-6 lg:px-12 py-16 text-center max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto"><IconCheck size={32} className="text-green-600" /></div>
          <h2 className="font-serif text-2xl font-bold mt-5">Thank you for your order!</h2>
          <p className="text-sm text-gray mt-2">Your order <span className="font-semibold text-ink">{placedOrder.order_number}</span> has been placed successfully.</p>
          <p className="text-xs text-gray mt-1">We'll send updates as it moves through packing and delivery.</p>
          <div className="flex gap-3 justify-center mt-7">
            <Link to="/account" className="px-6 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">View My Orders</Link>
            <Link to="/shop" className="px-6 py-3 border border-line text-[11px] tracking-[2px] uppercase font-bold hover:border-ink transition-colors">Continue Shopping</Link>
          </div>
        </section>
      </>
    )
  }

  const items = cart?.items || []
  if (cart && items.length === 0) {
    return (
      <>
        <PageHeader title="Checkout" crumbs={[{ label: 'Home', to: '/' }, { label: 'Checkout' }]} />
        <section className="px-6 lg:px-12 py-20 text-center">
          <p className="text-gray text-sm">Your cart is empty</p>
          <Link to="/shop" className="inline-block mt-4 px-8 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Browse Products</Link>
        </section>
      </>
    )
  }

  const handleSaveAddress = async (e) => {
    e.preventDefault()
    if (addrForm.pin_code.length !== 6) return toast.error('Pincode must be 6 digits')
    setSavingAddr(true)
    try {
      const { data } = await apiClient.post('/addresses', { ...addrForm, is_default: addresses.length === 0 })
      setAddresses((prev) => [...prev, data])
      setSelectedAddr(data.id)
      setShowAddrForm(false)
      setAddrForm(emptyAddr)
      toast.success('Address saved')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not save address')
    }
    setSavingAddr(false)
  }

  const placeCod = async (method) => {
    const { data } = await orderService.create({ address_id: selectedAddr, payment_method: method.backend })
    clearLocal()
    setPlacedOrder(data)
  }

  const placeOnline = async (method) => {
    const ok = await loadRazorpay()
    if (!ok) return toast.error('Could not load payment gateway. Please try again.')

    // 1. Ask the backend to create a Razorpay order for the cart total
    let init
    try {
      const { data } = await apiClient.post('/payments/create-order', { address_id: selectedAddr })
      init = data
    } catch (err) {
      if (err.response?.status === 503) return toast.error('Online payments are not enabled yet. Please use Cash on Delivery.')
      return toast.error(err.response?.data?.error || 'Could not start payment')
    }

    // 2. Open Razorpay checkout
    await new Promise((resolve) => {
      const rzp = new window.Razorpay({
        key: init.key_id,
        amount: init.amount,
        currency: init.currency,
        order_id: init.razorpay_order_id,
        name: 'AANGA',
        description: 'Order payment',
        prefill: { name: user?.full_name || '', email: user?.email || '', contact: user?.phone || '' },
        theme: { color: '#C8963E' },
        handler: async (resp) => {
          // 3. Verify signature on the backend, which then places the order
          try {
            const { data } = await apiClient.post('/payments/verify', {
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
              address_id: selectedAddr,
              payment_method: method.id,
            })
            clearLocal()
            setPlacedOrder(data)
          } catch (err) {
            toast.error(err.response?.data?.error || 'Payment verification failed')
          }
          resolve()
        },
        modal: { ondismiss: () => resolve() },
      })
      rzp.open()
    })
  }

  const handlePlaceOrder = async () => {
    if (!selectedAddr) return toast.error('Please select a delivery address')
    const method = PAYMENT_METHODS.find((m) => m.id === payment)
    if (!method) return

    setPlacing(true)
    try {
      if (method.online) await placeOnline(method)
      else await placeCod(method)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not place order')
    }
    setPlacing(false)
  }

  const activeAddr = addresses.find((a) => a.id === selectedAddr)
  const inputCls = 'w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors'
  const labelCls = 'text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5'

  return (
    <>
      <PageHeader title="Checkout" crumbs={[{ label: 'Home', to: '/' }, { label: 'Cart', to: '/cart' }, { label: 'Checkout' }]} />
      <section className="px-6 lg:px-12 py-10">
        {/* Stepper */}
        <div className="flex items-center justify-center gap-0 mb-10 max-w-md mx-auto">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 ${i <= step ? 'bg-gold border-gold text-ink' : 'border-line text-gray'}`}>
                  {i < step ? <IconCheck size={14} /> : i + 1}
                </div>
                <span className={`text-[10px] mt-1.5 tracking-[1px] uppercase ${i <= step ? 'text-ink font-semibold' : 'text-gray'}`}>{s}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`h-[2px] flex-1 -mt-4 ${i < step ? 'bg-gold' : 'bg-line'}`} />}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
          {/* Form */}
          <div className="bg-white border border-line p-6">
            {step === 0 && (
              <>
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-serif text-lg font-bold">Delivery Address</h3>
                  {addresses.length > 0 && !showAddrForm && (
                    <button onClick={() => setShowAddrForm(true)} className="text-xs text-gold font-semibold flex items-center gap-1"><IconPlus size={14} /> Add New</button>
                  )}
                </div>

                {/* Existing addresses */}
                {!showAddrForm && addresses.length > 0 && (
                  <div className="space-y-3">
                    {addresses.map((a) => (
                      <label key={a.id} className={`flex items-start gap-3 p-4 border cursor-pointer transition-colors ${selectedAddr === a.id ? 'border-gold bg-cream/40' : 'border-line hover:border-gold/50'}`}>
                        <input type="radio" name="addr" checked={selectedAddr === a.id} onChange={() => setSelectedAddr(a.id)} className="accent-gold mt-1" />
                        <div className="text-sm">
                          <div className="font-medium">{a.full_name} <span className="text-gray font-normal">· {a.phone}</span></div>
                          <div className="text-xs text-gray mt-0.5">{a.line1}{a.line2 ? `, ${a.line2}` : ''}, {a.city}, {a.state} - {a.pin_code}</div>
                          {a.is_default && <span className="inline-block mt-1 text-[9px] tracking-[1px] uppercase text-gold font-bold">Default</span>}
                        </div>
                      </label>
                    ))}
                  </div>
                )}

                {/* New address form */}
                {showAddrForm && (
                  <form onSubmit={handleSaveAddress}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div><label className={labelCls}>Full Name *</label><input required value={addrForm.full_name} onChange={(e) => setAddrForm((f) => ({ ...f, full_name: e.target.value }))} className={inputCls} placeholder="Enter full name" /></div>
                      <div><label className={labelCls}>Phone *</label><input required value={addrForm.phone} onChange={(e) => setAddrForm((f) => ({ ...f, phone: e.target.value }))} className={inputCls} placeholder="10-digit mobile" /></div>
                      <div className="md:col-span-2"><label className={labelCls}>Address *</label><input required value={addrForm.line1} onChange={(e) => setAddrForm((f) => ({ ...f, line1: e.target.value }))} className={inputCls} placeholder="House no., Street, Area" /></div>
                      <div className="md:col-span-2"><label className={labelCls}>Landmark / Apartment</label><input value={addrForm.line2} onChange={(e) => setAddrForm((f) => ({ ...f, line2: e.target.value }))} className={inputCls} placeholder="Optional" /></div>
                      <div><label className={labelCls}>City *</label><input required value={addrForm.city} onChange={(e) => setAddrForm((f) => ({ ...f, city: e.target.value }))} className={inputCls} placeholder="City" /></div>
                      <div><label className={labelCls}>State *</label><input required value={addrForm.state} onChange={(e) => setAddrForm((f) => ({ ...f, state: e.target.value }))} className={inputCls} placeholder="State" /></div>
                      <div><label className={labelCls}>Pincode *</label><input required value={addrForm.pin_code} onChange={(e) => setAddrForm((f) => ({ ...f, pin_code: e.target.value.replace(/\D/g, '').slice(0, 6) }))} className={inputCls} placeholder="6-digit pincode" /></div>
                    </div>
                    <div className="flex gap-3 mt-5">
                      <button type="submit" disabled={savingAddr} className="px-6 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-60">{savingAddr ? 'Saving…' : 'Save Address'}</button>
                      {addresses.length > 0 && <button type="button" onClick={() => setShowAddrForm(false)} className="px-6 py-3 border border-line text-[11px] tracking-[2px] uppercase font-bold hover:border-ink transition-colors">Cancel</button>}
                    </div>
                  </form>
                )}

                {!showAddrForm && (
                  <button onClick={() => selectedAddr ? setStep(1) : toast.error('Please select an address')} className="mt-6 px-8 py-3 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-gold-light transition-colors">Continue to Payment</button>
                )}
              </>
            )}

            {step === 1 && (
              <>
                <h3 className="font-serif text-lg font-bold mb-5">Payment Method</h3>
                <div className="space-y-3">
                  {PAYMENT_METHODS.map((m) => (
                    <label key={m.id} className={`flex items-center gap-4 p-4 border cursor-pointer transition-colors ${payment === m.id ? 'border-gold bg-cream/50' : 'border-line hover:border-gold/50'}`}>
                      <input type="radio" name="payment" checked={payment === m.id} onChange={() => setPayment(m.id)} className="accent-gold" />
                      <div>
                        <div className="text-sm font-medium">{m.label}{m.online && <span className="ml-2 text-[9px] tracking-[1px] uppercase text-gold">Secure</span>}</div>
                        <div className="text-[11px] text-gray">{m.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
                <div className="flex gap-3 mt-6">
                  <button onClick={() => setStep(0)} className="px-6 py-3 border border-line text-[11px] tracking-[2px] uppercase font-bold hover:border-ink transition-colors">Back</button>
                  <button onClick={() => setStep(2)} className="px-8 py-3 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-gold-light transition-colors">Review Order</button>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <h3 className="font-serif text-lg font-bold mb-5">Order Confirmation</h3>
                <div className="bg-surface p-4 mb-4">
                  <div className="text-[10px] tracking-[2px] uppercase text-gray font-semibold mb-2 flex items-center gap-1.5"><IconMapPin size={12} /> Delivery Address</div>
                  {activeAddr ? (
                    <>
                      <p className="text-sm">{activeAddr.full_name}, {activeAddr.phone}</p>
                      <p className="text-xs text-gray mt-0.5">{activeAddr.line1}{activeAddr.line2 ? `, ${activeAddr.line2}` : ''}, {activeAddr.city}, {activeAddr.state} - {activeAddr.pin_code}</p>
                    </>
                  ) : <p className="text-xs text-maroon-light">No address selected</p>}
                </div>
                <div className="bg-surface p-4 mb-4">
                  <div className="text-[10px] tracking-[2px] uppercase text-gray font-semibold mb-2">Payment</div>
                  <p className="text-sm">{PAYMENT_METHODS.find((m) => m.id === payment)?.label}</p>
                </div>
                <div className="flex gap-3 mt-6">
                  <button onClick={() => setStep(1)} className="px-6 py-3 border border-line text-[11px] tracking-[2px] uppercase font-bold hover:border-ink transition-colors">Back</button>
                  <button onClick={handlePlaceOrder} disabled={placing} className="px-8 py-3 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-gold-light transition-colors disabled:opacity-60">{placing ? 'Placing…' : 'Place Order'}</button>
                </div>
              </>
            )}
          </div>

          {/* Summary */}
          <div className="bg-surface p-6 h-fit">
            <h3 className="font-serif text-lg font-bold mb-4">Order Summary</h3>
            <div className="space-y-3 mb-4">
              {items.map((i) => (
                <div key={i.id} className="flex justify-between text-xs">
                  <span className="text-gray">{i.product_name} × {i.quantity}</span><span className="font-medium">{inr(i.line_total)}</span>
                </div>
              ))}
            </div>
            {cart && (
              <>
                <div className="border-t border-line pt-3 space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray">Subtotal</span><span>{inr(cart.subtotal)}</span></div>
                  {cart.discount > 0 && <div className="flex justify-between text-green-600"><span>Discount</span><span>−{inr(cart.discount)}</span></div>}
                  <div className="flex justify-between"><span className="text-gray">GST (5%)</span><span>{inr(cart.gst)}</span></div>
                  <div className="flex justify-between"><span className="text-gray">Delivery</span><span className={cart.delivery_charge === 0 ? 'text-green-600' : ''}>{cart.delivery_charge === 0 ? 'FREE' : inr(cart.delivery_charge)}</span></div>
                </div>
                <div className="flex justify-between font-bold text-lg mt-3 pt-3 border-t border-line">
                  <span>Total</span><span>{inr(cart.total)}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </section>
    </>
  )
}
