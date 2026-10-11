import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminStore } from '@/store/useAdminStore'
import {
  IconAlertTriangle, IconArrowBackUp, IconBuildingStore, IconCurrencyRupee,
  IconMail, IconPackageOff, IconRefresh, IconShoppingCart, IconTruckDelivery, IconUsers,
} from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { CardSkeleton, ErrorState } from '@/components/admin/DataState'
import { Badge, PageHeading } from '@/components/admin/controls'
import { ORDER_STATUS_TONE, formatDateTime, humanize, inputCls, inr } from '@/components/admin/helpers'

const isoDay = (date) => {
  // Local calendar day, not the UTC one toISOString() would give after 6:30 pm IST.
  const d = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return d.toISOString().slice(0, 10)
}

const PRESETS = [
  { id: 'today', label: 'Today', days: 1 },
  { id: '7d', label: '7 days', days: 7 },
  { id: '30d', label: '30 days', days: 30 },
  { id: '90d', label: '90 days', days: 90 },
]

const rangeFor = (days) => {
  const to = new Date()
  const from = new Date()
  from.setDate(to.getDate() - (days - 1))
  return { from: isoDay(from), to: isoDay(to) }
}

function Kpi({ icon: Icon, label, value, sub, tone = 'bg-gray-900' }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg p-2 ${tone}`}>
          <Icon size={18} stroke={1.75} className="text-white" />
        </div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <div className="mt-3 text-2xl font-semibold tabular-nums text-gray-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-gray-500">{sub}</div>}
    </div>
  )
}

/* Work that is waiting on someone. Zero is shown quietly; anything else links to the queue. */
function Todo({ icon: Icon, label, count, to }) {
  const waiting = count > 0
  return (
    <Link
      to={to}
      className={`flex items-center gap-3 rounded-xl border p-4 transition-colors ${
        waiting ? 'border-amber-200 bg-amber-50 hover:bg-amber-100' : 'border-gray-200 bg-white hover:bg-gray-50'
      }`}
    >
      <Icon size={20} stroke={1.5} className={waiting ? 'text-amber-600' : 'text-gray-400'} />
      <span className="flex-1 text-sm text-gray-700">{label}</span>
      <span className={`text-lg font-semibold tabular-nums ${waiting ? 'text-amber-800' : 'text-gray-400'}`}>
        {count}
      </span>
    </Link>
  )
}

function RevenueChart({ series }) {
  const max = Math.max(...series.map((p) => p.revenue), 1)
  // Label roughly six points along the axis whatever the range length.
  const step = Math.max(1, Math.ceil(series.length / 6))

  return (
    <div>
      <div className="flex h-44 items-end gap-px" role="img" aria-label="Revenue per day">
        {series.map((point) => (
          <div key={point.date} className="group relative flex h-full flex-1 items-end">
            <div
              className="w-full rounded-t bg-gold/80 transition-colors group-hover:bg-gold"
              style={{ height: `${Math.max((point.revenue / max) * 100, point.revenue > 0 ? 2 : 0)}%` }}
            />
            <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-gray-900 px-2.5 py-1.5 text-xs text-white shadow-lg group-hover:block">
              <div className="font-medium">{inr(point.revenue)}</div>
              <div className="text-white/70">
                {new Date(point.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })} ·{' '}
                {point.orders} order{point.orders === 1 ? '' : 's'}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-px border-t border-gray-100 pt-2 text-[11px] text-gray-400">
        {series.map((point, i) => (
          <div key={point.date} className="flex-1 overflow-visible whitespace-nowrap text-center">
            {i % step === 0
              ? new Date(point.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
              : ''}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  // A tile is a shortcut to a screen: no tile for a screen this role cannot open.
  const areas = useAdminStore((s) => s.admin?.areas) || []
  const can = (area) => areas.includes(area)
  const [preset, setPreset] = useState('30d')
  const [range, setRange] = useState(() => rangeFor(30))
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    adminApi
      .get('/admin/dashboard/overview', { params: range })
      .then((r) => setData(r.data))
      .catch((err) => setError(err.response?.data?.error || 'Could not load the dashboard.'))
      .finally(() => setLoading(false))
  }, [range])

  useEffect(() => { load() }, [load])

  const choosePreset = (p) => {
    setPreset(p.id)
    setRange(rangeFor(p.days))
  }

  const setCustom = (key, value) => {
    if (!value) return
    setPreset('custom')
    setRange((r) => ({ ...r, [key]: value }))
  }

  const statuses = useMemo(
    () => (data ? Object.entries(data.orders.by_status).filter(([, n]) => n > 0) : []),
    [data],
  )

  const rangeLabel = preset === 'custom' || !data
    ? 'selected range'
    : PRESETS.find((p) => p.id === preset)?.label.toLowerCase()

  return (
    <div>
      <PageHeading title="Dashboard" subtitle="Sales, stock and work waiting for you.">
        <div className="flex rounded-lg border border-gray-200 bg-white p-0.5" role="group" aria-label="Date range">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              aria-pressed={preset === p.id}
              onClick={() => choosePreset(p)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                preset === p.id ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-sm text-gray-500">
          <input
            type="date" aria-label="From date" value={range.from} max={range.to}
            onChange={(e) => setCustom('from', e.target.value)}
            className={`${inputCls} w-auto py-1.5`}
          />
          <span>to</span>
          <input
            type="date" aria-label="To date" value={range.to} min={range.from} max={isoDay(new Date())}
            onChange={(e) => setCustom('to', e.target.value)}
            className={`${inputCls} w-auto py-1.5`}
          />
        </div>
        <button
          type="button" onClick={load} aria-label="Refresh"
          className="rounded-lg border border-gray-200 bg-white p-2 text-gray-500 hover:bg-gray-50 hover:text-gray-900"
        >
          <IconRefresh size={18} className={loading ? 'animate-spin' : ''} />
        </button>
      </PageHeading>

      {error && !data && <ErrorState message={error} onRetry={load} />}

      {!data && loading && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <CardSkeleton key={i} />)}
          </div>
          <CardSkeleton className="h-72" />
        </div>
      )}

      {data && (
        <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">
              {error} Showing the last figures that loaded.
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Kpi
              icon={IconCurrencyRupee} tone="bg-gold"
              label={`Revenue · ${rangeLabel}`} value={inr(data.revenue.range)}
              sub={`${data.orders.paid_range} order${data.orders.paid_range === 1 ? '' : 's'} · avg ${inr(data.orders.average_value)}`}
            />
            <Kpi icon={IconCurrencyRupee} label="Revenue today" value={inr(data.revenue.today)}
              sub={`${inr(data.revenue.last_7d)} in the last 7 days`} />
            <Kpi icon={IconCurrencyRupee} label="Revenue · last 30 days" value={inr(data.revenue.last_30d)}
              sub="Excludes cancelled and returned orders" />
            {can('users') && (
              <Kpi icon={IconUsers} label="Customers" value={data.users.total.toLocaleString('en-IN')}
                sub={`${data.users.new_range} new in ${rangeLabel}`} />
            )}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <Todo icon={IconTruckDelivery} label="Orders to fulfil" count={data.pending.orders} to="/admin/orders" />
            <Todo icon={IconArrowBackUp} label="Returns to review" count={data.pending.returns} to="/admin/returns" />
            <Todo icon={IconPackageOff} label="Out of stock" count={data.products.out_of_stock} to="/admin/products" />
            {can('wholesale-inquiries') && <Todo icon={IconBuildingStore} label="New inquiries" count={data.pending.inquiries} to="/admin/inquiries" />}
            {can('contact-messages') && <Todo icon={IconMail} label="Unread messages" count={data.pending.messages} to="/admin/messages" />}
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <section className="rounded-xl border border-gray-200 bg-white p-6 xl:col-span-2">
              <div className="mb-5 flex items-baseline justify-between">
                <h2 className="font-medium text-gray-900">Revenue per day</h2>
                <span className="text-xs text-gray-400">
                  {data.range.from} → {data.range.to} · IST
                </span>
              </div>
              {data.revenue.range > 0 ? (
                <RevenueChart series={data.series} />
              ) : (
                <p className="flex h-44 items-center justify-center text-sm text-gray-400">
                  No sales in this range.
                </p>
              )}
            </section>

            <section className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="mb-4 font-medium text-gray-900">Orders by status</h2>
              {statuses.length === 0 ? (
                <p className="py-8 text-center text-sm text-gray-400">No orders in this range.</p>
              ) : (
                <ul className="space-y-3">
                  {statuses.map(([status, count]) => (
                    <li key={status}>
                      <div className="mb-1 flex justify-between text-sm">
                        <span className="text-gray-700">{humanize(status)}</span>
                        <span className="font-medium tabular-nums text-gray-900">{count}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-gray-900"
                          style={{ width: `${(count / data.orders.range) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <section className="overflow-hidden rounded-xl border border-gray-200 bg-white xl:col-span-2">
              <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
                <h2 className="font-medium text-gray-900">Recent orders</h2>
                <Link to="/admin/orders" className="text-sm font-medium text-gray-900 underline underline-offset-2 hover:underline">
                  View all
                </Link>
              </div>
              {data.recent_orders.length === 0 ? (
                <p className="px-6 py-10 text-center text-sm text-gray-400">No orders yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                        <th className="px-6 py-3 font-medium">Order</th>
                        <th className="px-6 py-3 font-medium">Customer</th>
                        <th className="px-6 py-3 font-medium">Status</th>
                        <th className="px-6 py-3 text-right font-medium">Total</th>
                        <th className="px-6 py-3 font-medium">Placed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_orders.map((o) => (
                        <tr key={o.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                          <td className="px-6 py-3">
                            <Link to={`/admin/orders/${o.id}`} className="font-medium text-gray-900 hover:underline">
                              {o.order_number}
                            </Link>
                          </td>
                          <td className="px-6 py-3 text-gray-600">{o.customer_name}</td>
                          <td className="px-6 py-3">
                            <Badge tone={ORDER_STATUS_TONE[o.status]}>{humanize(o.status)}</Badge>
                          </td>
                          <td className="px-6 py-3 text-right tabular-nums text-gray-900">{inr(o.total_amount)}</td>
                          <td className="px-6 py-3 whitespace-nowrap text-gray-500">{formatDateTime(o.placed_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <div className="space-y-6">
              <section className="rounded-xl border border-gray-200 bg-white p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-medium text-gray-900">Low stock</h2>
                  <span className="text-xs text-gray-400">
                    {data.products.low_stock} at or under {data.products.low_stock_threshold}
                  </span>
                </div>
                {data.products.low_stock_items.length === 0 ? (
                  <p className="py-4 text-center text-sm text-gray-400">Everything is well stocked.</p>
                ) : (
                  <ul className="divide-y divide-gray-100">
                    {data.products.low_stock_items.map((item, i) => (
                      <li key={`${item.product_id}-${i}`} className="flex items-center gap-3 py-2.5">
                        {item.stock_qty === 0 && <IconAlertTriangle size={16} className="shrink-0 text-red-500" />}
                        <Link to={`/admin/products/${item.product_id}`} className="min-w-0 flex-1 hover:underline">
                          <div className="truncate text-sm text-gray-900">{item.name}</div>
                          <div className="text-xs text-gray-500">{item.size} · {item.color_name}</div>
                        </Link>
                        <Badge tone={item.stock_qty === 0 ? 'red' : 'amber'}>
                          {item.stock_qty === 0 ? 'Out' : `${item.stock_qty} left`}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="rounded-xl border border-gray-200 bg-white p-6">
                <h2 className="mb-4 flex items-center gap-2 font-medium text-gray-900">
                  <IconShoppingCart size={18} stroke={1.5} className="text-gray-400" /> Best sellers
                </h2>
                {data.top_products.length === 0 ? (
                  <p className="py-4 text-center text-sm text-gray-400">No sales in this range.</p>
                ) : (
                  <ol className="space-y-2.5">
                    {data.top_products.map((p, i) => (
                      <li key={p.product_id} className="flex items-center gap-3 text-sm">
                        <span className="w-4 text-gray-400 tabular-nums">{i + 1}</span>
                        <Link to={`/admin/products/${p.product_id}`} className="min-w-0 flex-1 truncate text-gray-900 hover:underline">
                          {p.name}
                        </Link>
                        <span className="tabular-nums text-gray-500">{p.units} sold</span>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
