import clsx from 'clsx'
import { useEffect, useId, useRef } from 'react'
import { IconX } from '@tabler/icons-react'

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/*
 * What every overlay needs to be usable without a mouse: focus moves in when
 * it opens and back to where it was when it closes, Tab cannot wander out to
 * the page behind, Escape closes it, and the page behind does not scroll.
 */
function useOverlay(open, onClose, panelRef) {
  useEffect(() => {
    if (!open) return undefined
    const previous = document.activeElement
    const panel = panelRef.current
    const first = panel?.querySelector('[data-autofocus]') || panel?.querySelector(FOCUSABLE)
    ;(first || panel)?.focus()

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panel) return
      const items = [...panel.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null)
      if (items.length === 0) return
      const [head, tail] = [items[0], items[items.length - 1]]
      if (e.shiftKey && document.activeElement === head) {
        e.preventDefault()
        tail.focus()
      } else if (!e.shiftKey && document.activeElement === tail) {
        e.preventDefault()
        head.focus()
      }
    }

    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = overflow
      document.removeEventListener('keydown', onKey)
      previous?.focus?.()
    }
    // onClose is intentionally not a dependency: a new function identity on
    // each render would re-run this and steal focus mid-typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, panelRef])
}

function Header({ titleId, title, onClose }) {
  return (
    <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4">
      <h2 id={titleId} className="display text-xl text-fg">{title}</h2>
      <button
        type="button" onClick={onClose} aria-label="Close"
        className="-m-2 p-2 rounded-full text-muted hover:bg-fill hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <IconX size={20} />
      </button>
    </div>
  )
}

/* Centred dialog. On phones it rises from the bottom as a sheet. */
export function Modal({ open, onClose, title, children, footer, size = 'md' }) {
  const panelRef = useRef(null)
  const titleId = useId()
  useOverlay(open, onClose, panelRef)
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[300] flex items-end sm:items-center justify-center bg-black/50 sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={panelRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
        className={clsx(
          'w-full bg-card shadow-lift outline-none flex flex-col max-h-[92vh]',
          'rounded-t-block sm:rounded-block',
          size === 'sm' && 'sm:max-w-md', size === 'md' && 'sm:max-w-lg', size === 'lg' && 'sm:max-w-2xl',
        )}
      >
        <Header titleId={titleId} title={title} onClose={onClose} />
        <div className="px-6 pb-6 overflow-y-auto">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-hairline/60 flex flex-wrap justify-end gap-3">{footer}</div>}
      </div>
    </div>
  )
}

/* Side panel — mobile filters and the like. */
export function Drawer({ open, onClose, title, children, footer, side = 'left' }) {
  const panelRef = useRef(null)
  const titleId = useId()
  useOverlay(open, onClose, panelRef)
  if (!open) return null

  return (
    <div
      className={clsx('fixed inset-0 z-[300] flex bg-black/50', side === 'right' && 'justify-end')}
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={panelRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
        className="w-[min(22rem,88vw)] h-full bg-card shadow-lift outline-none flex flex-col"
      >
        <Header titleId={titleId} title={title} onClose={onClose} />
        <div className="flex-1 px-6 pb-6 overflow-y-auto">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-hairline/60">{footer}</div>}
      </div>
    </div>
  )
}
