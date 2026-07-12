import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { IconSearch, IconCheck, IconTruck, IconPackage, IconCircleDashed } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import apiClient from '@/services/apiClient'
import { useAuthStore } from '@/store/useAuthStore'
import { toast } from '@/components/ui/Toast'

const inr = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`
const fmtDateTime = (iso) => iso ? new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''

const ICONS = {
  placed: IconCheck,
  confirmed: IconCheck,
  packed: IconPackage,
  dispatched: IconTruck,
  in_transit: IconTruck,
  out_for_delivery: IconTruck,
  delivered: IconCheck,
  failed_attempt: IconCircleDashed,
  returned: IconCircleDashed,
}

export default function OrderTracking() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [orderNumber, setOrderNumber] = useState(params.get('order') || '')
  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(false)
  const [notFound, setNotFound] = useState(false)

  const track = useCallback(async (number) => {
    const q = (number || '').trim()
    if (!q) return
    if (!isAuthenticated) {
      toast.info('Please sign in to track your order')
      navigate('/login')
      return
    }
    setLoading(true); setNotFound(false); setOrder(null)
    try {
      const { data } = await apiClient.get('/orders')
      const match = data.orders.find((o) => o.order_number.toLowerCase() === q.toLowerCase())
      if (!match) { setNotFound(true); setLoading(false); return }
      const detail = await apiClient.get(`/orders/${match.id}`)
      setOrder(detail.data)
    } catch {
      setNotFound(true)
    }
    setLoading(false)
  }, [isAuthenticated, navigate])

  useEffect(() => {
    const q = params.get('order')
    if (q && isAuthenticated) track(q)
  }, [params, isAuthenticated, track])

  return (
    <>
      <PageHeader title="Track Order" crumbs={[{ label: 'Home', to: '/' }, { label: 'Track Order' }]} />
      <section className="px-6 lg:px-12 py-10 max-w-2xl mx-auto">
        <div className="flex gap-2 mb-8">
          <input type="text" value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && track(orderNumber)} placeholder="Enter Order Number (e.g. ANG-2026-12)" className="flex-1 border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" />
          <button onClick={() => track(orderNumber)} className="px-5 py-3 bg-ink text-white flex items-center gap-2 text-[11px] tracking-[1px] uppercase font-bold hover:bg-ink/90 transition-colors">
            <IconSearch size={14} /> Track
          </button>
        </div>

        {loading && <div className="py-12 text-center text-gray text-sm">Fetching your order…</div>}

        {notFound && !loading && (
          <div className="py-12 text-center">
            <p className="text-gray text-sm">No order found with that number under your account.</p>
            <Link to="/account" className="text-[11px] text-gold font-medium hover:underline mt-2 inline-block">View my orders</Link>
          </div>
        )}

        {order && !loading && (
          <div className="border border-line p-6">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-line">
              <div>
                <div className="font-serif text-lg font-bold">Order #{order.order_number}</div>
                <div className="text-xs text-gray mt-0.5">
                  Placed on {fmtDateTime(order.placed_at)} · {order.items.length} item{order.items.length !== 1 ? 's' : ''} · {inr(order.total_amount)}
                </div>
                {order.tracking_number && <div className="text-[11px] text-gray mt-0.5">Courier: {order.courier_name || '—'} · AWB: {order.tracking_number}</div>}
              </div>
              <span className="px-2.5 py-1 text-[10px] tracking-[1px] uppercase font-bold text-gold bg-cream capitalize whitespace-nowrap">{order.status.replace(/_/g, ' ')}</span>
            </div>

            {order.tracking.length === 0 ? (
              <p className="text-sm text-gray text-center py-6">No tracking updates yet.</p>
            ) : (
              <div className="relative pl-8">
                <div className="absolute left-[15px] top-2 bottom-2 w-[2px] bg-line" />
                {order.tracking.map((t, i) => {
                  const Icon = ICONS[t.status_type] || IconCheck
                  const isLatest = i === order.tracking.length - 1
                  return (
                    <div key={t.id} className="relative pb-7 last:pb-0">
                      <div className={`absolute -left-8 w-8 h-8 rounded-full flex items-center justify-center ${isLatest ? 'bg-gold text-ink' : 'bg-ink text-gold'}`}>
                        <Icon size={14} />
                      </div>
                      <div className="ml-4">
                        <div className="font-semibold text-sm">{t.status_label}</div>
                        <div className="text-[11px] text-gray">{fmtDateTime(t.event_time)}</div>
                        {t.description && <div className="text-xs text-gray mt-0.5">{t.description}</div>}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {order.expected_delivery && order.status !== 'delivered' && (
              <div className="mt-6 pt-4 border-t border-line text-xs text-gray">
                Expected delivery by <span className="font-semibold text-ink">{new Date(order.expected_delivery).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  )
}
