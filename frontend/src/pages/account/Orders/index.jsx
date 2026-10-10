import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconChevronRight, IconPackage } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { EmptyState, ErrorState, Skeleton, StatusBadge } from '@/components/ui/Display'
import { formatDate, inr } from '@/utils/format'
import Seo from '@/components/Seo'

const PER_PAGE = 10

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [meta, setMeta] = useState({ page: 1, pages: 1, total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback((page) => {
    setLoading(true)
    setError(false)
    return apiClient
      .get('/orders', { params: { page, per_page: PER_PAGE } })
      .then(({ data }) => {
        setOrders((current) => (page === 1 ? data.orders : [...current, ...data.orders]))
        setMeta({ page: data.page, pages: data.pages, total: data.total })
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load(1) }, [load])

  return (
    <>
      <Seo title="My Orders" noindex />
      <h1 className="display text-3xl text-fg">Orders</h1>
      <p className="mt-2 text-sm text-muted">Track a delivery, cancel an order or start a return.</p>

      <div className="mt-8">
        {error && orders.length === 0 ? (
          <ErrorState message="We could not load your orders." onRetry={() => load(1)} />
        ) : loading && orders.length === 0 ? (
          <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-24" />)}</div>
        ) : orders.length === 0 ? (
          <EmptyState
            icon={IconPackage} title="No orders yet"
            hint="When you place an order it will appear here."
            action={<Button to="/shop">Start shopping</Button>}
          />
        ) : (
          <>
            <ul className="space-y-3">
              {orders.map((o) => (
                <li key={o.id}>
                  <Link
                    to={`/account/orders/${o.id}`}
                    className="block rounded-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                  >
                    <Card hover className="flex items-center gap-4 p-5">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                          <span className="text-sm font-semibold text-fg">{o.order_number}</span>
                          <StatusBadge status={o.status} />
                        </div>
                        <p className="mt-1.5 truncate text-sm text-muted">{o.item_summary}</p>
                        <p className="mt-1 text-xs text-subtle">
                          {formatDate(o.placed_at)} · {o.item_count} item{o.item_count === 1 ? '' : 's'}
                        </p>
                      </div>
                      <span className="shrink-0 text-sm font-semibold tabular-nums text-fg">{inr(o.total_amount)}</span>
                      <IconChevronRight size={18} className="shrink-0 text-subtle" aria-hidden="true" />
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
            {meta.page < meta.pages && (
              <div className="mt-6 text-center">
                <Button variant="secondary" disabled={loading} onClick={() => load(meta.page + 1)}>
                  {loading ? 'Loading…' : 'Show older orders'}
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
