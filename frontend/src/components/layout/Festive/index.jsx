import { useEffect, useState } from 'react'
import { useCampaign } from '@/store/useLayoutStore'
import { exitPreview } from '@/services/preview'

/*
 * The festive decoration layer.
 *
 * An overlay, never a theme change: the design tokens stay exactly as they
 * are. When a live campaign has decoration switched on, <html> gets
 * data-festive and three CSS variables (the accent preset the owner chose);
 * the few rules in index.css under [data-festive] use them for sale badges,
 * the countdown and the motifs below. Everything is CSS and inline SVG — no
 * images, no animation.
 */
export function FestiveLayer() {
  const campaign = useCampaign()
  const decoration = campaign?.decoration?.enabled ? campaign.decoration : null

  useEffect(() => {
    const root = document.documentElement
    if (!decoration) {
      delete root.dataset.festive
      return undefined
    }
    root.dataset.festive = decoration.preset
    root.style.setProperty('--festive-accent', decoration.accent)
    root.style.setProperty('--festive-on-accent', decoration.on_accent)
    root.style.setProperty('--festive-accent-text', decoration.accent_text)
    return () => {
      delete root.dataset.festive
      for (const name of ['--festive-accent', '--festive-on-accent', '--festive-accent-text']) {
        root.style.removeProperty(name)
      }
    }
  }, [decoration?.preset, decoration?.accent, decoration?.on_accent, decoration?.accent_text]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!campaign?.preview) return null
  return (
    <div className="fixed inset-x-0 bottom-0 z-[400] flex flex-wrap items-center justify-center gap-3 bg-black px-4 py-2.5 text-center text-xs text-white">
      <span>
        Preview of <strong className="font-semibold">{campaign.name}</strong> — only you can see this.
        Prices here are for show; checkout uses today’s prices.
      </span>
      <button type="button" onClick={exitPreview} className="rounded-full border border-white/50 px-3 py-1 font-medium hover:bg-white hover:text-black">
        Exit preview
      </button>
    </div>
  )
}

/* A scalloped line, drawn along the bottom edge of the announcement bar. It
   sits on top of the bar (absolute), so switching it on moves nothing. */
export function FestiveBorder() {
  return (
    <svg className="festive-only pointer-events-none absolute inset-x-0 -bottom-[5px] z-[1] h-[6px] w-full" aria-hidden="true" preserveAspectRatio="none">
      <defs>
        <pattern id="festive-scallop" width="16" height="6" patternUnits="userSpaceOnUse">
          <path d="M0 0 Q8 9 16 0 Z" fill="var(--festive-accent)" />
        </pattern>
      </defs>
      <rect width="100%" height="6" fill="url(#festive-scallop)" />
    </svg>
  )
}

/* A small rangoli quarter for a corner of the hero. Decorative only. */
export function FestiveCorner({ className = '' }) {
  return (
    <svg viewBox="0 0 64 64" className={`festive-only pointer-events-none absolute h-12 w-12 sm:h-16 sm:w-16 ${className}`} aria-hidden="true">
      <g fill="none" stroke="var(--festive-accent)" strokeWidth="2" strokeLinecap="round">
        <path d="M2 2h22M2 2v22" />
        <path d="M2 34a32 32 0 0 0 32-32" />
        <path d="M2 22A20 20 0 0 0 22 2" />
      </g>
      <g fill="var(--festive-accent)">
        <circle cx="24" cy="24" r="3" />
        <circle cx="36" cy="14" r="1.8" />
        <circle cx="14" cy="36" r="1.8" />
        <path d="M44 4l2.2 3.8L44 11.6 41.8 7.8zM4 44l3.8 2.2L4 48.4.2 46.2z" opacity=".9" />
      </g>
    </svg>
  )
}

const pad = (n) => String(n).padStart(2, '0')

function remaining(endsAt) {
  const ms = new Date(endsAt).getTime() - Date.now()
  if (ms <= 0) return null
  const total = Math.floor(ms / 1000)
  return { d: Math.floor(total / 86400), h: Math.floor(total / 3600) % 24, m: Math.floor(total / 60) % 60, s: total % 60 }
}

/* "Ends in 20d 04h 12m". Fixed-width digits so the line does not jitter. It
   changes once a minute; seconds are shown only in the last hour, when they
   matter — and never for visitors who ask for less motion. */
export function Countdown({ endsAt, className = '' }) {
  const calm = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const [left, setLeft] = useState(() => remaining(endsAt))
  const lastHour = Boolean(left) && left.d === 0 && left.h === 0 && !calm

  useEffect(() => {
    setLeft(remaining(endsAt))
    const id = setInterval(() => setLeft(remaining(endsAt)), lastHour ? 1000 : 30_000)
    return () => clearInterval(id)
  }, [endsAt, lastHour])

  if (!left) return null
  const text = `${left.d > 0 ? `${left.d}d ` : ''}${pad(left.h)}h ${pad(left.m)}m${lastHour ? ` ${pad(left.s)}s` : ''}`
  return (
    <span className={`festive-countdown inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 font-semibold normal-case tracking-normal tabular-nums ${className}`}>
      <span className="sr-only">Offer ends in </span>
      <span aria-hidden="true">Ends in</span>
      {/* The text keeps changing; screen readers get it once. */}
      <time dateTime={endsAt} aria-live="off">{text}</time>
    </span>
  )
}
