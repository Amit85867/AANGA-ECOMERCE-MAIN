import { useState } from 'react'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Checkbox } from '@/components/ui/Field'

const EMPTY = { full_name: '', phone: '', line1: '', line2: '', city: '', state: '', pin_code: '', is_default: false }

// The same rules the API enforces, so a mistake is caught before the round trip.
function validate(form) {
  const errors = {}
  if (form.full_name.trim().length < 2) errors.full_name = 'Enter the recipient’s name.'
  if (!/^\+?\d{10,14}$/.test(form.phone.replace(/[\s\-()]/g, ''))) errors.phone = 'Enter a valid phone number.'
  if (form.line1.trim().length < 3) errors.line1 = 'Enter the house number and street.'
  if (form.city.trim().length < 2) errors.city = 'Enter the city.'
  if (form.state.trim().length < 2) errors.state = 'Enter the state.'
  if (!/^[1-9]\d{5}$/.test(form.pin_code)) errors.pin_code = 'Enter a valid 6-digit PIN code.'
  return errors
}

/*
 * Add or edit a delivery address. Pass `address` to edit it.
 * `onSaved(address)` receives the saved row; `onCancel` hides the form.
 */
export default function AddressForm({ address, onSaved, onCancel, forceDefault = false }) {
  const [form, setForm] = useState(() => ({ ...EMPTY, ...(address || {}), line2: address?.line2 || '' }))
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const field = (name, extra = {}) => ({
    name: `address-${name}`,
    value: form[name],
    error: errors[name],
    onChange: (e) => {
      setForm((f) => ({ ...f, [name]: e.target.value }))
      if (errors[name]) setErrors((er) => ({ ...er, [name]: undefined }))
    },
    ...extra,
  })

  const submit = async (e) => {
    e.preventDefault()
    if (saving) return
    const found = validate(form)
    setErrors(found)
    if (Object.keys(found).length) return

    const payload = {
      full_name: form.full_name.trim(), phone: form.phone.trim(),
      line1: form.line1.trim(), line2: form.line2.trim() || null,
      city: form.city.trim(), state: form.state.trim(), pin_code: form.pin_code,
      is_default: forceDefault || form.is_default,
    }
    setSaving(true)
    try {
      const { data } = address
        ? await apiClient.put(`/addresses/${address.id}`, payload)
        : await apiClient.post('/addresses', payload)
      toast.success(address ? 'Address updated' : 'Address saved')
      onSaved(data)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not save the address')
    }
    setSaving(false)
  }

  return (
    <form onSubmit={submit} noValidate className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Input label="Full name" autoComplete="name" {...field('full_name')} />
      <Input label="Phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="10-digit mobile number" {...field('phone')} />
      <div className="sm:col-span-2">
        <Input label="Address" autoComplete="address-line1" placeholder="House no., building, street" {...field('line1')} />
      </div>
      <div className="sm:col-span-2">
        <Input label="Landmark or apartment (optional)" autoComplete="address-line2" {...field('line2')} />
      </div>
      <Input label="City" autoComplete="address-level2" {...field('city')} />
      <Input label="State" autoComplete="address-level1" {...field('state')} />
      <Input
        label="PIN code" inputMode="numeric" autoComplete="postal-code" maxLength={6}
        {...field('pin_code', {
          onChange: (e) => {
            setForm((f) => ({ ...f, pin_code: e.target.value.replace(/\D/g, '').slice(0, 6) }))
            if (errors.pin_code) setErrors((er) => ({ ...er, pin_code: undefined }))
          },
        })}
      />
      {!forceDefault && !address?.is_default && (
        <div className="flex items-end pb-3">
          <Checkbox
            label="Make this my default address" checked={form.is_default}
            onChange={(e) => setForm((f) => ({ ...f, is_default: e.target.checked }))}
          />
        </div>
      )}
      <div className="sm:col-span-2 flex flex-wrap gap-3 pt-1">
        <Button type="submit" disabled={saving}>{saving ? 'Saving…' : address ? 'Save changes' : 'Save address'}</Button>
        {onCancel && <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  )
}
