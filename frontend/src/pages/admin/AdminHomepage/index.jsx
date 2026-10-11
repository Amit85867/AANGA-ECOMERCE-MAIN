import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconExternalLink, IconEye, IconEyeOff } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { ErrorState, CardSkeleton } from '@/components/admin/DataState'
import { PageHeading } from '@/components/admin/controls'
import { inputCls, notifyError } from '@/components/admin/helpers'
import { Field, MoveButtons } from '@/components/admin/kit'
import { btnGhost, btnPrimary, fieldErrors, moveItem, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

// Sections whose heading the storefront actually shows.
const HAS_HEADING = ['features', 'category_tiles', 'featured', 'testimonials', 'newsletter']

export default function AdminHomepage() {
  const { data, loading, error, reload, setData } = useLoad('/admin/homepage')
  const [sections, setSections] = useState([])
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!data) return
    setSections(data.sections.map((s) => ({ ...s, collection_id: s.config?.collection_id ?? null })))
    setDirty(false)
  }, [data])

  const update = (key, patch) => {
    setSections((list) => list.map((s) => (s.key === key ? { ...s, ...patch } : s)))
    setDirty(true)
  }
  const move = (from, to) => { setSections((list) => moveItem(list, from, to)); setDirty(true) }

  const save = async () => {
    if (saving) return
    setSaving(true)
    try {
      const { data: body } = await adminApi.put('/admin/homepage', {
        sections: sections.map((s) => ({
          key: s.key, is_visible: s.is_visible, title: s.title || null, subtitle: s.subtitle || null,
          ...(s.key === 'featured' ? { collection_id: s.collection_id || null } : {}),
        })),
      })
      setData(body)
      toast.success('Homepage saved. Open the store to see it.')
    } catch (err) {
      notifyError(err, Object.values(fieldErrors(err))[0] || 'Could not save the homepage.')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !data) return <><PageHeading title="Homepage" /><CardSkeleton className="h-96" /></>
  if (error) return <><PageHeading title="Homepage" /><ErrorState message={error} onRetry={reload} /></>

  return (
    <div>
      <PageHeading title="Homepage" subtitle="Choose which sections appear on the home page and in what order. The top of this list is the top of the page.">
        <a href="/" target="_blank" rel="noreferrer" className={btnGhost}><IconExternalLink size={16} /> View store</a>
        <button type="button" onClick={save} disabled={saving || !dirty} className={btnPrimary}>{saving ? 'Saving…' : 'Save homepage'}</button>
      </PageHeading>

      <ol className="space-y-3">
        {sections.map((s, index) => (
          <li key={s.key} className={`rounded-xl border bg-white p-4 sm:p-5 ${s.is_visible ? 'border-gray-200' : 'border-dashed border-gray-300 bg-gray-50'}`}>
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-medium text-gray-600">{index + 1}</span>
              <div className="min-w-0 flex-1">
                <div className={`font-medium ${s.is_visible ? 'text-gray-900' : 'text-gray-500'}`}>{s.label}</div>
                {!s.is_visible && <div className="text-xs text-gray-500">Hidden from the home page</div>}
              </div>
              {s.edit_url && (
                <Link to={s.edit_url} className="text-sm text-gray-600 underline underline-offset-2 hover:text-gray-900">Edit content</Link>
              )}
              <button
                type="button" onClick={() => update(s.key, { is_visible: !s.is_visible })}
                aria-pressed={s.is_visible} className={`${btnGhost} px-3 py-1.5`}
              >
                {s.is_visible ? <><IconEye size={16} /> Shown</> : <><IconEyeOff size={16} /> Hidden</>}
              </button>
              <MoveButtons index={index} count={sections.length} onMove={move} label={s.label} />
            </div>

            {s.is_visible && (HAS_HEADING.includes(s.key)) && (
              <div className="mt-4 grid gap-4 border-t border-gray-100 pt-4 sm:grid-cols-3">
                <Field label="Heading">
                  <input value={s.title || ''} maxLength={80} onChange={(e) => update(s.key, { title: e.target.value })} className={inputCls} />
                </Field>
                <Field label={s.key === 'newsletter' ? 'Line under the heading' : 'Small line above the heading'}>
                  <input value={s.subtitle || ''} maxLength={160} onChange={(e) => update(s.key, { subtitle: e.target.value })} className={inputCls} />
                </Field>
                {s.key === 'featured' && (
                  <Field label="Products to show" help="A collection you have made, or the products marked “featured”.">
                    <select value={s.collection_id || ''} onChange={(e) => update(s.key, { collection_id: e.target.value ? Number(e.target.value) : null })} className={inputCls}>
                      <option value="">Products marked “featured”</option>
                      {data.collections.map((c) => <option key={c.id} value={c.id}>{c.name}{c.is_active ? '' : ' (inactive)'}</option>)}
                    </select>
                  </Field>
                )}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}
