import clsx from 'clsx'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  IconAlertCircle, IconChevronRight, IconRefresh, IconStar, IconStarFilled,
} from '@tabler/icons-react'
import Button from '@/components/ui/Button'
import { ORDER_STATUS, inr } from '@/utils/format'

/* Small display pieces shared across the storefront. */

/* Page-width wrapper: one gutter and one max width everywhere. */
export function Container({ className, children, as: Tag = 'div', ...props }) {
  return (
    <Tag className={clsx('mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-8', className)} {...props}>
      {children}
    </Tag>
  )
}

export function Breadcrumbs({ items, className }) {
  return (
    <nav aria-label="Breadcrumb" className={clsx('text-xs text-subtle', className)}>
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((item, i) => (
          <li key={item.label} className="flex items-center gap-1.5">
            {i > 0 && <IconChevronRight size={12} aria-hidden="true" />}
            {item.to ? (
              <Link to={item.to} className="hover:text-fg underline-offset-2 hover:underline">{item.label}</Link>
            ) : (
              <span className="text-muted" aria-current="page">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

/* Title block at the top of an inner page. */
export function PageTitle({ title, subtitle, crumbs, children, className }) {
  return (
    <header className={clsx('pt-6 pb-6 sm:pt-8 sm:pb-8', className)}>
      {crumbs && <Breadcrumbs items={crumbs} className="mb-3" />}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-3xl sm:text-4xl text-fg">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-muted max-w-2xl">{subtitle}</p>}
        </div>
        {children}
      </div>
    </header>
  )
}

// Tones use only the frozen tokens: there is no green or amber in the palette,
// so "done" is the solid dark badge and "needs attention" is the soft accent.
const BADGE_TONES = {
  neutral: 'bg-fill text-muted',
  dark: 'bg-primary text-on-primary',
  accent: 'bg-accent-soft text-fg',
  danger: 'bg-danger-soft text-danger',
  outline: 'border border-hairline text-muted',
}

export function Badge({ tone = 'neutral', className, children }) {
  return (
    <span className={clsx('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', BADGE_TONES[tone], className)}>
      {children}
    </span>
  )
}

export function StatusBadge({ status, map = ORDER_STATUS }) {
  const [label, tone] = map[status] || [status, 'neutral']
  return <Badge tone={tone}>{label}</Badge>
}

export function Skeleton({ className }) {
  return <div className={clsx('animate-pulse rounded-card bg-fill-strong/70', className)} aria-hidden="true" />
}

/* Same footprint as a ProductCard, so the grid does not jump when data lands. */
export function ProductCardSkeleton() {
  return (
    <div aria-hidden="true">
      <Skeleton className="aspect-[3/4] w-full" />
      <Skeleton className="mt-3 h-3 w-1/3" />
      <Skeleton className="mt-2 h-4 w-4/5" />
      <Skeleton className="mt-2 h-4 w-2/5" />
    </div>
  )
}

export function EmptyState({ icon: Icon, title, hint, action, className }) {
  return (
    <div className={clsx('flex flex-col items-center text-center px-6 py-16', className)}>
      {Icon && (
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-fill text-subtle">
          <Icon size={28} stroke={1.5} />
        </div>
      )}
      <h2 className="display text-xl text-fg mt-5">{title}</h2>
      {hint && <p className="mt-2 text-sm text-muted max-w-sm">{hint}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

export function ErrorState({ message = 'Something went wrong while loading this.', onRetry, className }) {
  return (
    <div role="alert" className={clsx('flex flex-col items-center text-center px-6 py-14 rounded-card bg-danger-soft/50', className)}>
      <IconAlertCircle size={28} stroke={1.5} className="text-danger" />
      <p className="mt-3 text-sm font-medium text-fg">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          <IconRefresh size={14} /> Try again
        </Button>
      )}
    </div>
  )
}

/* Read-only star rating. `count` adds "(12)". */
export function Rating({ value = 0, count, size = 14, className }) {
  const rounded = Math.round(value * 2) / 2
  return (
    <span className={clsx('inline-flex items-center gap-1.5', className)}>
      <span className="inline-flex text-fg" role="img" aria-label={`${Number(value).toFixed(1)} out of 5`}>
        {[1, 2, 3, 4, 5].map((n) =>
          n <= rounded
            ? <IconStarFilled key={n} size={size} />
            : <IconStar key={n} size={size} className="text-hairline" />,
        )}
      </span>
      {count != null && <span className="text-xs text-subtle">({count})</span>}
    </span>
  )
}

/* Star picker. Real radio inputs, so arrow keys and screen readers just work. */
export function RatingInput({ value, onChange, name = 'rating', error }) {
  const [hover, setHover] = useState(0)
  const shown = hover || value || 0
  return (
    <fieldset>
      <legend className="block mb-1.5 text-xs font-medium uppercase tracking-[0.05em] text-muted">
        Your rating<span className="text-danger" aria-hidden="true"> *</span>
      </legend>
      <div className="inline-flex gap-1" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <label
            key={n}
            onMouseEnter={() => setHover(n)}
            className={clsx(
              'cursor-pointer rounded transition-colors',
              'has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary',
              n <= shown ? 'text-fg' : 'text-hairline',
            )}
          >
            <input
              type="radio" name={name} value={n} checked={value === n}
              onChange={() => onChange(n)} className="sr-only"
              aria-label={`${n} star${n === 1 ? '' : 's'}`}
            />
            <IconStarFilled size={30} aria-hidden="true" />
          </label>
        ))}
      </div>
      {error && <p className="mt-1.5 text-xs text-danger">{error}</p>}
    </fieldset>
  )
}

/* Selling price, struck-through MRP and the saving — one format everywhere. */
export function Price({ price, mrp, size = 'md', className }) {
  const off = mrp > price ? Math.round(((mrp - price) / mrp) * 100) : 0
  return (
    <span className={clsx('inline-flex flex-wrap items-baseline gap-x-2 gap-y-0.5', className)}>
      <span className={clsx('font-semibold text-fg tabular-nums', size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-sm' : 'text-base')}>
        {inr(price)}
      </span>
      {off > 0 && (
        <>
          <span className={clsx('text-subtle line-through tabular-nums', size === 'lg' ? 'text-base' : 'text-xs')}>
            <span className="sr-only">Was </span>{inr(mrp)}
          </span>
          <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-fg">{off}% off</span>
        </>
      )}
    </span>
  )
}

/* Checkout progress: 1 Address — 2 Payment — 3 Review. */
export function Stepper({ steps, current }) {
  return (
    <ol className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm">
      {steps.map((step, i) => {
        const done = i < current
        const active = i === current
        return (
          <li key={step} className="flex items-center gap-2 sm:gap-3" aria-current={active ? 'step' : undefined}>
            {i > 0 && <span className={clsx('h-px w-5 sm:w-10', done || active ? 'bg-primary' : 'bg-hairline')} aria-hidden="true" />}
            <span className={clsx(
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
              done || active ? 'bg-primary text-on-primary' : 'bg-fill text-subtle',
            )}>
              {i + 1}
            </span>
            <span className={clsx('font-medium', active ? 'text-fg' : done ? 'text-muted' : 'text-subtle')}>{step}</span>
          </li>
        )
      })}
    </ol>
  )
}
