import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { toast } from '@/components/ui/Toast'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Checkbox } from '@/components/ui/Field'
import GoogleButton from '@/components/auth/GoogleButton'
import { useAuthStore } from '@/store/useAuthStore'
import Seo from '@/components/Seo'

const MIN_PASSWORD = 8

// The same rules the API applies, checked before the request is sent.
function validate(form) {
  const errors = {}
  if (form.full_name.trim().length < 2) errors.full_name = 'Enter your name.'
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) errors.email = 'Enter a valid email address.'
  const phone = form.phone.replace(/[\s\-()]/g, '')
  if (phone && !/^\+?\d{10,15}$/.test(phone)) errors.phone = 'Enter a valid phone number, or leave it empty.'
  if (form.password.length < MIN_PASSWORD) errors.password = `Use at least ${MIN_PASSWORD} characters.`
  if (form.confirm !== form.password) errors.confirm = 'The two passwords do not match.'
  if (!form.agreed) errors.agreed = 'Please accept the terms to create an account.'
  return errors
}

export default function Register() {
  const navigate = useNavigate()
  const location = useLocation()
  const { register, loading, error, clearError, isAuthenticated } = useAuthStore()
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '', confirm: '', agreed: false,
  })
  const [errors, setErrors] = useState({})

  const destination = typeof location.state?.from === 'string' ? location.state.from : '/'

  useEffect(() => clearError, [clearError])

  if (isAuthenticated) return <Navigate to={destination} replace />

  const field = (name) => ({
    name,
    value: form[name],
    error: errors[name],
    onChange: (e) => {
      setForm((f) => ({ ...f, [name]: e.target.value }))
      if (errors[name]) setErrors((er) => ({ ...er, [name]: undefined }))
    },
  })

  const done = () => {
    toast.success('Your account is ready')
    navigate(destination, { replace: true })
  }

  const submit = async (e) => {
    e.preventDefault()
    if (loading) return
    const found = validate(form)
    setErrors(found)
    if (Object.keys(found).length) return
    const phone = form.phone.replace(/[\s\-()]/g, '')
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: phone || undefined,
        password: form.password,
      })
      done()
    } catch {
      // The store holds the message; it is shown above the form.
    }
  }

  return (
    <div className="w-full max-w-md rounded-block bg-card p-6 shadow-card sm:p-10">
      <Seo title="Create Account" noindex />
      <h1 className="display text-2xl text-fg sm:text-3xl">Create your account</h1>
      <p className="mt-2 text-sm text-muted">Track orders, save addresses and check out faster.</p>

      <div className="mt-8">
        <GoogleButton onSignedIn={done} />

        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && (
            <p role="alert" className="rounded-card bg-danger-soft px-4 py-3 text-sm text-danger">{error}</p>
          )}
          <Input label="Full name" autoComplete="name" {...field('full_name')} />
          <Input label="Email" type="email" autoComplete="email" placeholder="you@example.com" {...field('email')} />
          <Input label="Phone (optional)" type="tel" autoComplete="tel" hint="For delivery updates." {...field('phone')} />
          <Input
            label="Password" type="password" autoComplete="new-password"
            hint={`At least ${MIN_PASSWORD} characters.`} {...field('password')}
          />
          <Input label="Confirm password" type="password" autoComplete="new-password" {...field('confirm')} />

          <div>
            <Checkbox
              checked={form.agreed}
              onChange={(e) => {
                setForm((f) => ({ ...f, agreed: e.target.checked }))
                setErrors((er) => ({ ...er, agreed: undefined }))
              }}
              label={
                <span className="text-muted">
                  I agree to the{' '}
                  <Link to="/terms" target="_blank" className="font-medium text-fg underline underline-offset-2">Terms</Link>
                  {' '}and{' '}
                  <Link to="/privacy-policy" target="_blank" className="font-medium text-fg underline underline-offset-2">Privacy Policy</Link>
                </span>
              }
            />
            {errors.agreed && <p className="mt-1.5 text-xs text-danger">{errors.agreed}</p>}
          </div>

          <Button type="submit" size="lg" full disabled={loading}>
            {loading ? 'Creating your account…' : 'Create account'}
          </Button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{' '}
        <Link to="/login" state={location.state} className="font-medium text-fg underline underline-offset-2">Sign in</Link>
      </p>
      <p className="mt-2 text-center text-xs text-subtle">
        Buying for a shop? <Link to="/wholesale" className="underline underline-offset-2 hover:text-fg">Ask about wholesale</Link>
      </p>
    </div>
  )
}
