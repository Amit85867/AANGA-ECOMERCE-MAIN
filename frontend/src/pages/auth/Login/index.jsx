import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { toast } from '@/components/ui/Toast'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import GoogleButton from '@/components/auth/GoogleButton'
import { useAuthStore } from '@/store/useAuthStore'
import Seo from '@/components/Seo'

/*
 * Sign in with email, or Google when it is configured. Phone-OTP sign-in is
 * not offered: no SMS provider is connected, so a code could never arrive.
 */
export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, loading, error, clearError, isAuthenticated } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  // Go back to where the customer was heading (checkout, their orders…).
  const destination = typeof location.state?.from === 'string' ? location.state.from : '/'

  useEffect(() => clearError, [clearError])

  if (isAuthenticated) return <Navigate to={destination} replace />

  const done = () => {
    toast.success('Welcome back')
    navigate(destination, { replace: true })
  }

  const submit = async (e) => {
    e.preventDefault()
    if (loading) return
    try {
      await login({ email: email.trim(), password })
      done()
    } catch {
      // The store holds the message; it is shown above the form.
    }
  }

  return (
    <div className="w-full max-w-md rounded-block bg-card p-6 shadow-card sm:p-10">
      <Seo title="Sign In" noindex />
      <h1 className="display text-2xl text-fg sm:text-3xl">Sign in</h1>
      <p className="mt-2 text-sm text-muted">
        {destination === '/checkout' ? 'Sign in to finish checking out.' : 'Welcome back. Sign in to continue.'}
      </p>

      <div className="mt-8">
        <GoogleButton onSignedIn={done} />

        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && (
            <p role="alert" className="rounded-card bg-danger-soft px-4 py-3 text-sm text-danger">{error}</p>
          )}
          <Input
            label="Email" name="email" type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
          />
          <div>
            <Input
              label="Password" name="password" type="password" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)}
            />
            <div className="mt-2 text-right">
              <Link to="/forgot-password" className="text-xs font-medium text-muted underline underline-offset-2 hover:text-fg">
                Forgot your password?
              </Link>
            </div>
          </div>
          <Button type="submit" size="lg" full disabled={loading || !email || !password}>
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-muted">
        New to AANGA?{' '}
        <Link to="/register" state={location.state} className="font-medium text-fg underline underline-offset-2">
          Create an account
        </Link>
      </p>
    </div>
  )
}
