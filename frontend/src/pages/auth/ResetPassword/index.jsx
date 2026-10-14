import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { IconCircleCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Seo from '@/components/Seo'

const MIN_PASSWORD = 8

export default function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (submitting) return
    const found = {}
    if (password.length < MIN_PASSWORD) found.password = `Use at least ${MIN_PASSWORD} characters.`
    if (confirm !== password) found.confirm = 'The two passwords do not match.'
    setErrors(found)
    if (Object.keys(found).length) return

    setSubmitting(true)
    try {
      await apiClient.post('/auth/reset-password', { token, new_password: password })
      setDone(true)
    } catch (err) {
      setErrors({ form: err.response?.data?.error || 'We could not reset your password. Please try again.' })
    }
    setSubmitting(false)
  }

  const shell = (children) => (
    <div className="w-full max-w-md rounded-block bg-card p-6 shadow-card sm:p-10">
      <Seo title="Reset Password" noindex />
      {children}
    </div>
  )

  if (!token) {
    return shell(
      <div className="text-center">
        <h1 className="display text-2xl text-fg">This link is not valid</h1>
        <p className="mt-3 text-sm text-muted">The reset link is incomplete. Request a new one and use it within an hour.</p>
        <Button to="/forgot-password" className="mt-8">Request a new link</Button>
      </div>,
    )
  }

  if (done) {
    return shell(
      <div className="text-center" role="status">
        <IconCircleCheck size={44} stroke={1.25} className="mx-auto text-fg" aria-hidden="true" />
        <h1 className="display text-2xl text-fg mt-4">Password changed</h1>
        <p className="mt-3 text-sm text-muted">You can now sign in with your new password.</p>
        <Button to="/login" className="mt-8">Sign in</Button>
      </div>,
    )
  }

  return shell(
    <>
      <h1 className="display text-2xl text-fg sm:text-3xl">Choose a new password</h1>
      <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
        {errors.form && (
          <p role="alert" className="rounded-card bg-danger-soft px-4 py-3 text-sm text-danger">
            {errors.form}{' '}
            <Link to="/forgot-password" className="font-medium underline underline-offset-2">Request a new link</Link>
          </p>
        )}
        <Input
          label="New password" name="new-password" type="password" autoComplete="new-password"
          value={password} error={errors.password} hint={`At least ${MIN_PASSWORD} characters.`}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Input
          label="Confirm new password" name="confirm-password" type="password" autoComplete="new-password"
          value={confirm} error={errors.confirm} onChange={(e) => setConfirm(e.target.value)}
        />
        <Button type="submit" size="lg" full disabled={submitting}>
          {submitting ? 'Saving…' : 'Change password'}
        </Button>
      </form>
    </>,
  )
}
