import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import { Container, PageTitle } from '@/components/ui/Display'
import { useAuthStore } from '@/store/useAuthStore'
import Seo from '@/components/Seo'

/*
 * Find an order by its number and open it. Tracking itself lives on the order
 * page, so there is one place that shows an order's progress, not two.
 *
 * Orders belong to accounts, so looking one up needs a sign-in.
 */
export default function OrderTracking() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const initializing = useAuthStore((s) => s.initializing)
  const [orderNumber, setOrderNumber] = useState(params.get('order') || '')
  const [error, setError] = useState('')
  const [searching, setSearching] = useState(false)

  const find = useCallback(async (number) => {
    const wanted = number.trim().toLowerCase()
    if (!wanted) {
      setError('Enter your order number. It looks like ANG-2026-10001.')
      return
    }
    setSearching(true)
    setError('')
    try {
      // Walk the customer's order pages until the number turns up.
      for (let page = 1; page <= 10; page += 1) {
        const { data } = await apiClient.get('/orders', { params: { page, per_page: 50 } })
        const match = data.orders.find((o) => o.order_number.toLowerCase() === wanted)
        if (match) {
          navigate(`/account/orders/${match.id}`)
          return
        }
        if (page >= data.pages) break
      }
      setError('We could not find that order on your account. Check the number and try again.')
    } catch {
      setError('We could not look up your order just now. Please try again.')
    }
    setSearching(false)
  }, [navigate])

  // Arriving with ?order=… (a link from an email) looks it up straight away.
  useEffect(() => {
    const fromLink = params.get('order')
    if (fromLink && isAuthenticated) find(fromLink)
  }, [params, isAuthenticated, find])

  return (
    <>
      <Seo title="Track Your Order" description="Track the delivery of your AANGA order." />
      <Container className="max-w-2xl pb-20">
        <PageTitle
          title="Track your order"
          subtitle="Enter the order number from your confirmation to see where it is."
          crumbs={[{ label: 'Home', to: '/' }, { label: 'Track order' }]}
        />

        <Card className="p-6 sm:p-8">
          {!initializing && !isAuthenticated ? (
            <div className="text-center">
              <p className="text-sm text-muted">Sign in to see your orders and where each one is.</p>
              <Button to="/login" state={{ from: '/track-order' }} className="mt-5">Sign in</Button>
            </div>
          ) : (
            <form
              onSubmit={(e) => { e.preventDefault(); find(orderNumber) }}
              className="flex flex-col gap-3 sm:flex-row sm:items-start" noValidate
            >
              <div className="flex-1">
                <Input
                  label="Order number" name="order-number" value={orderNumber} error={error}
                  onChange={(e) => { setOrderNumber(e.target.value); setError('') }}
                  placeholder="ANG-2026-10001" autoComplete="off"
                />
              </div>
              <Button type="submit" disabled={searching} className="sm:mt-[1.625rem]">
                {searching ? 'Looking…' : 'Track order'}
              </Button>
            </form>
          )}
        </Card>

        {isAuthenticated && (
          <p className="mt-6 text-center text-sm text-muted">
            Or see <Link to="/account/orders" className="font-medium text-fg underline underline-offset-2">all your orders</Link>.
          </p>
        )}
      </Container>
    </>
  )
}
