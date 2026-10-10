import clsx from 'clsx'
import { forwardRef } from 'react'

/*
 * Text input. 1px hairline border that becomes a 2px black border on focus,
 * per the design system. Pass `pill` for search-style fields.
 */
const Input = forwardRef(function Input(
  { label, error, hint, pill = false, className, id, ...props },
  ref,
) {
  const inputId = id || props.name

  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={inputId}
          className="block mb-1.5 text-xs font-medium uppercase tracking-[0.05em] text-muted"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={clsx(
          'w-full h-11 px-4 bg-card text-fg placeholder:text-subtle',
          'border transition-colors duration-200 outline-none',
          // 1px idle → 2px black on focus, without the box shifting
          'border-hairline focus:border-primary focus:ring-1 focus:ring-primary',
          error && 'border-danger focus:border-danger focus:ring-danger',
          pill ? 'rounded-full' : 'rounded-card',
          className,
        )}
        aria-invalid={!!error || undefined}
        {...props}
      />
      {(error || hint) && (
        <p className={clsx('mt-1.5 text-xs', error ? 'text-danger' : 'text-muted')}>
          {error || hint}
        </p>
      )}
    </div>
  )
})

export default Input
