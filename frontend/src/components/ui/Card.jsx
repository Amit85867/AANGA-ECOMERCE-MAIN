import clsx from 'clsx'

/*
 * Elevated white surface — the base container of the design system.
 * `hover` adds the "lift" interaction used by product tiles.
 */
export default function Card({ hover = false, block = false, className, children, ...props }) {
  return (
    <div
      className={clsx(
        'bg-card shadow-card',
        block ? 'rounded-block' : 'rounded-card',
        hover &&
          'transition-all duration-300 hover:shadow-lift hover:-translate-y-0.5 cursor-pointer',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
