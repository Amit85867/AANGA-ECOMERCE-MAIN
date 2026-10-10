import { useState } from 'react'
import { IconRosetteDiscountCheck, IconStar, IconStarFilled, IconTrash } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/Toast'
import { confirm } from '@/components/admin/confirm'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { PageHeading, SearchInput } from '@/components/admin/controls'
import { formatDate, inputCls, notifyError } from '@/components/admin/helpers'

function Stars({ rating }) {
  return (
    <span className="inline-flex text-[#C8963E]" role="img" aria-label={`${rating} out of 5`}>
      {[1, 2, 3, 4, 5].map((n) =>
        n <= rating ? <IconStarFilled key={n} size={14} /> : <IconStar key={n} size={14} className="text-gray-300" />,
      )}
    </span>
  )
}

export default function AdminReviews() {
  const [q, setQ] = useState('')
  const [rating, setRating] = useState('')
  const [verified, setVerified] = useState('')
  const [sort, setSort] = useState('created_at:desc')
  const [removing, setRemoving] = useState(null)

  const [sortBy, dir] = sort.split(':')
  const list = useAdminList('/admin/reviews', 'reviews', { q, rating, verified, sort: sortBy, dir })

  const remove = async (review) => {
    const sure = await confirm({
      title: 'Remove this review?',
      message: `The ${review.rating}-star review by ${review.customer_name} on “${review.product_name}” will be deleted from the storefront. A copy is kept in the audit log.`,
      confirmLabel: 'Remove review',
      danger: true,
    })
    if (!sure) return
    setRemoving(review.id)
    try {
      await adminApi.delete(`/admin/reviews/${review.id}`)
      toast.success('Review removed.')
      list.reload()
    } catch (err) {
      notifyError(err, 'Could not remove the review.')
    }
    setRemoving(null)
  }

  return (
    <div>
      <PageHeading title="Reviews" subtitle="What customers have written about your products." />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_auto_auto_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Search review text, product or customer" />
        <select value={rating} onChange={(e) => setRating(e.target.value)} aria-label="Rating" className={`${inputCls} w-auto`}>
          <option value="">All ratings</option>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} star{n === 1 ? '' : 's'}</option>)}
        </select>
        <select value={verified} onChange={(e) => setVerified(e.target.value)} aria-label="Purchase" className={`${inputCls} w-auto`}>
          <option value="">All reviews</option>
          <option value="true">Verified purchase</option>
          <option value="false">Not verified</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className={`${inputCls} w-auto`}>
          <option value="created_at:desc">Newest first</option>
          <option value="created_at:asc">Oldest first</option>
          <option value="rating:asc">Lowest rated first</option>
          <option value="rating:desc">Highest rated first</option>
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={list.filtered}
        skeleton={<TableSkeleton rows={6} columns={4} />}
        emptyIcon={IconStar}
        emptyTitle="No reviews yet"
        emptyHint="Reviews appear here as customers write them."
      >
        <ul className={`space-y-3 ${list.loading ? 'opacity-60' : ''}`}>
          {list.rows.map((r) => (
            <li key={r.id} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <Stars rating={r.rating} />
                    {r.is_verified && (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
                        <IconRosetteDiscountCheck size={14} /> Verified purchase
                      </span>
                    )}
                    <span className="text-xs text-gray-400">{formatDate(r.created_at)}</span>
                  </div>
                  <a
                    href={`/product/${r.product_slug}`} target="_blank" rel="noreferrer"
                    className="mt-1.5 block truncate text-sm font-medium text-gray-900 hover:underline"
                  >
                    {r.product_name}
                  </a>
                </div>
                <button
                  type="button" onClick={() => remove(r)} disabled={removing === r.id}
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <IconTrash size={16} /> {removing === r.id ? 'Removing…' : 'Remove'}
                </button>
              </div>
              {r.title && <p className="mt-3 text-sm font-medium text-gray-900">{r.title}</p>}
              {r.body && <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-gray-700">{r.body}</p>}
              <p className="mt-3 text-xs text-gray-500">
                {r.customer_name}{r.customer_email ? ` · ${r.customer_email}` : ''}
              </p>
            </li>
          ))}
        </ul>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="reviews" />
      </DataState>
    </div>
  )
}
