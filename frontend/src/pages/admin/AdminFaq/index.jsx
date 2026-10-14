import { useState } from 'react'
import { IconEdit, IconPlus, IconTrash } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { Badge, PageHeading } from '@/components/admin/controls'
import { confirm } from '@/components/admin/confirm'
import { inputCls, notifyError } from '@/components/admin/helpers'
import { Field, MoveButtons, Toggle } from '@/components/admin/kit'
import { btnGhost, btnPrimary, cardCls, fieldErrors, moveItem, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

const EMPTY = { question: '', answer: '', is_active: true }

export default function AdminFaq() {
  const { data, loading, error, reload, setData } = useLoad('/admin/faq')
  const [form, setForm] = useState(null)       // {id?, question, answer, is_active}
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const items = data?.items || []

  const save = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const body = { question: form.question, answer: form.answer, is_active: form.is_active }
      if (form.id) await adminApi.put(`/admin/faq/${form.id}`, body)
      else await adminApi.post('/admin/faq', body)
      toast.success(form.id ? 'Changes saved.' : 'Question added.')
      setForm(null)
      setErrors({})
      reload()
    } catch (err) {
      setErrors(fieldErrors(err))
      notifyError(err, 'Could not save this question.')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (item) => {
    if (!(await confirm({ title: 'Remove this question?', message: item.question, confirmLabel: 'Remove', danger: true }))) return
    try {
      await adminApi.delete(`/admin/faq/${item.id}`)
      toast.success('Removed.')
      reload()
    } catch (err) {
      notifyError(err, 'Could not remove this question.')
    }
  }

  const move = async (from, to) => {
    const next = moveItem(items, from, to)
    setData({ items: next })
    try {
      const { data: body } = await adminApi.put('/admin/faq/order', { ids: next.map((i) => i.id) })
      setData(body)
    } catch (err) {
      notifyError(err, 'Could not save the new order.')
      reload()
    }
  }

  return (
    <div>
      <PageHeading title="FAQ" subtitle="The questions and answers on the store’s FAQ page, in this order.">
        <button type="button" className={btnPrimary} onClick={() => { setForm(EMPTY); setErrors({}) }}><IconPlus size={18} /> Add question</button>
      </PageHeading>

      {form && (
        <form onSubmit={save} className={`${cardCls} mb-6 space-y-4`}>
          <h2 className="font-medium text-gray-900">{form.id ? 'Edit question' : 'New question'}</h2>
          <Field label="Question *" error={errors.question}>
            <input required maxLength={200} value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} className={inputCls} />
          </Field>
          <Field label="Answer *" error={errors.answer} help="Plain text. Press Enter for a new line.">
            <textarea required rows={4} maxLength={2000} value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} className={inputCls} />
          </Field>
          <Toggle label="Show on the FAQ page" checked={form.is_active} onChange={(on) => setForm({ ...form, is_active: on })} />
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Saving…' : form.id ? 'Save changes' : 'Add question'}</button>
            <button type="button" className={btnGhost} onClick={() => setForm(null)}>Cancel</button>
          </div>
        </form>
      )}

      {loading && !data ? <TableSkeleton rows={5} columns={2} /> : error ? <ErrorState message={error} onRetry={reload} /> : items.length === 0 ? (
        <EmptyState title="No questions yet" hint="Add the questions customers ask most. The FAQ page shows them in the order you set here." />
      ) : (
        <ol className="space-y-2">
          {items.map((item, index) => (
            <li key={item.id} className="flex items-start gap-3 rounded-xl border border-gray-200 bg-white p-4">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs text-gray-600">{index + 1}</span>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-gray-900">
                  {item.question}
                  {!item.is_active && <span className="ml-2"><Badge tone="gray">Hidden</Badge></span>}
                  {item.is_demo && <span className="ml-2"><Badge tone="purple">Demo</Badge></span>}
                </div>
                <p className="mt-1 whitespace-pre-line text-sm text-gray-600">{item.answer}</p>
              </div>
              <div className="flex shrink-0 items-center">
                <MoveButtons index={index} count={items.length} onMove={move} label={item.question} />
                <button type="button" onClick={() => { setForm(item); setErrors({}) }} aria-label={`Edit: ${item.question}`} title="Edit" className="rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-900"><IconEdit size={16} /></button>
                <button type="button" onClick={() => remove(item)} aria-label={`Remove: ${item.question}`} title="Remove" className="rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600"><IconTrash size={16} /></button>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
