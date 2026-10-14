import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconRosetteDiscountCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { useAuthStore } from '@/store/useAuthStore'
import { toast } from '@/components/ui/toastStore'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Overlay'
import { ErrorState, Rating, RatingInput, Skeleton } from '@/components/ui/Display'
import { formatDate } from '@/utils/format'

const PER_PAGE = 5

function ReviewForm({ productId, productName, open, onClose, onSubmitted }) {
  const [rating, setRating] = useState(0)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (saving) return
    if (!rating) {
      setError('Choose a star rating.')
      return
    }
    setError('')
    setSaving(true)
    try {
      const { data } = await apiClient.post('/reviews', {
        product_id: productId,
        rating,
        ...(title.trim() ? { title: title.trim() } : {}),
        ...(body.trim() ? { body: body.trim() } : {}),
      })
      toast.success(data.is_verified ? 'Thank you — your verified review is live.' : 'Thank you — your review is live.')
      onSubmitted()
      onClose()
    } catch (err) {
      setError(err.response?.data?.error || 'Could not submit your review. Please try again.')
    }
    setSaving(false)
  }

  return (
    <Modal open={open} onClose={onClose} title="Write a review">
      <form onSubmit={submit} className="space-y-5" noValidate>
        <p className="text-sm text-muted">{productName}</p>
        <RatingInput value={rating} onChange={(n) => { setRating(n); setError('') }} />
        <Input
          label="Headline" name="review-title" maxLength={200} value={title}
          onChange={(e) => setTitle(e.target.value)} placeholder="Sum it up in a few words"
        />
        <Textarea
          label="Your review" name="review-body" maxLength={5000} rows={5} value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="How does it fit? How is the fabric? Would you buy it again?"
        />
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        <div className="flex justify-end gap-3 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Submitting…' : 'Submit review'}</Button>
        </div>
      </form>
    </Modal>
  )
}

export default function Reviews({ productId, productName, onChanged }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const [data, setData] = useState(null)
  const [reviews, setReviews] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [formOpen, setFormOpen] = useState(false)

  const load = useCallback(
    (pageToLoad) => {
      setLoading(true)
      setError(false)
      return apiClient
        .get(`/reviews/product/${productId}`, { params: { page: pageToLoad, per_page: PER_PAGE } })
        .then(({ data: res }) => {
          setData(res)
          setPage(res.page)
          setReviews((current) => (pageToLoad === 1 ? res.reviews : [...current, ...res.reviews]))
        })
        .catch(() => setError(true))
        .finally(() => setLoading(false))
    },
    [productId],
  )

  useEffect(() => { load(1) }, [load])

  const total = data?.total ?? 0

  return (
    <section aria-labelledby="reviews-heading" className="border-t border-hairline/60 pt-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="reviews-heading" className="display text-2xl lg:text-3xl text-fg">Customer reviews</h2>
          {total > 0 && (
            <div className="mt-3 flex items-center gap-3">
              <span className="display text-3xl text-fg tabular-nums">{Number(data.avg_rating).toFixed(1)}</span>
              <div>
                <Rating value={data.avg_rating} size={16} />
                <p className="text-xs text-muted mt-0.5">Based on {total} review{total === 1 ? '' : 's'}</p>
              </div>
            </div>
          )}
        </div>
        {isAuthenticated ? (
          <Button variant="secondary" onClick={() => setFormOpen(true)}>Write a review</Button>
        ) : (
          <p className="text-sm text-muted">
            <Link to="/login" className="font-medium text-fg underline underline-offset-2">Sign in</Link> to write a review.
          </p>
        )}
      </div>

      <div className="mt-8">
        {error && reviews.length === 0 ? (
          <ErrorState message="We could not load the reviews." onRetry={() => load(1)} />
        ) : loading && reviews.length === 0 ? (
          <div className="space-y-6">
            {[0, 1].map((i) => (
              <div key={i}><Skeleton className="h-4 w-28" /><Skeleton className="mt-3 h-4 w-2/3" /><Skeleton className="mt-2 h-4 w-1/2" /></div>
            ))}
          </div>
        ) : total === 0 ? (
          <p className="rounded-card bg-fill px-6 py-10 text-center text-sm text-muted">
            No reviews yet. Be the first to share what you think.
          </p>
        ) : (
          <>
            <ul className="divide-y divide-hairline/60">
              {reviews.map((r) => (
                <li key={r.id} className="py-6 first:pt-0">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <Rating value={r.rating} />
                    {r.is_verified && (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-fg">
                        <IconRosetteDiscountCheck size={14} aria-hidden="true" /> Verified purchase
                      </span>
                    )}
                  </div>
                  {r.title && <h3 className="mt-2 text-sm font-semibold text-fg">{r.title}</h3>}
                  {r.body && <p className="mt-1.5 text-sm leading-relaxed text-muted whitespace-pre-line">{r.body}</p>}
                  <p className="mt-3 text-xs text-muted">{r.user_name} · {formatDate(r.created_at)}</p>
                </li>
              ))}
            </ul>
            {page < (data?.pages || 1) && (
              <div className="mt-6 text-center">
                <Button variant="secondary" size="sm" disabled={loading} onClick={() => load(page + 1)}>
                  {loading ? 'Loading…' : 'Show more reviews'}
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      <ReviewForm
        productId={productId} productName={productName}
        open={formOpen} onClose={() => setFormOpen(false)}
        onSubmitted={() => { load(1); onChanged?.() }}
      />
    </section>
  )
}
