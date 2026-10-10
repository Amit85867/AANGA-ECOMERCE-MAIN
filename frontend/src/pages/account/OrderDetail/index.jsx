import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { IconArrowLeft, IconCircleCheckFilled, IconCircle } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/toastStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { Select, Textarea } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Overlay'
import AddressBlock from '@/components/account/AddressBlock'
import { ErrorState, Skeleton, StatusBadge } from '@/components/ui/Display'
import { RETURN_REASONS, formatDate, formatDateTime, humanize, inr } from '@/utils/format'
import Seo from '@/components/Seo'

// The API is the authority on both; these only decide whether to offer the button.
const CANCELLABLE = ['pending', 'confirmed']
const RETURNABLE = ['delivered', 'return_requested']

const PAYMENT_LABEL = {
  cod: 'Cash on delivery', upi: 'UPI', credit_card: 'Card', debit_card: 'Card',
  net_banking: 'Net banking', wallet: 'Wallet', emi: 'EMI',
}

function CancelDialog({ order, open, onClose, onCancelled }) {
  const [working, setWorking] = useState(false)
  const prepaid = order.payment_status === 'paid'

  const cancel = async () => {
    setWorking(true)
    try {
      const { data } = await apiClient.post(`/orders/${order.id}/cancel`)
      // The API says plainly whether the refund went through.
      if (data.refunded === false) toast.info(data.message)
      else toast.success(data.message || 'Order cancelled')
      onCancelled()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.error || 'We could not cancel this order.')
    }
    setWorking(false)
  }

  return (
    <Modal
      open={open} onClose={onClose} title="Cancel this order?" size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={working} data-autofocus>Keep order</Button>
          <Button variant="danger" onClick={cancel} disabled={working}>
            {working ? 'Cancelling…' : 'Cancel order'}
          </Button>
        </>
      }
    >
      <p className="text-sm leading-relaxed text-muted">
        Order <span className="font-medium text-fg">{order.order_number}</span> will be cancelled and cannot be reinstated.
        {prepaid
          ? ` Your payment of ${inr(order.total_amount)} will be refunded to the original payment method, usually within 5–7 working days.`
          : ' Nothing has been charged, so there is nothing to refund.'}
      </p>
    </Modal>
  )
}

