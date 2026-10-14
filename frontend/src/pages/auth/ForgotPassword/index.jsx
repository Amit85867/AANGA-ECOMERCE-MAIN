import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconMailCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Seo from '@/components/Seo'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  // Only ever present on a local development server.
  const [devLink, setDevLink] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    if (submitting) return
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      setError('Enter a valid email address.')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      const { data } = await apiClient.post('/auth/forgot-password', { email: email.trim() })
      setSent(true)
      if (data.dev_reset_link) setDevLink(data.dev_reset_link)
    } catch (err) {
      setError(
        err.response?.status === 429
          ? 'Too many requests. Please wait a while before trying again.'
          : err.response?.data?.error || 'Something went wrong. Please try again.',
      )
    }
    setSubmitting(false)
  }

  return (
    <div className="w-full max-w-md rounded-block bg-card p-6 shadow-card sm:p-10">
      <Seo title="Forgot Password" noindex />
      {sent ? (
        <div className="text-center" role="status">
          <IconMailCheck size={44} stroke={1.25} className="mx-auto text-fg" aria-hidden="true" />
          <h1 className="display text-2xl text-fg mt-4">Check your inbox</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            If an account exists for <span className="font-medium text-fg">{email.trim()}</span>, a link to reset
            the password is on its way. It works for one hour.
          </p>
          {devLink && (
            <p className="mt-5 break-all rounded-card bg-fill p-3 text-left text-xs text-muted">
              Development only: <a href={devLink} className="text-fg underline">{devLink}</a>
            </p>
          )}
          <Button to="/login" variant="secondary" className="mt-8">Back to sign in</Button>
        </div>
      ) : (
        <>
          <h1 className="display text-2xl text-fg sm:text-3xl">Reset your password</h1>
          <p className="mt-2 text-sm text-muted">Enter your email and we will send you a link to choose a new one.</p>
          <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
            <Input
              label="Email" name="email" type="email" autoComplete="email" value={email} error={error}
              onChange={(e) => { setEmail(e.target.value); setError('') }} placeholder="you@example.com"
            />
            <Button type="submit" size="lg" full disabled={submitting}>
              {submitting ? 'Sending…' : 'Send reset link'}
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-muted">
            Remembered it? <Link to="/login" className="font-medium text-fg underline underline-offset-2">Sign in</Link>
          </p>
        </>
      )}
    </div>
  )
}
