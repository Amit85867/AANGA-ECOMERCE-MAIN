import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { IconArrowLeft, IconExternalLink } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { ErrorState, CardSkeleton, TableSkeleton } from '@/components/admin/DataState'
import { Badge, PageHeading } from '@/components/admin/controls'
import { formatDateTime, inputCls, notifyError } from '@/components/admin/helpers'
import { Field, ImageField, RichText } from '@/components/admin/kit'
import { btnGhost, btnPrimary, cardCls, fieldErrors, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

function PageList() {
  const { data, loading, error, reload } = useLoad('/admin/pages')
  return (
    <div>
      <PageHeading title="Pages" subtitle="The text of your information pages. The questions on the FAQ page are edited under FAQ." />
      {loading && !data ? <TableSkeleton rows={7} columns={3} /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <ul className="divide-y divide-gray-100">
            {data.pages.map((p) => (
              <li key={p.slug} className="flex flex-wrap items-center gap-3 px-6 py-4">
                <div className="min-w-0 flex-1">
                  <Link to={`/admin/pages/${p.slug}`} className="font-medium text-gray-900 hover:underline">{p.title}</Link>
                  <div className="text-xs text-gray-500">
                    {p.path}{p.updated_at && !p.is_empty ? ` · last saved ${formatDateTime(p.updated_at)}` : ''}
                  </div>
                </div>
                {p.is_demo && <Badge tone="purple">Demo text</Badge>}
                {p.is_empty
                  ? <Badge tone="amber">{['shipping', 'contact', 'faq'].includes(p.slug) ? 'No text yet' : 'Using the built-in text'}</Badge>
                  : <Badge tone="green">Written</Badge>}
                <Link to={`/admin/pages/${p.slug}`} className={`${btnGhost} px-3 py-1.5`}>Edit</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function PageEditor({ slug }) {
  const { data, loading, error, reload, setData } = useLoad(`/admin/pages/${slug}`)
  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (data) {
      setForm({
        title: data.title, body_html: data.body_html || '', meta_title: data.meta_title || '',
        meta_description: data.meta_description || '', share_image_url: data.share_image_url || '',
      })
    }
  }, [data])

  const save = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const { data: body } = await adminApi.put(`/admin/pages/${slug}`, {
        ...form, meta_title: form.meta_title || null, meta_description: form.meta_description || null,
        share_image_url: form.share_image_url || null,
      })
      setData(body)          // the cleaned-up text the server actually stored
      setErrors({})
      toast.success('Page saved.')
    } catch (err) {
      setErrors(fieldErrors(err))
      notifyError(err, 'Could not save this page.')
    } finally {
      setSaving(false)
    }
  }

  const back = (
    <Link to="/admin/pages" className="mb-3 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900">
      <IconArrowLeft size={16} /> All pages
    </Link>
  )
  if (loading && !data) return <>{back}<CardSkeleton className="h-96" /></>
  if (error) return <>{back}<ErrorState message={error} onRetry={reload} /></>
  if (!form) return null

  return (
    <form onSubmit={save}>
      {back}
      <PageHeading title={`Edit: ${data.title}`} subtitle={`Shown at ${data.path}`}>
        <a href={data.path} target="_blank" rel="noreferrer" className={btnGhost}><IconExternalLink size={16} /> View page</a>
        <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Saving…' : 'Save page'}</button>
      </PageHeading>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className={`${cardCls} space-y-4 xl:col-span-2`}>
          <Field label="Page title *" error={errors.title}>
            <input required maxLength={120} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inputCls} />
          </Field>
          <RichText
            label={slug === 'faq' || slug === 'contact' ? 'Introduction (optional, shown above the rest of the page)' : 'Page text'}
            value={form.body_html} onChange={(html) => setForm((f) => ({ ...f, body_html: html }))}
          />
          <p className="text-xs text-gray-500">
            Headings, bold, italics, lists and links are kept. Anything else — including pasted code — is removed when you save.
            {['about', 'returns', 'privacy', 'terms'].includes(slug) && ' Leave the text empty to go back to the built-in version of this page.'}
          </p>
        </div>

        <div className={`${cardCls} space-y-4 self-start`}>
          <h2 className="font-medium text-gray-900">Search and sharing</h2>
          <Field label="Title in search results" help="Up to 70 characters. Empty uses the page title." error={errors.meta_title}>
            <input maxLength={70} value={form.meta_title} onChange={(e) => setForm({ ...form, meta_title: e.target.value })} className={inputCls} />
          </Field>
          <Field label="Description in search results" help="Up to 200 characters." error={errors.meta_description}>
            <textarea rows={3} maxLength={200} value={form.meta_description} onChange={(e) => setForm({ ...form, meta_description: e.target.value })} className={inputCls} />
          </Field>
          <ImageField label="Image when the page is shared" value={form.share_image_url} error={errors.share_image_url} onChange={(url) => setForm({ ...form, share_image_url: url })} />
        </div>
      </div>
    </form>
  )
}

export default function AdminPages() {
  const { slug } = useParams()
  return slug ? <PageEditor key={slug} slug={slug} /> : <PageList />
}
