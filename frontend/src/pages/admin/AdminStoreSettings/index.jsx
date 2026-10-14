import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { ErrorState, CardSkeleton } from '@/components/admin/DataState'
import { PageHeading } from '@/components/admin/controls'
import { inputCls, notifyError } from '@/components/admin/helpers'
import { Field, ImageField, Toggle } from '@/components/admin/kit'
import { btnPrimary, cardCls, fieldErrors, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

const INPUT_TYPE = { email: 'email', phone: 'tel', url: 'url', money: 'number', int: 'number' }

export default function AdminStoreSettings() {
  const { data, loading, error, reload, setData } = useLoad('/admin/settings')
  const [values, setValues] = useState({})
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!data) return
    setValues(Object.fromEntries(data.groups.flatMap((g) => g.fields.map((f) => [f.key, f.value]))))
    setDirty(false)
  }, [data])

  const change = (key, value) => {
    setValues((v) => ({ ...v, [key]: value }))
    setErrors((e) => ({ ...e, [key]: undefined }))
    setDirty(true)
  }

  const save = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const { data: body } = await adminApi.put('/admin/settings', { values })
      setData(body)
      setErrors({})
      toast.success('Settings saved. The storefront is already using them.')
    } catch (err) {
      const found = fieldErrors(err)
      setErrors(found)
      notifyError(err, Object.keys(found).length ? 'Some fields need attention.' : 'Could not save the settings.')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !data) return <><PageHeading title="Store settings" /><CardSkeleton className="h-96" /></>
  if (error) return <><PageHeading title="Store settings" /><ErrorState message={error} onRetry={reload} /></>

  return (
    <form onSubmit={save}>
      <PageHeading title="Store settings" subtitle="Your store’s name, contact details, shipping and payment rules. Changes apply as soon as you save.">
        <button type="submit" disabled={saving || !dirty} className={btnPrimary}>{saving ? 'Saving…' : 'Save settings'}</button>
      </PageHeading>

      <div className="space-y-6">
        {data.groups.map((group) => (
          <section key={group.name} className={cardCls} aria-labelledby={`group-${group.name}`}>
            <h2 id={`group-${group.name}`} className="mb-4 font-medium text-gray-900">{group.name}</h2>
            <div className="grid gap-5 md:grid-cols-2">
              {group.fields.map((f) => {
                const value = values[f.key] ?? ''
                if (f.type === 'bool') {
                  return (
                    <div key={f.key}>
                      <Toggle label={f.label} help={f.help} checked={value === 'true'} onChange={(on) => change(f.key, on ? 'true' : 'false')} />
                      {errors[f.key] && <span role="alert" className="block text-xs text-red-700">{errors[f.key]}</span>}
                    </div>
                  )
                }
                if (f.type === 'image') {
                  return <ImageField key={f.key} label={f.label} help={f.help} error={errors[f.key]} value={value} onChange={(url) => change(f.key, url)} />
                }
                return (
                  <Field key={f.key} label={f.label} help={f.help} error={errors[f.key]} className={f.type === 'longtext' ? 'md:col-span-2' : ''}>
                    {f.type === 'longtext' ? (
                      <textarea rows={3} value={value} onChange={(e) => change(f.key, e.target.value)} className={inputCls} />
                    ) : (
                      <input
                        type={INPUT_TYPE[f.type] || 'text'} value={value} min={INPUT_TYPE[f.type] === 'number' ? 0 : undefined}
                        step={f.type === 'int' ? 1 : f.type === 'money' ? 'any' : undefined}
                        onChange={(e) => change(f.key, e.target.value)} className={inputCls}
                      />
                    )}
                  </Field>
                )
              })}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-6">
        <button type="submit" disabled={saving || !dirty} className={btnPrimary}>{saving ? 'Saving…' : 'Save settings'}</button>
      </div>
    </form>
  )
}
