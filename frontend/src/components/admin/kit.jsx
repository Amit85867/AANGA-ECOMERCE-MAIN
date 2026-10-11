/* Small building blocks shared by the owner-dashboard screens. */
import { useEffect, useRef, useState } from 'react'
import {
  IconArrowDown, IconArrowUp, IconBold, IconH2, IconH3, IconItalic, IconLink, IconList,
  IconListNumbers, IconPhoto, IconUpload, IconX,
} from '@tabler/icons-react'
import { toast } from '@/components/ui/toastStore'
import { inputCls, notifyError } from '@/components/admin/helpers'
import { btnGhost, uploadImage, useLoad } from '@/components/admin/kitUtils'

/* A labelled field. The label wraps the control, so they are always tied. */
export function Field({ label, help, error, children, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-xs font-medium text-gray-600">{label}</span>
      {children}
      {help && !error && <span className="mt-1 block text-xs text-gray-500">{help}</span>}
      {error && <span role="alert" className="mt-1 block text-xs text-red-700">{error}</span>}
    </label>
  )
}

export function Toggle({ label, checked, onChange, help }) {
  return (
    <label className="flex items-start gap-3 py-1.5">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 h-4 w-4 rounded" />
      <span>
        <span className="block text-sm text-gray-800">{label}</span>
        {help && <span className="block text-xs text-gray-500">{help}</span>}
      </span>
    </label>
  )
}

/* Up / down buttons for reordering a list — works with a keyboard and on a phone. */
export function MoveButtons({ index, count, onMove, label }) {
  const cls = 'rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-900 disabled:opacity-30 disabled:hover:bg-transparent'
  return (
    <span className="inline-flex">
      <button type="button" className={cls} disabled={index === 0} onClick={() => onMove(index, index - 1)} aria-label={`Move ${label} up`} title="Move up">
        <IconArrowUp size={16} />
      </button>
      <button type="button" className={cls} disabled={index === count - 1} onClick={() => onMove(index, index + 1)} aria-label={`Move ${label} down`} title="Move down">
        <IconArrowDown size={16} />
      </button>
    </span>
  )
}

/* ── Images ─────────────────────────────────────────────────── */

