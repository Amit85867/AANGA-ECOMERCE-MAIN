import { useState } from 'react'
import { IconCopy, IconKey, IconPlus, IconTrash } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { useAdminStore } from '@/store/useAdminStore'
import { ErrorState, TableSkeleton } from '@/components/admin/DataState'
import { Badge, PageHeading } from '@/components/admin/controls'
import { confirm } from '@/components/admin/confirm'
import { formatDateTime, inputCls, notifyError } from '@/components/admin/helpers'
import { Field } from '@/components/admin/kit'
import { btnGhost, btnPrimary, cardCls, fieldErrors, useLoad } from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

const ROLE_HELP = {
  master: 'Everything, including store settings, staff and demo content.',
  manager: 'Runs the shop: catalogue, orders, customers, content, collections, campaigns and coupons. No store settings or staff.',
  staff: 'Catalogue and orders only: products, categories, images, orders and returns.',
}
const ROLE_TONE = { master: 'amber', manager: 'blue', staff: 'gray' }
const EMPTY = { full_name: '', email: '', role: 'staff' }

export default function AdminStaff() {
  const me = useAdminStore((s) => s.admin)
  const { data, loading, error, reload } = useLoad('/admin/staff')
  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  // A one-time password is shown exactly once, right after it is created.
  const [secret, setSecret] = useState(null)

  const invite = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    setErrors({})
    try {
      const { data: body } = await adminApi.post('/admin/staff', form)
      setSecret({ email: body.staff.email, password: body.temporary_password })
      setForm(null)
      reload()
    } catch (err) {
      setErrors(fieldErrors(err))
      notifyError(err, 'Could not add this person.')
    } finally {
      setSaving(false)
    }
  }

  const patch = async (member, change, message) => {
    try {
      const { data: body } = await adminApi.patch(`/admin/staff/${member.id}`, change)
      if (body.temporary_password) setSecret({ email: member.email, password: body.temporary_password })
      else toast.success(message)
      reload()
    } catch (err) {
      notifyError(err, 'Could not save this change.')
      reload()
    }
  }

  const resetPassword = async (member) => {
    if (!(await confirm({
      title: `Reset the password for ${member.full_name}?`,
      message: 'Their current password stops working. You will be shown a new one-time password to pass on to them.',
      confirmLabel: 'Reset password',
    }))) return
    patch(member, { reset_password: true })
  }

  const remove = async (member) => {
    if (!(await confirm({
      title: `Remove ${member.full_name}?`,
      message: 'They will no longer be able to sign in. What they did stays in the audit log.',
      confirmLabel: 'Remove', danger: true,
    }))) return
    try {
      await adminApi.delete(`/admin/staff/${member.id}`)
      toast.success('Removed.')
      reload()
    } catch (err) {
      notifyError(err, 'Could not remove this person.')
    }
  }

  return (
    <div>
      <PageHeading title="Staff" subtitle="Who can sign in to this dashboard, and what each person can do.">
        <button type="button" className={btnPrimary} onClick={() => { setForm(EMPTY); setErrors({}) }}>
          <IconPlus size={18} /> Add staff member
        </button>
      </PageHeading>

      {secret && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-5" role="status">
          <p className="font-medium text-amber-900">One-time password for {secret.email}</p>
          <p className="mt-1 text-sm text-amber-900">
            Pass this on to them privately. It is shown only now and is not stored anywhere you can read it again.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <code className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm">{secret.password}</code>
            <button
              type="button" className={btnGhost}
              onClick={() => navigator.clipboard?.writeText(secret.password).then(() => toast.success('Copied.'))}
            >
              <IconCopy size={16} /> Copy
            </button>
            <button type="button" className={btnGhost} onClick={() => setSecret(null)}>I have saved it</button>
          </div>
        </div>
      )}

      {form && (
        <form onSubmit={invite} className={`${cardCls} mb-6`}>
          <h2 className="mb-4 font-medium text-gray-900">New staff member</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Full name *" error={errors.full_name}>
              <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className={inputCls} />
            </Field>
            <Field label="Email *" error={errors.email}>
              <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputCls} />
            </Field>
            <Field label="Role" error={errors.role} help={ROLE_HELP[form.role]}>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className={inputCls}>
                {(data?.roles || []).map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </Field>
          </div>
          <p className="mt-3 text-xs text-gray-500">A one-time password is created for you to pass on. No email is sent.</p>
          <div className="mt-4 flex gap-2">
            <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Adding…' : 'Add staff member'}</button>
            <button type="button" className={btnGhost} onClick={() => setForm(null)}>Cancel</button>
          </div>
        </form>
      )}

      {loading && !data ? <TableSkeleton rows={4} columns={5} /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-6 py-3 font-medium">Role</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Last sign-in</th>
                  <th className="px-6 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.staff.map((member) => {
                  const mine = member.id === me?.id
                  return (
                    <tr key={member.id} className="border-b border-gray-50 last:border-0">
                      <td className="px-6 py-3">
                        <div className="font-medium text-gray-900">
                          {member.full_name} {mine && <span className="text-xs font-normal text-gray-500">(you)</span>}
                          {member.is_demo && <span className="ml-2"><Badge tone="purple">Demo</Badge></span>}
                        </div>
                        <div className="text-xs text-gray-500">{member.email}</div>
                      </td>
                      <td className="px-6 py-3">
                        <select
                          value={member.role} aria-label={`Role of ${member.full_name}`}
                          onChange={(e) => patch(member, { role: e.target.value }, 'Role changed.')}
                          className={`${inputCls} w-auto py-1.5`}
                        >
                          {data.roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                        </select>
                      </td>
                      <td className="px-6 py-3">
                        <Badge tone={member.is_active ? 'green' : 'red'}>{member.is_active ? 'Active' : 'Deactivated'}</Badge>
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 text-gray-500">{member.last_login ? formatDateTime(member.last_login) : 'Never'}</td>
                      <td className="px-6 py-3">
                        <div className="flex justify-end gap-1">
                          <button
                            type="button" disabled={mine} className={`${btnGhost} px-3 py-1.5`}
                            onClick={() => patch(member, { is_active: !member.is_active }, member.is_active ? 'Deactivated.' : 'Reactivated.')}
                          >
                            {member.is_active ? 'Deactivate' : 'Reactivate'}
                          </button>
                          <button type="button" onClick={() => resetPassword(member)} aria-label={`Reset password for ${member.full_name}`} title="Reset password" className="rounded p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900">
                            <IconKey size={17} />
                          </button>
                          <button type="button" disabled={mine} onClick={() => remove(member)} aria-label={`Remove ${member.full_name}`} title="Remove" className="rounded p-2 text-gray-500 hover:bg-red-50 hover:text-red-600 disabled:opacity-30">
                            <IconTrash size={17} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {data.roles.map((r) => (
              <div key={r.value} className={cardCls}>
                <Badge tone={ROLE_TONE[r.value]}>{r.label}</Badge>
                <p className="mt-2 text-sm text-gray-600">{ROLE_HELP[r.value]}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
