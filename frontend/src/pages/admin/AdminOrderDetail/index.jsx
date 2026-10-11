import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { inr, notifyError } from '@/components/admin/helpers'
import { IconArrowLeft, IconTruckDelivery, IconRefresh } from '@tabler/icons-react'

const ORDER_STATUSES = ['pending', 'confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled']
const TRACKING_TYPES = ['placed', 'confirmed', 'packed', 'dispatched', 'in_transit', 'out_for_delivery', 'delivered', 'failed_attempt', 'returned']

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  packed: 'bg-indigo-100 text-indigo-700',
  shipped: 'bg-purple-100 text-purple-700',
  out_for_delivery: 'bg-cyan-100 text-cyan-700',
  delivered: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

export default function AdminOrderDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(true)
  const [newStatus, setNewStatus] = useState('')
  const [tracking, setTracking] = useState({ status_label: '', description: '', status_type: 'confirmed', courier_name: '', tracking_number: '' })
  const [shipping, setShipping] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  const [savingStatus, setSavingStatus] = useState(false)
  const [savingEvent, setSavingEvent] = useState(false)

  const reload = async () => {
    const r = await adminApi.get(`/admin/orders/${id}`)
    setOrder(r.data)
    setNewStatus(r.data.status)
  }

  const load = () => {
    setLoading(true)
    setError(null)
    reload()
      .catch((err) =>
        setError(
          err.response?.status === 404
            ? 'This order does not exist.'
            : err.response?.data?.error || 'Could not load this order.',
        ),
      )
      .finally(() => setLoading(false))
  }

  const shipViaShiprocket = async () => {
    if (!(await confirm({ title: 'Book this shipment?', message: 'A Shiprocket shipment is created and an AWB assigned. This cannot be undone from here.', confirmLabel: 'Book shipment' }))) return
    setShipping(true)
    try {
      const { data } = await adminApi.post(`/admin/orders/${id}/ship`)
      toast.success(`Shipment booked with ${data.courier_name || 'courier'} — AWB ${data.tracking_number}`)
      await reload()
    } catch (err) {
      notifyError(err, 'Could not create shipment')
    }
    setShipping(false)
  }

  const syncTracking = async () => {
    setSyncing(true)
    try {
      const { data } = await adminApi.post(`/admin/orders/${id}/sync-tracking`)
      toast.success(data.message || 'Tracking synced')
      await reload()
    } catch (err) {
      notifyError(err, 'Could not sync tracking')
    }
    setSyncing(false)
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [id])

  const updateStatus = async () => {
    if (savingStatus || newStatus === order.status) return

    // Cancelling restores stock and, for a prepaid order, sends the money
    // back — say so before it happens.
    if (newStatus === 'cancelled') {
      const prepaid = order.payment_status === 'paid'
      const sure = await confirm({
        title: `Cancel order ${order.order_number}?`,
        message: prepaid
          ? `${inr(order.total_amount)} is refunded to the customer through Razorpay and the items go back into stock. A cancelled order cannot be reopened.`
          : 'The items go back into stock. A cancelled order cannot be reopened.',
        confirmLabel: prepaid ? `Cancel and refund ${inr(order.total_amount)}` : 'Cancel order',
        cancelLabel: 'Keep order',
        danger: true,
      })
      if (!sure) {
        setNewStatus(order.status)
        return
      }
    }

    setSavingStatus(true)
    try {
      const { data } = await adminApi.patch(`/admin/orders/${id}/status`, { status: newStatus })
      if (data.refunded === false) {
        toast.error('Order cancelled, but the refund did not go through. Refund it in the Razorpay Dashboard.')
      } else {
        toast.success(data.refunded ? 'Order cancelled and payment refunded.' : 'Order status updated.')
      }
      await reload()
    } catch (err) {
      notifyError(err, 'Could not update the status.')
      setNewStatus(order.status)
    }
    setSavingStatus(false)
  }

  const addTracking = async (e) => {
    e.preventDefault()
    if (savingEvent) return
    setSavingEvent(true)
    try {
      await adminApi.post(`/admin/orders/${id}/tracking`, tracking)
      toast.success('Tracking event added.')
      await reload()
      setTracking({ status_label: '', description: '', status_type: 'confirmed', courier_name: '', tracking_number: '' })
    } catch (err) {
      notifyError(err, 'Could not add the tracking event.')
    }
    setSavingEvent(false)
  }

  if (loading) return <TableSkeleton rows={6} columns={4} />
  if (error || !order) return <ErrorState message={error || 'This order does not exist.'} onRetry={load} />

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-gold'

  return (
    <div>
      <button onClick={() => navigate('/admin/orders')} className="mb-4 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
        <IconArrowLeft size={16} /> Back to orders
      </button>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-semibold text-gray-900">{order.order_number}</h1>
        <span className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${STATUS_COLORS[order.status] || 'bg-gray-100 text-gray-600'}`}>
          {order.status.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Items</h3>
            <div className="space-y-3">
              {order.items.map((item) => (
                <div key={item.id} className="flex gap-4 rounded-lg border border-gray-100 p-3">
                  {item.image_url ? (
                    <img src={item.image_url} alt="" className="h-16 w-16 rounded-lg object-cover" />
                  ) : (
                    <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-gray-100 text-xs text-gray-400">N/A</div>
                  )}
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{item.product_name}</div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>{item.size}</span>
                      <span className="inline-block h-3 w-3 rounded-full border" style={{ background: item.color_hex }} />
                      <span>{item.color_name}</span>
                    </div>
                    <div className="mt-1 text-sm text-gray-700">
                      {inr(item.unit_price)} x {item.quantity} = {inr(item.total_price)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Update Status</h3>
            <div className="flex gap-2">
              <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)} className={inputCls}>
                {ORDER_STATUSES
                  .filter((s) => s === order.status || (order.allowed_statuses || ORDER_STATUSES).includes(s))
                  .map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
              </select>
              <button onClick={updateStatus} disabled={savingStatus || newStatus === order.status} className="disabled:cursor-not-allowed disabled:opacity-50 rounded-lg bg-gray-900 px-4 text-sm text-white hover:bg-gray-800">Update</button>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 font-medium text-gray-900">Tracking Events</h3>
            {order.tracking.length > 0 && (
              <div className="mb-4 space-y-2">
                {order.tracking.map((t) => (
                  <div key={t.id} className="flex items-start gap-3 rounded-lg border border-gray-50 p-3">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-gold" />
                    <div>
                      <div className="text-sm font-medium text-gray-900">{t.status_label}</div>
                      {t.description && <div className="text-xs text-gray-500">{t.description}</div>}
                      <div className="text-xs text-gray-400">{new Date(t.event_time).toLocaleString('en-IN')}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <form onSubmit={addTracking} className="grid gap-3 border-t border-gray-100 pt-4 sm:grid-cols-2">
              <input value={tracking.status_label} onChange={(e) => setTracking((t) => ({ ...t, status_label: e.target.value }))} placeholder="Status label *" required className={inputCls} />
              <select value={tracking.status_type} onChange={(e) => setTracking((t) => ({ ...t, status_type: e.target.value }))} className={inputCls}>
                {TRACKING_TYPES.map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
              </select>
              <input value={tracking.description} onChange={(e) => setTracking((t) => ({ ...t, description: e.target.value }))} placeholder="Description" className={inputCls} />
              <input value={tracking.courier_name} onChange={(e) => setTracking((t) => ({ ...t, courier_name: e.target.value }))} placeholder="Courier name" className={inputCls} />
              <input value={tracking.tracking_number} onChange={(e) => setTracking((t) => ({ ...t, tracking_number: e.target.value }))} placeholder="Tracking number" className={inputCls} />
              <button type="submit" disabled={savingEvent} className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white hover:bg-gray-800 disabled:opacity-60">{savingEvent ? 'Adding…' : 'Add Event'}</button>
            </form>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-3 font-medium text-gray-900">Customer</h3>
            <div className="space-y-1 text-sm">
              <div className="text-gray-900">{order.customer.full_name}</div>
              <div className="text-gray-500">{order.customer.email}</div>
              <div className="text-gray-500">{order.customer.phone}</div>
            </div>
          </div>

          {order.address && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="mb-3 font-medium text-gray-900">Delivery Address</h3>
              <div className="space-y-1 text-sm text-gray-600">
                <div>{order.address.full_name}</div>
                <div>{order.address.line1}</div>
                {order.address.line2 && <div>{order.address.line2}</div>}
                <div>{order.address.city}, {order.address.state} {order.address.pin_code}</div>
                <div>{order.address.phone}</div>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-3 font-medium text-gray-900">Payment</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Method</span><span className="capitalize text-gray-900">{order.payment_method.replace(/_/g, ' ')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Status</span><span className="capitalize text-gray-900">{order.payment_status}</span></div>
              {order.payment_ref && <div className="flex justify-between"><span className="text-gray-500">Ref</span><span className="text-gray-900">{order.payment_ref}</span></div>}
              <hr className="my-2" />
              <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>{inr(order.subtotal)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Discount</span><span className="text-green-600">-{inr(order.discount_amount)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">GST</span><span>{inr(order.gst_amount)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Delivery</span><span>{inr(order.delivery_charge)}</span></div>
              <hr className="my-2" />
              <div className="flex justify-between font-semibold"><span>Total</span><span>{inr(order.total_amount)}</span></div>
            </div>
          </div>

          {/* Shiprocket delivery */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-3 flex items-center gap-2 font-medium text-gray-900"><IconTruckDelivery size={18} /> Delivery</h3>
            {order.tracking_number ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Courier</span><span className="text-gray-900">{order.courier_name || '—'}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">AWB</span><span className="font-mono text-gray-900">{order.tracking_number}</span></div>
                <button onClick={syncTracking} disabled={syncing} className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60">
                  <IconRefresh size={15} /> {syncing ? 'Syncing…' : 'Sync tracking'}
                </button>
              </div>
            ) : (
              <>
                <p className="mb-3 text-xs text-gray-500">Create a Shiprocket shipment to auto-assign a courier and AWB, then push updates to the customer's tracking page.</p>
                <button onClick={shipViaShiprocket} disabled={shipping} className="flex w-full items-center justify-center gap-2 rounded-lg bg-gold py-2.5 text-sm font-medium text-white hover:bg-gold-dark disabled:opacity-60">
                  <IconTruckDelivery size={16} /> {shipping ? 'Creating…' : 'Ship via Shiprocket'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
