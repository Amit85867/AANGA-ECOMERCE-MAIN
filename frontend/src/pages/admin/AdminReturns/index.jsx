import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowBackUp } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import {
  RETURN_STATUS_TONE, formatDate, humanize, inputCls, inr, notifyError,
} from '@/components/admin/helpers'

// The steps a return moves through before it is settled.
const PROGRESS = ['requested', 'approved', 'pickup_scheduled', 'picked_up', 'inspected']
const RESOLUTIONS = ['refund', 'exchange', 'store_credit']
const CLOSED = new Set(['resolved', 'rejected'])

function ReturnCard({ ret, onChanged }) {
  const closed = CLOSED.has(ret.status)
  const [resolution, setResolution] = useState(ret.resolution_type || 'refund')
  const [amount, setAmount] = useState(ret.refund_amount ?? ret.item_total)
  const [restock, setRestock] = useState(ret.reason !== 'damaged')
  const [busy, setBusy] = useState(false)

  const send = async (payload, success) => {
    setBusy(true)
    try {
      const { data } = await adminApi.patch(`/admin/returns/${ret.id}`, payload)
      toast.success(typeof success === 'function' ? success(data) : success)
      onChanged()
    } catch (err) {
      notifyError(err, 'Could not update this return.')
    }
    setBusy(false)
  }

  const resolve = async () => {
    const refunding = resolution === 'refund'
    const value = Number(amount)
    if (refunding && !(value > 0 && value <= ret.item_total)) {
      toast.error(`Refund must be between ₹1 and ${inr(ret.item_total)}.`)
      return
    }

    // Say exactly what is about to happen: this is the step that moves money.
    const moneyLine = !refunding
      ? `The return is closed as ${humanize(resolution).toLowerCase()}. No payment is refunded.`
      : ret.prepaid
        ? `${inr(value)} is refunded to the customer through Razorpay straight away. This cannot be undone.`
        : `This was a cash-on-delivery order, so nothing can be refunded online. Pay ${inr(value)} to the customer yourself, then confirm.`
    const sure = await confirm({
      title: `Resolve return for ${ret.order_number}?`,
      message: `${moneyLine}${restock ? ` ${ret.quantity} ${ret.quantity === 1 ? 'unit goes' : 'units go'} back into stock.` : ''}`,
      confirmLabel: refunding && ret.prepaid ? `Refund ${inr(value)}` : 'Resolve return',
      danger: refunding && ret.prepaid,
    })
    if (!sure) return

    send(
      { status: 'resolved', resolution_type: resolution, restock, ...(refunding ? { refund_amount: value } : {}) },
      (data) =>
        data.refund_method === 'gateway' ? `Refunded ${inr(data.refund_amount)} through Razorpay.`
          : data.refund_method === 'manual' ? `Resolved. Remember to pay ${inr(data.refund_amount)} to the customer.`
            : 'Return resolved.',
    )
  }

  const reject = async () => {
    const sure = await confirm({
      title: 'Reject this return?',
      message: 'The customer keeps the item and receives no refund. A rejected return cannot be reopened.',
      confirmLabel: 'Reject return',
      danger: true,
    })
    if (sure) send({ status: 'rejected' }, 'Return rejected.')
  }

  return (
    <li className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium text-gray-900">{ret.product_name}</div>
          <div className="text-sm text-gray-600">
            {ret.variant} · qty {ret.quantity} · {inr(ret.item_total)}
          </div>
          <div className="mt-1 text-sm text-gray-500">
            <Link to={`/admin/orders/${ret.order_id}`} className="font-medium text-gray-900 hover:underline">
              {ret.order_number}
            </Link>{' '}
            · {ret.customer_name}{ret.customer_email ? ` (${ret.customer_email})` : ''}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge tone={RETURN_STATUS_TONE[ret.status]}>{humanize(ret.status)}</Badge>
          <span className="text-xs text-gray-500">Requested {formatDate(ret.requested_at)}</span>
        </div>
      </div>

      <dl className="mt-4 grid gap-x-6 gap-y-2 border-t border-gray-100 pt-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-gray-500">Reason</dt>
          <dd className="text-gray-900">{humanize(ret.reason)}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Payment</dt>
          <dd className="text-gray-900">{ret.prepaid ? 'Paid online — refundable through Razorpay' : 'Cash on delivery — refund is paid manually'}</dd>
        </div>
        {ret.description && (
          <div className="sm:col-span-2">
            <dt className="text-xs text-gray-500">Customer’s note</dt>
            <dd className="whitespace-pre-line text-gray-900">{ret.description}</dd>
          </div>
        )}
      </dl>

      {closed ? (
        <p className="mt-4 rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-700">
          {ret.status === 'resolved'
            ? `Resolved ${formatDate(ret.resolved_at)} as ${humanize(ret.resolution_type).toLowerCase()}${ret.refund_amount ? ` — ${inr(ret.refund_amount)} refunded` : ''}.`
            : `Rejected ${formatDate(ret.resolved_at)}.`}
        </p>
      ) : (
        <div className="mt-4 space-y-4 border-t border-gray-100 pt-4">
          <label className="flex items-center gap-3 text-sm">
            <span className="shrink-0 text-gray-600">Progress</span>
            <select
              value={ret.status} disabled={busy}
              onChange={(e) => send({ status: e.target.value }, `Marked ${humanize(e.target.value).toLowerCase()}.`)}
              className={`${inputCls} max-w-xs py-1.5`}
            >
              {PROGRESS.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
            </select>
          </label>

          <fieldset className="rounded-lg bg-gray-50 p-4" disabled={busy}>
            <legend className="px-1 text-sm font-medium text-gray-900">Settle this return</legend>
            <div className="flex flex-wrap items-end gap-4">
              <label className="flex flex-col gap-1 text-xs text-gray-600">
                Resolution
                <select value={resolution} onChange={(e) => setResolution(e.target.value)} className={`${inputCls} w-auto py-1.5`}>
                  {RESOLUTIONS.map((r) => <option key={r} value={r}>{humanize(r)}</option>)}
                </select>
              </label>
              {resolution === 'refund' && (
                <label className="flex flex-col gap-1 text-xs text-gray-600">
                  Refund amount (max {inr(ret.item_total)})
                  <input
                    type="number" min="1" max={ret.item_total} step="0.01" value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className={`${inputCls} w-36 py-1.5`}
                  />
                </label>
              )}
              <label className="flex items-center gap-2 pb-2 text-sm text-gray-700">
                <input type="checkbox" checked={restock} onChange={(e) => setRestock(e.target.checked)} className="rounded" />
                Return item to stock
              </label>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button" onClick={resolve}
                className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black disabled:opacity-60"
              >
                {busy ? 'Working…' : 'Resolve return'}
              </button>
              <button
                type="button" onClick={reject}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
              >
                Reject
              </button>
            </div>
          </fieldset>
        </div>
      )}
    </li>
  )
}

export default function AdminReturns() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('open')
  const [sort, setSort] = useState('requested_at:asc')

  const [sortBy, dir] = sort.split(':')
  const list = useAdminList('/admin/returns', 'returns', { q, status, sort: sortBy, dir })

  return (
    <div>
      <PageHeading title="Returns" subtitle="Review return requests, refund customers and put stock back on sale." />

      <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Order number, customer name or email" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status" className={`${inputCls} w-auto`}>
          <option value="open">Needs action</option>
          <option value="">All returns</option>
          {[...PROGRESS, 'resolved', 'rejected'].map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className={`${inputCls} w-auto`}>
          <option value="requested_at:asc">Oldest first</option>
          <option value="requested_at:desc">Newest first</option>
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={Boolean(q) || (status !== 'open' && status !== '')}
        skeleton={<TableSkeleton rows={4} columns={4} />}
        emptyIcon={IconArrowBackUp}
        emptyTitle={status === 'open' ? 'No returns waiting for you' : 'No returns yet'}
        emptyHint={status === 'open' ? 'New return requests will appear here.' : 'Customers can request a return within 7 days of delivery.'}
      >
        <ul className={`space-y-3 ${list.loading ? 'opacity-60' : ''}`}>
          {list.rows.map((ret) => <ReturnCard key={`${ret.id}-${ret.status}`} ret={ret} onChanged={list.reload} />)}
        </ul>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="returns" />
      </DataState>
    </div>
  )
}
