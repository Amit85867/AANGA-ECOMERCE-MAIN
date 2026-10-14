import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconShoppingCart } from '@tabler/icons-react'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import {
  ORDER_STATUS_TONE, countOf, formatDateTime, humanize, inputCls, inr,
} from '@/components/admin/helpers'

const STATUSES = [
  'pending', 'confirmed', 'packed', 'shipped', 'out_for_delivery',
  'delivered', 'cancelled', 'return_requested', 'returned',
]
const PAYMENT_TONE = { paid: 'green', pending: 'amber', failed: 'red', refunded: 'gray' }

const SORTS = [
  ['placed_at:desc', 'Newest first'],
  ['placed_at:asc', 'Oldest first'],
  ['total_amount:desc', 'Highest value'],
  ['total_amount:asc', 'Lowest value'],
]

export default function AdminOrders() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [paymentStatus, setPaymentStatus] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [sort, setSort] = useState('placed_at:desc')

  const [sortBy, dir] = sort.split(':')
  const list = useAdminList('/admin/orders', 'orders', {
    q, status, payment_status: paymentStatus, from, to, sort: sortBy, dir,
  })
  const filtered = Boolean(q || status || paymentStatus || from || to)

  return (
    <div>
      <PageHeading title="Orders" subtitle={`${countOf(list.total, 'orders')} found`} />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Order number, customer name, email or phone" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Order status" className={`${inputCls} w-auto`}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
        </select>
        <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)} aria-label="Payment status" className={`${inputCls} w-auto`}>
          <option value="">Any payment</option>
          {Object.keys(PAYMENT_TONE).map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
        </select>
        <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} aria-label="Placed from" className={`${inputCls} w-auto`} />
        <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} aria-label="Placed to" className={`${inputCls} w-auto`} />
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className={`${inputCls} w-auto`}>
          {SORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={filtered}
        skeleton={<TableSkeleton rows={8} columns={6} />}
        emptyIcon={IconShoppingCart}
        emptyTitle="No orders yet"
        emptyHint="Orders appear here as soon as a customer checks out."
      >
        <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white ${list.loading ? 'opacity-60' : ''}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="px-6 py-3 font-medium">Order</th>
                <th className="px-6 py-3 font-medium">Customer</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Payment</th>
                <th className="px-6 py-3 text-right font-medium">Total</th>
                <th className="px-6 py-3 font-medium">Placed</th>
              </tr>
            </thead>
            <tbody>
              {list.rows.map((o) => (
                <tr key={o.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <Link to={`/admin/orders/${o.id}`} className="font-medium text-gray-900 hover:underline">
                      {o.order_number}
                    </Link>
                    <div className="text-xs text-gray-500">{o.item_count} item{o.item_count === 1 ? '' : 's'}</div>
                  </td>
                  <td className="px-6 py-3">
                    <div className="text-gray-900">{o.customer_name}</div>
                    <div className="text-xs text-gray-500">{o.customer_email}</div>
                  </td>
                  <td className="px-6 py-3">
                    <Badge tone={ORDER_STATUS_TONE[o.status]}>{humanize(o.status)}</Badge>
                  </td>
                  <td className="px-6 py-3">
                    <Badge tone={PAYMENT_TONE[o.payment_status]}>{humanize(o.payment_status)}</Badge>
                    <div className="mt-0.5 text-xs uppercase text-gray-400">{humanize(o.payment_method)}</div>
                  </td>
                  <td className="px-6 py-3 text-right tabular-nums text-gray-900">{inr(o.total_amount)}</td>
                  <td className="whitespace-nowrap px-6 py-3 text-gray-500">{formatDateTime(o.placed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="orders" />
      </DataState>
    </div>
  )
}
