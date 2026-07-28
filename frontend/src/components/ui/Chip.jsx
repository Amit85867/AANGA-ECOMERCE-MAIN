import clsx from 'clsx'

/*
 * Selection chips for sizes and colours (product detail, listing filters).
 *
 * <Chip selected>M</Chip>
 * <Chip color="#000000" selected aria-label="Charcoal Black" />
 */
export default function Chip({
  selected = false,
  disabled = false,
  color,
  className,
  children,
  ...props
}) {
  // Colour swatch: a filled circle with a ring when selected.
  if (color) {
    return (
      <button
        type="button"
        disabled={disabled}
        aria-pressed={selected}
        className={clsx(
          'w-8 h-8 rounded-full transition-all duration-200',
          'ring-offset-2 ring-offset-bg',
          selected ? 'ring-2 ring-primary' : 'ring-1 ring-hairline hover:ring-subtle',
          disabled && 'opacity-40 cursor-not-allowed',
          className,
        )}
        style={{ backgroundColor: color }}
        {...props}
      />
    )
  }

  return (
    <button
      type="button"
      disabled={disabled}
      aria-pressed={selected}
      className={clsx(
        'min-w-[3rem] h-11 px-4 rounded-card text-sm font-medium',
        'border transition-all duration-200',
        selected
          ? 'border-primary bg-fill text-fg'
          : 'border-hairline bg-card text-muted hover:border-subtle',
        disabled && 'opacity-40 cursor-not-allowed line-through',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
