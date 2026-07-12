import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { IconCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password.length < 8) return toast.error('Password must be at least 8 characters')
    if (password !== confirm) return toast.error('Passwords do not match')
    setSubmitting(true)
    try {
      await apiClient.post('/auth/reset-password', { token, new_password: password })
      setDone(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not reset password')
    }
    setSubmitting(false)
  }

  if (!token) {
    return (
      <div className="bg-white p-8 md:p-10 max-w-[440px] w-full shadow-[0_4px_40px_rgba(0,0,0,0.06)] text-center">
        <h1 className="font-serif text-2xl font-bold">Invalid Link</h1>
        <p className="text-gray text-sm mt-2">This reset link is missing or malformed.</p>
        <Link to="/forgot-password" className="inline-block mt-5 text-xs text-gold font-semibold hover:underline">Request a new link</Link>
      </div>
    )
  }

  if (done) {
    return (
      <div className="bg-white p-8 md:p-10 max-w-[440px] w-full shadow-[0_4px_40px_rgba(0,0,0,0.06)] text-center">
        <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto"><IconCheck size={26} className="text-green-600" /></div>
        <h1 className="font-serif text-2xl font-bold mt-4">Password Updated</h1>
        <p className="text-gray text-sm mt-2">Redirecting you to sign in…</p>
        <Link to="/login" className="inline-block mt-5 text-xs text-gold font-semibold hover:underline">Sign in now</Link>
      </div>
    )
  }

  return (
    <div className="bg-white p-8 md:p-10 max-w-[440px] w-full shadow-[0_4px_40px_rgba(0,0,0,0.06)]">
      <h1 className="font-serif text-2xl text-center font-bold">Set New Password</h1>
      <p className="text-gray text-xs text-center mt-1">Choose a strong password for your account</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">New Password</label>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="At least 8 characters" />
        </div>
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Confirm Password</label>
          <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="Re-enter password" />
        </div>
        <button type="submit" disabled={submitting} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
          {submitting ? 'Updating…' : 'Update Password'}
        </button>
      </form>
    </div>
  )
}