/* Pick an image already in the media library. */
export function MediaPicker({ open, onClose, onPick }) {
  const [q, setQ] = useState('')
  const { data, loading } = useLoad(open ? '/admin/media' : null, { q, per_page: 48 })
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Choose an image">
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-xl bg-white">
        <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-4">
          <h2 className="flex-1 font-medium text-gray-900">Choose from the media library</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded p-1.5 text-gray-500 hover:bg-gray-100"><IconX size={18} /></button>
        </div>
        <div className="border-b border-gray-100 px-5 py-3">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by file name or description" aria-label="Search images" className={inputCls} />
        </div>
        <div className="overflow-y-auto p-5">
          {loading && <p className="text-sm text-gray-500">Loading…</p>}
          {!loading && (data?.assets || []).length === 0 && (
            <p className="text-sm text-gray-500">No images yet. Upload one from the field, or from Media library.</p>
          )}
          <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
            {(data?.assets || []).map((asset) => (
              <li key={asset.id}>
                <button
                  type="button" onClick={() => { onPick(asset); onClose() }}
                  className="block w-full overflow-hidden rounded-lg border border-gray-200 hover:border-gold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold"
                >
                  <img src={asset.url} alt={asset.alt_text || asset.filename || ''} loading="lazy" className="aspect-square w-full object-cover" />
                  <span className="block truncate px-2 py-1 text-left text-[11px] text-gray-500">{asset.filename}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

/* An image field: shows the picture, and lets the owner upload a new one or
   reuse one from the library. Every upload lands in the library. */
export function ImageField({ label, value, onChange, help, error }) {
  const [busy, setBusy] = useState(false)
  const [picking, setPicking] = useState(false)
  const input = useRef(null)

  const upload = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setBusy(true)
    try {
      const asset = await uploadImage(file)
      onChange(asset.url)
      toast.success('Image uploaded.')
    } catch (err) {
      notifyError(err, 'Could not upload this image.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <span className="mb-1 block text-xs font-medium text-gray-600">{label}</span>
      <div className="flex items-center gap-3">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-gray-200 bg-gray-50 text-gray-300">
          {value ? <img src={value} alt="" className="h-full w-full object-cover" /> : <IconPhoto size={22} />}
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btnGhost} disabled={busy} onClick={() => input.current?.click()}>
            <IconUpload size={16} /> {busy ? 'Uploading…' : 'Upload'}
          </button>
          <button type="button" className={btnGhost} onClick={() => setPicking(true)}>From library</button>
          {value && <button type="button" className={btnGhost} onClick={() => onChange('')}>Remove</button>}
        </div>
        <input ref={input} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="hidden" onChange={upload} aria-label={`Upload ${label}`} />
      </div>
      {help && !error && <span className="mt-1 block text-xs text-gray-500">{help}</span>}
      {error && <span role="alert" className="mt-1 block text-xs text-red-700">{error}</span>}
      <MediaPicker open={picking} onClose={() => setPicking(false)} onPick={(asset) => onChange(asset.url)} />
    </div>
  )
}

/* ── Rich text ──────────────────────────────────────────────────
   A small editor for page text: headings, bold, italic, lists, links. What
   it produces is sent to the server, which rebuilds it from an allow-list
   before storing it — the editor is a convenience, not the safety. */
export function RichText({ label, value, onChange }) {
  const ref = useRef(null)
  const last = useRef(null)

  // Only write into the box when the value came from outside (a load), never
  // while typing — that would throw the cursor to the start.
  useEffect(() => {
    if (ref.current && value !== last.current) {
      ref.current.innerHTML = value || ''
      last.current = value
    }
  }, [value])

  const emit = () => {
    last.current = ref.current.innerHTML
    onChange(last.current)
  }
  const run = (command, arg) => {
    ref.current?.focus()
    document.execCommand(command, false, arg)
    emit()
  }
  // The link address is typed into a small box in the toolbar. The selection
  // is remembered first, because clicking into that box would lose it.
  const [linkUrl, setLinkUrl] = useState(null)
  const saved = useRef(null)
  const startLink = () => {
    const selection = window.getSelection()
    saved.current = selection.rangeCount ? selection.getRangeAt(0).cloneRange() : null
    setLinkUrl('')
  }
  const applyLink = () => {
    const url = (linkUrl || '').trim()
    if (!/^(\/(?!\/)|https?:\/\/|mailto:|tel:)/i.test(url)) {
      toast.error('Use a page on this site (starting with /) or a full https:// link.')
      return
    }
    ref.current?.focus()
    if (saved.current) {
      const selection = window.getSelection()
      selection.removeAllRanges()
      selection.addRange(saved.current)
    }
    document.execCommand('createLink', false, url)
    emit()
    setLinkUrl(null)
  }
  // Paste as plain text: formatting copied from Word or a web page would only
  // be stripped by the server anyway.
  const paste = (e) => {
    e.preventDefault()
    document.execCommand('insertText', false, e.clipboardData.getData('text/plain'))
  }

  const tools = [
    [IconH2, 'Heading', () => run('formatBlock', 'h2')],
    [IconH3, 'Sub-heading', () => run('formatBlock', 'h3')],
    [null, 'Paragraph', () => run('formatBlock', 'p')],
    [IconBold, 'Bold', () => run('bold')],
    [IconItalic, 'Italic', () => run('italic')],
    [IconList, 'Bulleted list', () => run('insertUnorderedList')],
    [IconListNumbers, 'Numbered list', () => run('insertOrderedList')],
    [IconLink, 'Link', startLink],
  ]

  return (
    <div>
      <span id="richtext-label" className="mb-1 block text-xs font-medium text-gray-600">{label}</span>
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white focus-within:border-gold">
        <div role="toolbar" aria-label="Formatting" className="flex flex-wrap gap-1 border-b border-gray-100 bg-gray-50 px-2 py-1.5">
          {tools.map(([Icon, name, action]) => (
            <button
              key={name} type="button" title={name} aria-label={name}
              onMouseDown={(e) => e.preventDefault()} onClick={action}
              className="rounded px-2 py-1.5 text-xs text-gray-700 hover:bg-white hover:text-gray-900"
            >
              {Icon ? <Icon size={16} /> : 'Text'}
            </button>
          ))}
        </div>
        {linkUrl !== null && (
          <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 bg-gray-50 px-3 py-2">
            <input
              autoFocus value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} aria-label="Link address"
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); applyLink() } }}
              placeholder="/shop or https://…" className={`${inputCls} max-w-sm py-1.5`}
            />
            <button type="button" onClick={applyLink} className={btnGhost}>Add link</button>
            <button type="button" onClick={() => setLinkUrl(null)} className={btnGhost}>Cancel</button>
          </div>
        )}
        <div
          ref={ref} contentEditable suppressContentEditableWarning role="textbox" aria-multiline="true"
          aria-labelledby="richtext-label" onInput={emit} onBlur={emit} onPaste={paste}
          className="cms-prose min-h-[18rem] px-4 py-3 outline-none"
        />
      </div>
    </div>
  )
}