function ReturnDialog({ order, open, onClose, onRequested }) {
  const [eligibility, setEligibility] = useState(null)
  const [failed, setFailed] = useState(false)
  const [itemId, setItemId] = useState(null)
  const [reason, setReason] = useState('size_issue')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [working, setWorking] = useState(false)

  useEffect(() => {
    if (!open) return
    setEligibility(null)
    setFailed(false)
    setError('')
    apiClient.get(`/returns/eligibility/${order.id}`)
      .then(({ data }) => {
        setEligibility(data)
        setItemId(data.items.find((i) => i.returnable)?.order_item_id ?? null)
      })
      .catch(() => setFailed(true))
  }, [open, order.id])

  const submit = async (e) => {
    e.preventDefault()
    if (!itemId || working) return
    setWorking(true)
    setError('')
    try {
      await apiClient.post('/returns', {
        order_item_id: itemId, reason, ...(description.trim() ? { description: description.trim() } : {}),
      })
      toast.success('Return requested. We will be in touch about the pickup.')
      onRequested()
      onClose()
    } catch (err) {
      setError(err.response?.data?.error || 'We could not submit your return request.')
    }
    setWorking(false)
  }

  const anyReturnable = eligibility?.items.some((i) => i.returnable)

  return (
    <Modal open={open} onClose={onClose} title="Request a return">
      {failed ? (
        <ErrorState message="We could not load the return options." />
      ) : !eligibility ? (
        <div className="space-y-3"><Skeleton className="h-16" /><Skeleton className="h-16" /></div>
      ) : !anyReturnable ? (
        <p className="text-sm leading-relaxed text-muted">
          Nothing in this order can be returned right now.
          {!eligibility.window_open && ` Returns are accepted within ${eligibility.window_days} days of delivery, and that window has closed.`}
        </p>
      ) : (
        <form onSubmit={submit} className="space-y-5" noValidate>
          <p className="text-sm text-muted">
            Returns are accepted within {eligibility.window_days} days of delivery. Choose the item you want to send back.
          </p>
          <fieldset className="space-y-2">
            <legend className="mb-1.5 text-xs font-medium uppercase tracking-[0.05em] text-muted">Item</legend>
            {eligibility.items.map((i) => (
              <label
                key={i.order_item_id}
                className={`flex gap-3 rounded-card border p-3 text-sm ${
                  !i.returnable ? 'cursor-not-allowed border-hairline/60 opacity-60'
                    : itemId === i.order_item_id ? 'cursor-pointer border-primary ring-1 ring-primary'
                      : 'cursor-pointer border-hairline hover:border-subtle'
                }`}
              >
                <input
                  type="radio" name="return-item" className="mt-0.5 h-4 w-4 accent-black"
                  disabled={!i.returnable} checked={itemId === i.order_item_id}
                  onChange={() => setItemId(i.order_item_id)}
                />
                <span>
                  <span className="block font-medium text-fg">{i.product_name}</span>
                  <span className="block text-xs text-muted">
                    {[i.size && `Size ${i.size}`, i.color_name, `Qty ${i.quantity}`].filter(Boolean).join(' · ')}
                  </span>
                  {i.reason_unavailable && <span className="mt-0.5 block text-xs text-muted">{i.reason_unavailable}</span>}
                </span>
              </label>
            ))}
          </fieldset>
          <Select label="Reason" name="return-reason" value={reason} onChange={(e) => setReason(e.target.value)}>
            {RETURN_REASONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
          <Textarea
            label="Anything else we should know? (optional)" name="return-notes" rows={3} maxLength={2000}
            value={description} onChange={(e) => setDescription(e.target.value)}
          />
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={onClose}>Not now</Button>
            <Button type="submit" disabled={working || !itemId}>{working ? 'Submitting…' : 'Request return'}</Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default function OrderDetail() {
  const { id } = useParams()
  const [order, setOrder] = useState(null)
  const [error, setError] = useState(null)
  const [dialog, setDialog] = useState(null)   // 'cancel' | 'return' | null

  const load = useCallback(() => {
    setError(null)
    return apiClient.get(`/orders/${id}`)
      .then(({ data }) => setOrder(data))
      .catch((err) => setError(err.response?.status === 404 ? 'not-found' : 'failed'))
  }, [id])

  useEffect(() => { load() }, [load])

  const back = (
    <Link to="/account/orders" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
      <IconArrowLeft size={16} aria-hidden="true" /> All orders
    </Link>
  )

  if (error) {
    return (
      <>
        {back}
        <ErrorState
          className="mt-6"
          message={error === 'not-found' ? 'We could not find that order.' : 'We could not load this order.'}
          onRetry={error === 'failed' ? load : undefined}
        />
      </>
    )
  }
  if (!order) return <><Skeleton className="h-8 w-48" /><Skeleton className="mt-6 h-72" /></>

  const canCancel = CANCELLABLE.includes(order.status)
  const canReturn = RETURNABLE.includes(order.status)

  return (
    <>
      <Seo title={`Order ${order.order_number}`} noindex />
      {back}

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="display text-2xl sm:text-3xl text-fg">{order.order_number}</h1>
            <StatusBadge status={order.status} />
          </div>
          <p className="mt-2 text-sm text-muted">
            Placed {formatDateTime(order.placed_at)}
            {order.expected_delivery && !['delivered', 'cancelled', 'return_requested', 'returned'].includes(order.status) && (
              <> · Expected by <span className="font-medium text-fg">{formatDate(order.expected_delivery)}</span></>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canReturn && <Button variant="secondary" onClick={() => setDialog('return')}>Return an item</Button>}
          {canCancel && <Button variant="secondary" onClick={() => setDialog('cancel')}>Cancel order</Button>}
        </div>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Items</h2>
            <ul className="divide-y divide-hairline/60">
              {order.items.map((item) => (
                <li key={item.id} className="flex gap-4 py-4">
                  <Link to={`/product/${item.product_slug}`} className="h-24 w-[4.5rem] shrink-0 overflow-hidden rounded-lg bg-fill">
                    {item.image_url && <img src={item.image_url} alt="" width="144" height="192" loading="lazy" className="h-full w-full object-cover" />}
                  </Link>
                  <div className="min-w-0 flex-1">
                    <Link to={`/product/${item.product_slug}`} className="text-sm font-medium text-fg hover:underline underline-offset-2">
                      {item.product_name}
                    </Link>
                    <p className="mt-1 text-xs text-muted">
                      {[item.size && `Size ${item.size}`, item.color_name, `Qty ${item.quantity}`].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  <p className="text-sm font-medium tabular-nums text-fg">{inr(item.total_price)}</p>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-6">
            <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Tracking</h2>
            {order.tracking_number && (
              <p className="mb-4 text-sm text-muted">
                {order.courier_name || 'Courier'} · AWB <span className="font-medium text-fg tabular-nums">{order.tracking_number}</span>
              </p>
            )}
            {order.tracking.length === 0 ? (
              <p className="text-sm text-muted">Updates will appear here as your order moves.</p>
            ) : (
              <ol className="space-y-5">
                {[...order.tracking].reverse().map((event, i) => (
                  <li key={event.id} className="flex gap-3">
                    {i === 0
                      ? <IconCircleCheckFilled size={20} className="mt-0.5 shrink-0 text-fg" aria-hidden="true" />
                      : <IconCircle size={20} className="mt-0.5 shrink-0 text-hairline" aria-hidden="true" />}
                    <div>
                      <p className={`text-sm ${i === 0 ? 'font-semibold text-fg' : 'text-muted'}`}>{event.status_label}</p>
                      {event.description && <p className="text-sm text-muted">{event.description}</p>}
                      <p className="mt-0.5 text-xs text-muted">{formatDateTime(event.event_time)}</p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Payment</h2>
            <dl className="space-y-2.5 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-muted">Subtotal</dt><dd className="tabular-nums text-fg">{inr(order.subtotal)}</dd></div>
              {order.discount_amount > 0 && (
                <div className="flex justify-between gap-4"><dt className="text-muted">Discount</dt><dd className="tabular-nums text-fg">−{inr(order.discount_amount)}</dd></div>
              )}
              <div className="flex justify-between gap-4"><dt className="text-muted">GST</dt><dd className="tabular-nums text-fg">{inr(order.gst_amount)}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted">Delivery</dt><dd className="tabular-nums text-fg">{order.delivery_charge === 0 ? 'Free' : inr(order.delivery_charge)}</dd></div>
              <div className="flex justify-between gap-4 border-t border-hairline/60 pt-3 font-semibold">
                <dt className="text-fg">Total</dt><dd className="tabular-nums text-fg">{inr(order.total_amount)}</dd>
              </div>
            </dl>
            <p className="mt-4 text-sm text-muted">
              {PAYMENT_LABEL[order.payment_method] || humanize(order.payment_method)} · {humanize(order.payment_status)}
            </p>
          </Card>

          <Card className="p-6">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Delivered to</h2>
            <AddressBlock address={order.address} />
          </Card>
        </div>
      </div>

      <CancelDialog order={order} open={dialog === 'cancel'} onClose={() => setDialog(null)} onCancelled={load} />
      <ReturnDialog order={order} open={dialog === 'return'} onClose={() => setDialog(null)} onRequested={load} />
    </>
  )
}
