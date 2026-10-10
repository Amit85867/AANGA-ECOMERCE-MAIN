import { useState } from 'react'
import apiClient from '@/services/apiClient'
import { useAuthStore } from '@/store/useAuthStore'
import { toast } from '@/components/ui/Toast'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import Seo from '@/components/Seo'

const MIN_PASSWORD = 8

export default function Profile() {
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)

  const [form, setForm] = useState({ full_name: user?.full_name || '', phone: user?.phone || '' })
  const [profileErrors, setProfileErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const [pwd, setPwd] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwdErrors, setPwdErrors] = useState({})
  const [changing, setChanging] = useState(false)

  // Accounts created with Google have no password to change.
  const hasPassword = !user?.auth_provider || user.auth_provider === 'email'

  const saveProfile = async (e) => {
    e.preventDefault()
    if (saving) return
    const errors = {}
    if (form.full_name.trim().length < 2) errors.full_name = 'Enter your name.'
    const phone = form.phone.replace(/[\s\-()]/g, '')
    if (phone && !/^\+?\d{10,15}$/.test(phone)) errors.phone = 'Enter a valid phone number, or leave it empty.'
    setProfileErrors(errors)
    if (Object.keys(errors).length) return

    setSaving(true)
    try {
      const { data } = await apiClient.put('/profile', {
        full_name: form.full_name.trim(), ...(phone ? { phone } : {}),
      })
      setUser(data)
      toast.success('Profile updated')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not update your profile')
    }
    setSaving(false)
  }

  const changePassword = async (e) => {
    e.preventDefault()
    if (changing) return
    const errors = {}
    if (!pwd.current_password) errors.current_password = 'Enter your current password.'
    if (pwd.new_password.length < MIN_PASSWORD) errors.new_password = `Use at least ${MIN_PASSWORD} characters.`
    else if (pwd.new_password === pwd.current_password) errors.new_password = 'Choose a password different from the current one.'
    if (pwd.confirm !== pwd.new_password) errors.confirm = 'The two passwords do not match.'
    setPwdErrors(errors)
    if (Object.keys(errors).length) return

    setChanging(true)
    try {
      await apiClient.put('/profile/password', {
        current_password: pwd.current_password, new_password: pwd.new_password,
      })
      toast.success('Password changed')
      setPwd({ current_password: '', new_password: '', confirm: '' })
    } catch (err) {
      if (err.response?.status === 401) setPwdErrors({ current_password: 'That is not your current password.' })
      else toast.error(err.response?.data?.error || 'Could not change your password')
    }
    setChanging(false)
  }

  return (
    <>
      <Seo title="My Profile" noindex />
      <h1 className="display text-3xl text-fg">Profile</h1>
      <p className="mt-2 text-sm text-muted">Your details and sign-in.</p>

      <div className="mt-8 max-w-xl space-y-6">
        <Card className="p-6">
          <h2 className="display text-lg text-fg mb-5">Personal details</h2>
          <form onSubmit={saveProfile} className="space-y-4" noValidate>
            <Input
              label="Full name" name="profile-name" autoComplete="name" value={form.full_name}
              error={profileErrors.full_name}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
            />
            <Input
              label="Phone" name="profile-phone" type="tel" autoComplete="tel" value={form.phone}
              error={profileErrors.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
            />
            <Input
              label="Email" name="profile-email" value={user?.email || ''} disabled
              hint="Your email is your sign-in and cannot be changed here."
            />
            <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</Button>
          </form>
        </Card>

        <Card className="p-6">
          <h2 className="display text-lg text-fg mb-5">Password</h2>
          {hasPassword ? (
            <form onSubmit={changePassword} className="space-y-4" noValidate>
              <Input
                label="Current password" name="current-password" type="password" autoComplete="current-password"
                value={pwd.current_password} error={pwdErrors.current_password}
                onChange={(e) => setPwd((p) => ({ ...p, current_password: e.target.value }))}
              />
              <Input
                label="New password" name="new-password" type="password" autoComplete="new-password"
                value={pwd.new_password} error={pwdErrors.new_password}
                hint={`At least ${MIN_PASSWORD} characters.`}
                onChange={(e) => setPwd((p) => ({ ...p, new_password: e.target.value }))}
              />
              <Input
                label="Confirm new password" name="confirm-password" type="password" autoComplete="new-password"
                value={pwd.confirm} error={pwdErrors.confirm}
                onChange={(e) => setPwd((p) => ({ ...p, confirm: e.target.value }))}
              />
              <Button type="submit" variant="secondary" disabled={changing}>
                {changing ? 'Changing…' : 'Change password'}
              </Button>
            </form>
          ) : (
            <p className="text-sm text-muted">
              You sign in with {user.auth_provider === 'google' ? 'Google' : 'your phone'}, so there is no password to manage here.
            </p>
          )}
        </Card>
      </div>
    </>
  )
}
