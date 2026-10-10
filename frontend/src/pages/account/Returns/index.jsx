import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowBackUp } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { Modal } from '@/components/ui/Overlay'
import { EmptyState, ErrorState, Skeleton, StatusBadge } from '@/components/ui/Display'
import { RETURN_REASONS, RETURN_STATUS, formatDate, humanize, inr } from '@/utils/format'
import Seo from '@/components/Seo'

const REASON_LABEL = Object.fromEntries(RETURN_REASONS)

// What each stage means for the customer, in their terms.
const NEXT_STEP = {
  requested: 'We are reviewing your request and will confirm shortly.',
  approved: 'Approved. We are arranging a pickup.',
  pickup_scheduled: 'A courier will collect the item. Keep it packed with its tags.',
  picked_up: 'The item is on its way back to us.',
  inspected: 'We have received the item and are checking it.',
  resolved: 'This return is complete.',
  rejected: 'We could not accept this return. Contact us if you think this is a mistake.',
}

function ReturnDetail({ returnId, onClose }) {
  const [ret, setRet] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!returnId) return
    setRet(null)
    setFailed(false)
    apiClient.get(`/returns/${returnId}`)
      .then(({ data }) => setRet(data))
      .catch(() => setFailed(true))
  }, [returnId])

  return (
    <Modal open={Boolean(returnId)} onClose={onClose} title="Return details">
      {failed ? (
        <ErrorState message="We could not load this return." />
      ) : !ret ? (
        <div className="space-y-3"><Skeleton className="h-5 w-40" /><Skeleton className="h-24" /></div>
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge status={ret.status} map={RETURN_STATUS} />
            <span className="text-sm text-muted">Requested {formatDate(ret.requested_at)}</span>
          </div>
          <p className="rounded-card bg-fill px-4 py-3 text-sm text-fg">{NEXT_STEP[ret.status]}</p>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-[0.05em] text-subtle">Item</dt>
              <dd className="mt-0.5 text-fg">
                {ret.product_name}
                <span className="text-muted"> · {[ret.size && `Size ${ret.size}`, ret.color_name, `Qty ${ret.quantity}`].filter(Boolean).join(' · ')}</span>
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.05em] text-subtle">Order</dt>
              <dd className="mt-0.5">
                <Link to={`/account/orders/${ret.order_id}`} className="font-medium text-fg underline underline-offset-2">{ret.order_number}</Link>
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.05em] text-subtle">Reason</dt>
              <dd className="mt-0.5 text-fg">{REASON_LABEL[ret.reason] || humanize(ret.reason)}</dd>
            </div>
            {ret.description && (
              <div>
                <dt className="text-xs uppercase tracking-[0.05em] text-subtle">Your note</dt>
                <dd className="mt-0.5 whitespace-pre-line text-fg">{ret.description}</dd>
              </div>
            )}
            {ret.status === 'resolved' && (
              <div>
                <dt className="text-xs uppercase tracking-[0.05em] text-subtle">Outcome</dt>
                <dd className="mt-0.5 text-fg">
                  {humanize(ret.resolution_type)}
                  {ret.refund_amount != null && ` of ${inr(ret.refund_amount)}`}
                  {ret.resolved_at && ` on ${formatDate(ret.resolved_at)}`}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </Modal>
  )
}

export default function Returns() {
  const [returns, setReturns] = useState(null)
  const [failed, setFailed] = useState(false)
  const [openId, setOpenId] = useState(null)

  const load = useCallback(() => {
    setFailed(false)
    return apiClient.get('/returns', { params: { per_page: 50 } })
      .then(({ data }) => setReturns(data.returns))
      .catch(() => setFailed(true))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <>
      <Seo title="My Returns" noindex />
      <h1 className="display text-3xl text-fg">Returns</h1>
      <p className="mt-2 text-sm text-muted">
        Follow the returns you have requested. To start a new one, open the order and choose “Return an item”.
      </p>

      <div className="mt-8">
        {failed ? (
          <ErrorState message="We could not load your returns." onRetry={load} />
        ) : returns === null ? (
          <div className="space-y-3">{[0, 1].map((i) => <Skeleton key={i} className="h-24" />)}</div>
        ) : returns.length === 0 ? (
          <EmptyState
            icon={IconArrowBackUp} title="No returns"
            hint="You have not requested any returns. Items can be returned within 7 days of delivery."
            action={<Button to="/account/orders" variant="secondary">View my orders</Button>}
          />
        ) : (
          <ul className="space-y-3">
            {returns.map((r) => (
              <li key={r.id}>
                <Card className="flex flex-wrap items-center gap-4 p-5">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                      <span className="text-sm font-semibold text-fg">{r.product_name}</span>
                      <StatusBadge status={r.status} map={RETURN_STATUS} />
                    </div>
                    <p className="mt-1.5 text-sm text-muted">{NEXT_STEP[r.status]}</p>
                    <p className="mt-1 text-xs text-subtle">
                      Order {r.order_number} · requested {formatDate(r.requested_at)}
                    </p>
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => setOpenId(r.id)}>Details</Button>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ReturnDetail returnId={openId} onClose={() => setOpenId(null)} />
    </>
  )
}
