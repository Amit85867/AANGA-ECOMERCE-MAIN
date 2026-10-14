import { useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { IconCircleCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { useAuthStore } from '@/store/useAuthStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import AddressBlock from '@/components/account/AddressBlock'
import { Container, ErrorState, Skeleton } from '@/components/ui/Display'
import { formatDate, inr } from '@/utils/format'
import Seo from '@/components/Seo'

/*
 * The page a customer lands on after paying. It has its own URL and loads the
 * order from the API, so a refresh (or coming back from the payment window)
 * still shows the confirmation instead of an empty checkout.
 */
export default function OrderConfirmed() {
  const { id } = useParams()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const initializing = useAuthStore((s) => s.initializing)
  const user = useAuthStore((s) => s.user)
  const [order, setOrder] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) return
    apiClient.get(`/orders/${id}`)
      .then(({ data }) => setOrder(data))
      .catch(() => setFailed(true))
  }, [id, isAuthenticated])

  if (!initializing && !isAuthenticated) return <Navigate to="/login" replace />

  return (
    <>
      <Seo title="Order Confirmed" noindex />
      <Container className="py-12 sm:py-16 max-w-3xl">
        {failed ? (
          <ErrorState message="Your order was placed, but we could not load its details just now. You will find it under My Orders." />
        ) : !order ? (
          <div className="space-y-4" aria-busy="true"><Skeleton className="h-10 w-2/3" /><Skeleton className="h-64" /></div>
        ) : (
          <>
            <div className="text-center">
              <IconCircleCheck size={56} stroke={1.25} className="mx-auto text-fg" aria-hidden="true" />
              <h1 className="display text-3xl sm:text-4xl text-fg mt-4">Thank you — your order is in</h1>
              <p className="mt-3 text-sm text-muted">
                Order <span className="font-semibold text-fg">{order.order_number}</span>
                {user?.email && !user.email.endsWith('@phone.aanga.in') && <> · a confirmation is on its way to {user.email}</>}
              </p>
            </div>

            <Card className="mt-10 p-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Delivering to</h2>
                  <AddressBlock address={order.address} />
                </div>
                <div>
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Payment</h2>
                  <p className="text-sm text-fg">
                    {order.payment_method === 'cod'
                      ? `Cash on delivery — keep ${inr(order.total_amount)} ready`
                      : `Paid online — ${inr(order.total_amount)}`}
                  </p>
                  {order.expected_delivery && (
                    <>
                      <h2 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-[0.08em] text-muted">Expected by</h2>
                      <p className="text-sm text-fg">{formatDate(order.expected_delivery)}</p>
                    </>
                  )}
                </div>
              </div>

              <ul className="mt-6 divide-y divide-hairline/60 border-t border-hairline/60">
                {order.items.map((item) => (
                  <li key={item.id} className="flex items-center gap-4 py-3">
                    <div className="h-16 w-12 shrink-0 overflow-hidden rounded-lg bg-fill">
                      {item.image_url && <img src={item.image_url} alt="" width="96" height="128" className="h-full w-full object-cover" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-fg">{item.product_name}</p>
                      <p className="text-xs text-muted">
                        {[item.size && `Size ${item.size}`, item.color_name, `Qty ${item.quantity}`].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    <p className="text-sm tabular-nums text-fg">{inr(item.total_price)}</p>
                  </li>
                ))}
              </ul>
              <div className="flex justify-between border-t border-hairline/60 pt-4 text-sm font-semibold text-fg">
                <span>Total</span><span className="tabular-nums">{inr(order.total_amount)}</span>
              </div>
            </Card>

            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button to={`/account/orders/${order.id}`}>Track this order</Button>
              <Button to="/shop" variant="secondary">Continue shopping</Button>
            </div>
          </>
        )}
      </Container>
    </>
  )
}
