import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { PageHeading } from '@/components/admin/controls'
// The guide is one file, docs/OWNER_GUIDE.md, shown here as it is written.
import guide from '../../../../../docs/OWNER_GUIDE.md?raw'

const slug = (text) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

/* **bold**, `code` and [links](/admin/…) inside a line. Built as elements,
   never as HTML. */
function inline(text, keyBase) {
  const parts = []
  const pattern = /\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)/g
  let last = 0
  let match
  while ((match = pattern.exec(text))) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    const key = `${keyBase}-${match.index}`
    if (match[1]) parts.push(<strong key={key} className="font-semibold text-gray-900">{match[1]}</strong>)
    else if (match[2]) parts.push(<code key={key} className="rounded bg-gray-100 px-1.5 py-0.5 text-[0.85em]">{match[2]}</code>)
    else if (match[4].startsWith('/')) parts.push(<Link key={key} to={match[4]} className="text-gray-900 underline underline-offset-2">{match[3]}</Link>)
    else if (/^https?:\/\//.test(match[4])) parts.push(<a key={key} href={match[4]} target="_blank" rel="noreferrer" className="text-gray-900 underline underline-offset-2">{match[3]}</a>)
    else parts.push(match[3])
    last = pattern.lastIndex
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

/* Just enough Markdown for the guide: headings, paragraphs, numbered and
   bulleted lists, and "> " notes. */
function parse(markdown) {
  const blocks = []
  const lines = markdown.replace(/\r/g, '').split('\n')
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i += 1; continue }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line)
    if (heading) { blocks.push({ type: `h${heading[1].length}`, text: heading[2] }); i += 1; continue }
    const listMatch = /^(\d+\.|[-*])\s+/.exec(line)
    if (listMatch) {
      const ordered = /\d/.test(listMatch[1])
      const items = []
      while (i < lines.length && (/^(\d+\.|[-*])\s+/.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
        if (/^(\d+\.|[-*])\s+/.test(lines[i])) items.push(lines[i].replace(/^(\d+\.|[-*])\s+/, ''))
        else items[items.length - 1] += ` ${lines[i].trim()}`
        i += 1
      }
      blocks.push({ type: ordered ? 'ol' : 'ul', items })
      continue
    }
    if (line.startsWith('> ')) {
      const text = []
      while (i < lines.length && lines[i].startsWith('>')) { text.push(lines[i].replace(/^>\s?/, '')); i += 1 }
      blocks.push({ type: 'note', text: text.join(' ') })
      continue
    }
    const text = []
    while (i < lines.length && lines[i].trim() && !/^(#{1,3}\s|(\d+\.|[-*])\s|> )/.test(lines[i])) { text.push(lines[i].trim()); i += 1 }
    blocks.push({ type: 'p', text: text.join(' ') })
  }
  return blocks
}

export default function AdminHelp() {
  const blocks = useMemo(() => parse(guide), [])
  const title = blocks.find((b) => b.type === 'h1')?.text || 'Help'
  const sections = blocks.filter((b) => b.type === 'h2')

  return (
    <div>
      <PageHeading title={title} subtitle="How to do the everyday jobs in this dashboard, step by step." />
      <div className="grid gap-8 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <nav aria-label="In this guide" className="self-start rounded-xl border border-gray-200 bg-white p-4 lg:sticky lg:top-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">In this guide</p>
          <ul className="space-y-1 text-sm">
            {sections.map((s) => (
              <li key={s.text}><a href={`#${slug(s.text)}`} className="block rounded px-2 py-1 text-gray-700 hover:bg-gray-50 hover:text-gray-900">{s.text}</a></li>
            ))}
          </ul>
        </nav>

        <article className="max-w-3xl rounded-xl border border-gray-200 bg-white p-6 text-sm leading-relaxed text-gray-700 sm:p-8">
          {blocks.map((b, index) => {
            if (b.type === 'h1') return null
            if (b.type === 'h2') return <h2 key={index} id={slug(b.text)} className="mb-3 mt-10 scroll-mt-4 border-t border-gray-100 pt-8 text-xl font-semibold text-gray-900 first:mt-0 first:border-0 first:pt-0">{b.text}</h2>
            if (b.type === 'h3') return <h3 key={index} className="mb-2 mt-6 text-base font-semibold text-gray-900">{b.text}</h3>
            if (b.type === 'ol') return <ol key={index} className="mb-4 list-decimal space-y-1.5 pl-5">{b.items.map((item, n) => <li key={n}>{inline(item, `${index}-${n}`)}</li>)}</ol>
            if (b.type === 'ul') return <ul key={index} className="mb-4 list-disc space-y-1.5 pl-5">{b.items.map((item, n) => <li key={n}>{inline(item, `${index}-${n}`)}</li>)}</ul>
            if (b.type === 'note') return <p key={index} className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">{inline(b.text, index)}</p>
            return <p key={index} className="mb-4">{inline(b.text, index)}</p>
          })}
        </article>
      </div>
    </div>
  )
}
