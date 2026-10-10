import { useEffect, useState } from 'react'
import { IconLoader2, IconSearch, IconX } from '@tabler/icons-react'
import { inputCls } from '@/components/admin/helpers'

/* Small shared controls for admin pages. */

/*
 * Search box that reports the term after the user pauses, so typing "kurta"
 * is one request, not five.
 */
export function SearchInput({ value, onChange, placeholder = 'Search…', delay = 350, className = '' }) {
  const [text, setText] = useState(value ?? '')

  useEffect(() => setText(value ?? ''), [value])

  useEffect(() => {
    if (text === (value ?? '')) return undefined
    const timer = setTimeout(() => onChange(text.trim()), delay)
    return () => clearTimeout(timer)
  }, [text, value, onChange, delay])

  return (
    <div className={`relative ${className}`}>
      <IconSearch size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
      <input
        type="search"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className={`${inputCls} pl-9 pr-9 [&::-webkit-search-cancel-button]:hidden`}
      />
      {text && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => { setText(''); onChange('') }}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
        >
          <IconX size={14} />
        </button>
      )}
    </div>
  )
}

/* Submit button that cannot be pressed twice while a save is in flight. */
export function SaveButton({ saving, children, savingLabel = 'Saving…', className = '', ...props }) {
  return (
    <button
      type="submit"
      disabled={saving || props.disabled}
      aria-busy={saving}
      className={`inline-flex items-center justify-center gap-2 rounded-lg bg-[#C8963E] px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-[#b88534] disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      {...props}
    >
      {saving && <IconLoader2 size={16} className="animate-spin" />}
      {saving ? savingLabel : children}
    </button>
  )
}

export function PageHeading({ title, subtitle, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}

const BADGE_TONES = {
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  amber: 'bg-amber-100 text-amber-800',
  blue: 'bg-blue-100 text-blue-800',
  purple: 'bg-purple-100 text-purple-800',
  gray: 'bg-gray-100 text-gray-700',
}

export function Badge({ tone = 'gray', children }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${BADGE_TONES[tone] || BADGE_TONES.gray}`}>
      {children}
    </span>
  )
}
