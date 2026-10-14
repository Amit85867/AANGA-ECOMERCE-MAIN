import clsx from 'clsx'
import { forwardRef, useId } from 'react'
import { IconChevronDown, IconMinus, IconPlus } from '@tabler/icons-react'

/*
 * Form controls that share Input's look: hairline border that turns black on
 * focus, 44px tall (a comfortable touch target), label above, message below.
 */
const controlCls = (error, extra) =>
  clsx(
    'w-full bg-card text-fg placeholder:text-subtle rounded-card',
    'border outline-none transition-colors duration-200',
    'border-hairline focus:border-primary focus:ring-1 focus:ring-primary',
    'disabled:bg-fill disabled:text-subtle disabled:cursor-not-allowed',
    error && 'border-danger focus:border-danger focus:ring-danger',
    extra,
  )

function Shell({ id, label, error, hint, required, children }) {
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="block mb-1.5 text-xs font-medium uppercase tracking-[0.05em] text-muted">
          {label}
          {required && <span className="text-danger" aria-hidden="true"> *</span>}
        </label>
      )}
      {children}
      {(error || hint) && (
        <p id={`${id}-msg`} className={clsx('mt-1.5 text-xs', error ? 'text-danger' : 'text-muted')}>
          {error || hint}
        </p>
      )}
    </div>
  )
}

export const Select = forwardRef(function Select(
  { label, error, hint, className, id, children, required, ...props }, ref,
) {
  const auto = useId()
  const fieldId = id || props.name || auto
  return (
    <Shell id={fieldId} label={label} error={error} hint={hint} required={required}>
      <div className="relative">
        <select
          ref={ref} id={fieldId} required={required}
          aria-invalid={!!error || undefined}
          aria-describedby={error || hint ? `${fieldId}-msg` : undefined}
          className={controlCls(error, clsx('h-11 pl-4 pr-10 appearance-none cursor-pointer', className))}
          {...props}
        >
          {children}
        </select>
        <IconChevronDown size={16} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-muted" />
      </div>
    </Shell>
  )
})

export const Textarea = forwardRef(function Textarea(
  { label, error, hint, className, id, rows = 4, required, ...props }, ref,
) {
  const auto = useId()
  const fieldId = id || props.name || auto
  return (
    <Shell id={fieldId} label={label} error={error} hint={hint} required={required}>
      <textarea
        ref={ref} id={fieldId} rows={rows} required={required}
        aria-invalid={!!error || undefined}
        aria-describedby={error || hint ? `${fieldId}-msg` : undefined}
        className={controlCls(error, clsx('px-4 py-3 resize-y', className))}
        {...props}
      />
    </Shell>
  )
})

export function Checkbox({ label, className, ...props }) {
  return (
    <label className={clsx('inline-flex items-center gap-2.5 text-sm text-fg cursor-pointer', className)}>
      <input type="checkbox" className="h-4 w-4 rounded border-hairline accent-black" {...props} />
      {label}
    </label>
  )
}

/* − 2 + : never goes below min or above max, and says why it stopped. */
export function QuantityStepper({ value, min = 1, max = 99, onChange, disabled, label = 'Quantity', size = 'md' }) {
  const h = size === 'sm' ? 'h-9 w-9' : 'h-11 w-11'
  const btn = clsx(
    h, 'inline-flex items-center justify-center text-fg transition-colors',
    'hover:bg-fill disabled:text-hairline disabled:hover:bg-transparent disabled:cursor-not-allowed',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary',
  )
  return (
    <div
      role="group" aria-label={label}
      className="inline-flex items-center rounded-card border border-hairline bg-card overflow-hidden"
    >
      <button type="button" className={btn} aria-label="Decrease quantity"
        disabled={disabled || value <= min} onClick={() => onChange(value - 1)}>
        <IconMinus size={14} />
      </button>
      <span className={clsx('min-w-8 text-center text-sm font-semibold tabular-nums', disabled && 'text-muted')} aria-live="polite">
        {value}
      </span>
      <button type="button" className={btn} aria-label="Increase quantity"
        disabled={disabled || value >= max} onClick={() => onChange(value + 1)}>
        <IconPlus size={14} />
      </button>
    </div>
  )
}
