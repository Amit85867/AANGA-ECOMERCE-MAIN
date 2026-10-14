import { useState } from 'react'
import { IconTrash } from '@tabler/icons-react'
import adminApi, { isDemoMode, setDemoMode } from '@/services/adminApi'
import { ErrorState, CardSkeleton } from '@/components/admin/DataState'
import { PageHeading } from '@/components/admin/controls'
import { humanize, inputCls, notifyError } from '@/components/admin/helpers'
import { Field, Toggle } from '@/components/admin/kit'
import { btnDanger, btnGhost, cardCls, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

export default function AdminDemo() {
  const { data, loading, error, reload } = useLoad('/admin/demo')
  const [demoMode, setMode] = useState(isDemoMode())
  const [asking, setAsking] = useState(false)
  const [typed, setTyped] = useState('')
  const [working, setWorking] = useState(false)
  const [result, setResult] = useState(null)

  const toggle = (on) => {
    setDemoMode(on)
    setMode(on)
    // The banner at the top of every admin page reads the same switch.
    window.dispatchEvent(new Event('aanga:demo-mode'))
    toast.success(on ? 'Demo mode is on: what you create now is tagged as demo.' : 'Demo mode is off.')
  }

  const remove = async (e) => {
    e.preventDefault()
    if (working) return
    setWorking(true)
    try {
      const { data: body } = await adminApi.post('/admin/demo/remove', { confirm: typed })
      setResult(body)
      setAsking(false)
      setTyped('')
      toast.success('Demo content removed.')
      reload()
    } catch (err) {
      notifyError(err, 'Could not remove the demo content.')
    } finally {
      setWorking(false)
    }
  }

  if (loading && !data) return <><PageHeading title="Demo content" /><CardSkeleton className="h-72" /></>
  if (error) return <><PageHeading title="Demo content" /><ErrorState message={error} onRetry={reload} /></>

  const kinds = Object.entries(data.counts).filter(([, n]) => n > 0)

  return (
    <div>
      <PageHeading title="Demo content" subtitle="Sample products, pages and customers that make the store look complete — and how to clear them out when you are ready to add your own." />

      <div className="grid gap-6 lg:grid-cols-2">
        <section className={cardCls}>
          <h2 className="mb-2 font-medium text-gray-900">What is tagged as demo ({data.total})</h2>
          {kinds.length === 0 ? <p className="text-sm text-gray-600">There is no demo content in the store.</p> : (
            <dl className="divide-y divide-gray-100 text-sm">
              {kinds.map(([kind, n]) => (
                <div key={kind} className="flex justify-between py-2">
                  <dt className="text-gray-600">{humanize(kind)}</dt>
                  <dd className="tabular-nums font-medium text-gray-900">{n}</dd>
                </div>
              ))}
            </dl>
          )}
          <p className="mt-3 text-xs text-gray-500">Demo items carry a purple “Demo” label wherever they are listed, so you can find and replace them one by one instead.</p>
        </section>

        <section className={cardCls}>
          <h2 className="mb-2 font-medium text-gray-900">Demo mode</h2>
          <Toggle
            label="Tag what I create as demo content" checked={demoMode} onChange={toggle}
            help="While this is on, everything you add in this browser tab — products, images, slides, coupons, pages — is marked as demo. Switch it off before adding your real products."
          />
        </section>

        <section className={`${cardCls} border-red-200 lg:col-span-2`}>
          <h2 className="mb-2 font-medium text-gray-900">Remove demo content</h2>
          <p className="text-sm text-gray-600">
            Deletes everything tagged as demo: products, categories, collections, campaigns, slides, banners, coupons, FAQ entries,
            demo page text, demo customers with their orders, demo staff and demo images. Your own content is not touched.
            A demo product that a real customer has ordered is switched off and kept, so the order stays intact. This cannot be undone.
          </p>

          {!asking ? (
            <button type="button" className={`${btnDanger} mt-4`} disabled={data.total === 0} onClick={() => { setAsking(true); setResult(null) }}>
              <IconTrash size={16} /> Remove demo content…
            </button>
          ) : (
            <form onSubmit={remove} className="mt-4 max-w-md rounded-lg border border-red-200 bg-red-50 p-4" role="alertdialog" aria-label="Confirm removing demo content">
              <p className="text-sm font-medium text-red-900">This deletes {data.total} demo item{data.total === 1 ? '' : 's'} for good.</p>
              <Field label={`Type ${data.confirm_phrase} to confirm`} className="mt-3">
                <input autoFocus value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" className={inputCls} />
              </Field>
              <div className="mt-3 flex gap-2">
                <button type="submit" disabled={working || typed !== data.confirm_phrase} className={btnDanger}>{working ? 'Removing…' : 'Remove it all'}</button>
                <button type="button" className={btnGhost} onClick={() => { setAsking(false); setTyped('') }}>Cancel</button>
              </div>
            </form>
          )}

          {result && (
            <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700" role="status">
              <p className="font-medium text-gray-900">Removed</p>
              <p className="mt-1">{Object.entries(result.removed).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${humanize(k).toLowerCase()}`).join(', ') || 'Nothing.'}</p>
              {result.kept.length > 0 && (
                <>
                  <p className="mt-3 font-medium text-gray-900">Kept</p>
                  <ul className="mt-1 list-disc pl-5">{result.kept.map((line) => <li key={line}>{line}</li>)}</ul>
                </>
              )}
            </div>
          )}
          <p className="mt-4 text-xs text-gray-500">A developer can do the same from the server with <code>flask remove-demo-content</code>.</p>
        </section>
      </div>
    </div>
  )
}
