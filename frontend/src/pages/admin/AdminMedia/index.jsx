import { useRef, useState } from 'react'
import { IconCopy, IconPhoto, IconTrash, IconUpload, IconX } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, CardSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { confirm } from '@/components/admin/confirm'
import { formatDate, inputCls, notifyError } from '@/components/admin/helpers'
import { Field } from '@/components/admin/kit'
import { btnDanger, btnGhost, btnPrimary, uploadImage, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

const kb = (bytes) => (bytes ? `${Math.max(1, Math.round(bytes / 1024))} KB` : '')

function Details({ asset, onClose, onChanged }) {
  const usage = useLoad(`/admin/media/${asset.id}/usage`)
  const [alt, setAlt] = useState(asset.alt_text || '')
  const [source, setSource] = useState(asset.source_note || '')
  const [saving, setSaving] = useState(false)
  const used = usage.data?.usage || []

  const save = async () => {
    setSaving(true)
    try {
      await adminApi.patch(`/admin/media/${asset.id}`, { alt_text: alt, source_note: source })
      toast.success('Saved.')
      onChanged()
    } catch (err) {
      notifyError(err, 'Could not save.')
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!(await confirm({ title: 'Delete this image?', message: 'The file is removed for good.', confirmLabel: 'Delete', danger: true }))) return
    try {
      await adminApi.delete(`/admin/media/${asset.id}`)
      toast.success('Image deleted.')
      onChanged()
      onClose()
    } catch (err) {
      notifyError(err, 'Could not delete this image.')
      usage.reload()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Image details">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white">
        <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-4">
          <h2 className="min-w-0 flex-1 truncate font-medium text-gray-900">{asset.filename || 'Image'}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded p-1.5 text-gray-500 hover:bg-gray-100"><IconX size={18} /></button>
        </div>
        <div className="grid gap-5 p-5 sm:grid-cols-[14rem_minmax(0,1fr)]">
          <div>
            <img src={asset.url} alt={asset.alt_text || ''} className="w-full rounded-lg border border-gray-200 object-contain" />
            <p className="mt-2 text-xs text-gray-500">
              {[asset.width && `${asset.width} × ${asset.height}px`, kb(asset.size_bytes), asset.created_at && formatDate(asset.created_at)].filter(Boolean).join(' · ')}
            </p>
            <button type="button" className={`${btnGhost} mt-2 w-full px-3 py-1.5`} onClick={() => navigator.clipboard?.writeText(asset.url).then(() => toast.success('Address copied.'))}>
              <IconCopy size={16} /> Copy image address
            </button>
          </div>
          <div className="space-y-4">
            <Field label="Description (alt text)" help="What the picture shows, for people who cannot see it.">
              <input maxLength={200} value={alt} onChange={(e) => setAlt(e.target.value)} className={inputCls} />
            </Field>
            <Field label="Source and licence" help="Where the picture came from, for your records.">
              <textarea rows={2} maxLength={500} value={source} onChange={(e) => setSource(e.target.value)} className={inputCls} />
            </Field>
            <button type="button" disabled={saving} onClick={save} className={btnPrimary}>{saving ? 'Saving…' : 'Save details'}</button>

            <div className="border-t border-gray-100 pt-4">
              <h3 className="text-sm font-medium text-gray-900">Where it is used</h3>
              {usage.loading ? <p className="mt-1 text-sm text-gray-500">Checking…</p> : used.length === 0 ? (
                <p className="mt-1 text-sm text-gray-500">Not used anywhere. It is safe to delete.</p>
              ) : (
                <ul className="mt-2 space-y-1 text-sm text-gray-700">
                  {used.map((u, i) => <li key={i}><span className="text-gray-500">{u.where}:</span> {u.name}</li>)}
                </ul>
              )}
              <button type="button" disabled={usage.loading || used.length > 0} onClick={remove} className={`${btnDanger} mt-3`}>
                <IconTrash size={16} /> Delete image
              </button>
              {used.length > 0 && <p className="mt-2 text-xs text-gray-500">Replace it in the places above first; then it can be deleted.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AdminMedia() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useLoad('/admin/media', { q, page, per_page: 24 })
  const [open, setOpen] = useState(null)
  const [busy, setBusy] = useState(false)
  const input = useRef(null)

  const upload = async (e) => {
    const files = [...(e.target.files || [])]
    e.target.value = ''
    if (!files.length) return
    setBusy(true)
    let done = 0
    for (const file of files) {
      try {
        await uploadImage(file)
        done += 1
      } catch (err) {
        notifyError(err, `Could not upload ${file.name}.`)
      }
    }
    setBusy(false)
    if (done) toast.success(`${done} image${done === 1 ? '' : 's'} uploaded.`)
    setPage(1)
    reload()
  }

  const assets = data?.assets || []

  return (
    <div>
      <PageHeading title="Media library" subtitle="Every image uploaded to the store. Upload once and reuse it anywhere a picture is asked for.">
        <button type="button" className={btnPrimary} disabled={busy} onClick={() => input.current?.click()}>
          <IconUpload size={18} /> {busy ? 'Uploading…' : 'Upload images'}
        </button>
        <input ref={input} type="file" multiple accept="image/png,image/jpeg,image/webp,image/gif" className="hidden" onChange={upload} aria-label="Upload images" />
      </PageHeading>

      <div className="mb-4 max-w-md">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1) }} placeholder="Search by file name, description or source" />
      </div>

      {loading && !data ? <CardSkeleton className="h-64" /> : error ? <ErrorState message={error} onRetry={reload} /> : assets.length === 0 ? (
        <EmptyState icon={IconPhoto} title={q ? 'No images match' : 'No images yet'} hint="JPG, PNG, WebP or GIF, up to 5 MB each. Pictures are resized automatically for phones and large screens." />
      ) : (
        <>
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6">
            {assets.map((asset) => (
              <li key={asset.id}>
                <button
                  type="button" onClick={() => setOpen(asset)}
                  className="block w-full overflow-hidden rounded-xl border border-gray-200 bg-white text-left hover:border-gold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold"
                >
                  <img src={asset.url} alt={asset.alt_text || asset.filename || ''} loading="lazy" className="aspect-square w-full bg-gray-50 object-cover" />
                  <span className="block px-3 py-2">
                    <span className="block truncate text-xs text-gray-800">{asset.filename || 'Image'}</span>
                    <span className="mt-1 flex flex-wrap items-center gap-1">
                      <Badge tone={asset.used_count ? 'green' : 'gray'}>{asset.used_count ? `Used in ${asset.used_count}` : 'Not used'}</Badge>
                      {asset.is_demo && <Badge tone="purple">Demo</Badge>}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} noun="images" />
        </>
      )}

      {open && <Details key={open.id} asset={open} onClose={() => setOpen(null)} onChanged={reload} />}
    </div>
  )
}
