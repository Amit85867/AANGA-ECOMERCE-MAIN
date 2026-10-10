import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react'

/* 1 … 4 5 [6] 7 8 … 20 — never a button per page. */
function pageList(page, pages) {
  const wanted = new Set([1, pages, page - 1, page, page + 1])
  const list = [...wanted].filter((p) => p >= 1 && p <= pages).sort((a, b) => a - b)
  const out = []
  list.forEach((p, i) => {
    if (i > 0 && p - list[i - 1] > 1) out.push(`gap-${p}`)
    out.push(p)
  })
  return out
}

export default function Pagination({ page, pages, total, onChange, noun = 'results' }) {
  if (!total) return null

  const btn =
    'inline-flex h-9 min-w-9 items-center justify-center rounded-lg px-2.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40'

  return (
    <nav
      aria-label="Pagination"
      className="mt-4 flex flex-wrap items-center justify-between gap-3"
    >
      <p className="text-sm text-gray-500">
        Page <span className="font-medium text-gray-900">{page}</span> of {pages || 1} ·{' '}
        {total.toLocaleString('en-IN')} {noun}
      </p>
      {pages > 1 && (
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Previous page"
            disabled={page <= 1}
            onClick={() => onChange(page - 1)}
            className={`${btn} text-gray-600 hover:bg-gray-100`}
          >
            <IconChevronLeft size={18} />
          </button>
          {pageList(page, pages).map((p) =>
            typeof p === 'string' ? (
              <span key={p} className="px-1 text-gray-400" aria-hidden="true">…</span>
            ) : (
              <button
                key={p}
                type="button"
                aria-current={p === page ? 'page' : undefined}
                onClick={() => onChange(p)}
                className={`${btn} ${p === page ? 'bg-gray-900 font-medium text-white' : 'text-gray-600 hover:bg-gray-100'}`}
              >
                {p}
              </button>
            ),
          )}
          <button
            type="button"
            aria-label="Next page"
            disabled={page >= pages}
            onClick={() => onChange(page + 1)}
            className={`${btn} text-gray-600 hover:bg-gray-100`}
          >
            <IconChevronRight size={18} />
          </button>
        </div>
      )}
    </nav>
  )
}
