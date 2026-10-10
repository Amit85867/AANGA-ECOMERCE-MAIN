import clsx from 'clsx'
import { Link } from 'react-router-dom'

/*
 * Design system button.
 *   primary   — solid black, white text (high-intent actions)
 *   secondary — 2px outline
 *   subtle    — soft filled grey
 *   ghost     — text only
 *
 * Renders an <a>/<Link> automatically when `to` or `href` is passed.
 */
const VARIANTS = {
  primary: 'bg-primary text-on-primary hover:bg-primary/90 disabled:bg-subtle',
  secondary: 'border-2 border-primary text-fg hover:bg-fill',
  subtle: 'bg-fill text-fg hover:bg-fill-strong',
  ghost: 'text-fg hover:bg-fill',
  // Reserved for sale / high-intent promo actions only.
  accent: 'bg-accent text-on-primary hover:bg-accent/90',
  // Destructive confirmations (cancel an order, remove an address).
  danger: 'bg-danger text-on-primary hover:bg-danger/90',
}

const SIZES = {
  sm: 'h-9 px-4 text-xs',
  md: 'h-11 px-6 text-sm',
  lg: 'h-14 px-8 text-sm',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  pill = false,
  full = false,
  className,
  to,
  href,
  children,
  ...props
}) {
  const classes = clsx(
    'inline-flex items-center justify-center gap-2 font-semibold tracking-[0.05em]',
    'transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
    pill ? 'rounded-full' : 'rounded-card',
    full && 'w-full',
    VARIANTS[variant],
    SIZES[size],
    className,
  )

  if (to) return <Link to={to} className={classes} {...props}>{children}</Link>
  if (href) return <a href={href} className={classes} {...props}>{children}</a>
  return <button className={classes} {...props}>{children}</button>
}
