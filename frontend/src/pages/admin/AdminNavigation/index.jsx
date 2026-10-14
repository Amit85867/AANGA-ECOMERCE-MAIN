import { useEffect, useState } from 'react'
import { IconPlus, IconTrash } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { ErrorState, CardSkeleton } from '@/components/admin/DataState'
import { PageHeading } from '@/components/admin/controls'
import { inputCls, notifyError } from '@/components/admin/helpers'
import { MoveButtons } from '@/components/admin/kit'
import { btnGhost, btnPrimary, cardCls, fieldErrors, moveItem, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

let nextKey = 1
const withKey = (link) => ({ ...link, _key: nextKey++ })

function LinkList({ title, hint, links, onChange, grouped }) {
  const update = (index, patch) => onChange(links.map((l, i) => (i === index ? { ...l, ...patch } : l)))
  const groups = [...new Set(links.map((l) => l.group_name).filter(Boolean))]
  return (
    <section className={cardCls} aria-label={title}>
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="font-medium text-gray-900">{title}</h2>
        <button
          type="button" className={`${btnGhost} px-3 py-1.5`}
          onClick={() => onChange([...links, withKey({ label: '', url: '/', group_name: grouped ? (groups[0] || 'Shop') : null, is_visible: true })])}
        >
          <IconPlus size={16} /> Add link
        </button>
      </div>
      <p className="mb-4 text-xs text-gray-500">{hint}</p>

      {links.length === 0 && <p className="text-sm text-gray-500">No links. Add one, or save to leave this menu empty.</p>}
      <ul className="space-y-2">
        {links.map((link, index) => (
          <li key={link._key} className="grid items-center gap-2 rounded-lg border border-gray-100 p-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto]">
            <div className={grouped ? 'grid grid-cols-2 gap-2' : ''}>
              {grouped && (
                <input
                  value={link.group_name || ''} list="footer-columns" maxLength={40} aria-label={`Column for link ${index + 1}`}
                  placeholder="Column" onChange={(e) => update(index, { group_name: e.target.value })} className={inputCls}
                />
              )}
              <input
                value={link.label} maxLength={40} aria-label={`Text of link ${index + 1}`} placeholder="Link text"
                onChange={(e) => update(index, { label: e.target.value })} className={inputCls}
              />
            </div>
            <input
              value={link.url} maxLength={300} aria-label={`Address of link ${index + 1}`} placeholder="/shop or https://…"
              onChange={(e) => update(index, { url: e.target.value })} className={inputCls}
            />
            <div className="flex items-center justify-end gap-1">
              <label className="flex items-center gap-1.5 px-2 text-xs text-gray-600">
                <input type="checkbox" checked={link.is_visible} onChange={(e) => update(index, { is_visible: e.target.checked })} className="rounded" />
                Show
              </label>
              <MoveButtons index={index} count={links.length} onMove={(from, to) => onChange(moveItem(links, from, to))} label={link.label || `link ${index + 1}`} />
              <button type="button" onClick={() => onChange(links.filter((_, i) => i !== index))} aria-label={`Remove ${link.label || `link ${index + 1}`}`} title="Remove" className="rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600">
                <IconTrash size={16} />
              </button>
            </div>
          </li>
        ))}
      </ul>
      {grouped && <datalist id="footer-columns">{groups.map((g) => <option key={g} value={g} />)}</datalist>}
    </section>
  )
}

export default function AdminNavigation() {
  const { data, loading, error, reload, setData } = useLoad('/admin/navigation')
  const [header, setHeader] = useState([])
  const [footer, setFooter] = useState([])
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!data) return
    setHeader(data.header.map(withKey))
    setFooter(data.footer.map(withKey))
    setDirty(false)
  }, [data])

  const save = async () => {
    if (saving) return
    const clean = (l) => ({ label: l.label.trim(), url: l.url.trim(), group_name: l.group_name || null, is_visible: l.is_visible })
    if ([...header, ...footer].some((l) => !l.label.trim() || !l.url.trim())) {
      toast.error('Every link needs its text and an address.')
      return
    }
    setSaving(true)
    try {
      const { data: body } = await adminApi.put('/admin/navigation', { header: header.map(clean), footer: footer.map(clean) })
      setData(body)
      toast.success('Menus saved.')
    } catch (err) {
      const found = fieldErrors(err)
      notifyError(err, found.footer || 'A link address is not valid. Use a page on this site (starting with /) or a full https:// link.')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !data) return <><PageHeading title="Menus" /><CardSkeleton className="h-96" /></>
  if (error) return <><PageHeading title="Menus" /><ErrorState message={error} onRetry={reload} /></>

  return (
    <div>
      <PageHeading title="Menus" subtitle="The links in the bar at the top of the store and in the footer.">
        <button type="button" onClick={save} disabled={saving || !dirty} className={btnPrimary}>{saving ? 'Saving…' : 'Save menus'}</button>
      </PageHeading>
      <div className="space-y-6">
        <LinkList
          title="Header menu" links={header} onChange={(l) => { setHeader(l); setDirty(true) }}
          hint="A link to a category — for example /shop?category=men — automatically shows that category’s sub-categories as a drop-down."
        />
        <LinkList
          title="Footer links" grouped links={footer} onChange={(l) => { setFooter(l); setDirty(true) }}
          hint="Links with the same column name appear together under that heading. The first three columns are shown."
        />
      </div>
    </div>
  )
}
