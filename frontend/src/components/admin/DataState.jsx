import { IconAlertCircle, IconInbox, IconRefresh } from '@tabler/icons-react'

/* The three things a list can be instead of "showing rows". */

export function TableSkeleton({ rows = 6, columns = 5 }) {
  return (
    <div
      className="overflow-hidden rounded-xl border border-gray-200 bg-white"
      role="status"
      aria-label="Loading"
    >
      <div className="border-b border-gray-100 px-6 py-3.5">
        <div className="h-3 w-40 animate-pulse rounded bg-gray-100" />
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-6 border-b border-gray-50 px-6 py-4 last:border-0">
          {Array.from({ length: columns }).map((__, c) => (
            <div
              key={c}
              className="h-3.5 animate-pulse rounded bg-gray-100"
              // Uneven widths read as text; equal bars read as a broken table.
              style={{ width: `${[26, 18, 14, 12, 16, 10][c % 6]}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton({ className = 'h-28' }) {
  return <div className={`animate-pulse rounded-xl border border-gray-200 bg-gray-100/70 ${className}`} />
}

export function ErrorState({ message = 'Something went wrong while loading this.', onRetry }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center"
    >
      <IconAlertCircle size={32} stroke={1.5} className="text-red-500" />
      <p className="mt-3 text-sm font-medium text-red-900">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-red-700 ring-1 ring-red-200 hover:bg-red-100"
        >
          <IconRefresh size={16} /> Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ icon: Icon = IconInbox, title, hint, action }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-gray-300 bg-white px-6 py-14 text-center">
      <Icon size={36} stroke={1.25} className="text-gray-300" />
      <p className="mt-3 text-sm font-medium text-gray-900">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-gray-500">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

/*
 * Picks the right state for a list. `filtered` changes the empty message:
 * "nothing matches" is a different situation from "nothing exists yet".
 */
export default function DataState({
  loading, error, empty, onRetry, filtered,
  skeleton, emptyTitle, emptyHint, emptyAction, emptyIcon, children,
}) {
  if (loading) return skeleton ?? <TableSkeleton />
  if (error) return <ErrorState message={error} onRetry={onRetry} />
  if (empty) {
    return filtered ? (
      <EmptyState
        icon={emptyIcon}
        title="Nothing matches these filters"
        hint="Try a different search term or clear the filters."
      />
    ) : (
      <EmptyState icon={emptyIcon} title={emptyTitle} hint={emptyHint} action={emptyAction} />
    )
  }
  return children
}
