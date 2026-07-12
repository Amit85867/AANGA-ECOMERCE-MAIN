import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconMail } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const [devLink, setDevLink] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const { data } = await apiClient.post('/auth/forgot-password', { email: email.trim() })
      setSent(true)
      if (data.dev_reset_link) setDevLink(data.dev_reset_link)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Something went wrong')
    }
    setSubmitting(false)
  }

  return (
    <div className="bg-white p-8 md:p-10 max-w-[440px] w-full shadow-[0_4px_40px_rgba(0,0,0,0.06)]">
      <h1 className="font-serif text-2xl text-center font-bold">Forgot Password</h1>
      <p className="text-gray text-xs text-center mt-1">Enter your email and we'll send you a reset link</p>

      {sent ? (
        <div className="mt-6 text-center">
          <div className="w-14 h-14 rounded-full bg-cream flex items-center justify-center mx-auto"><IconMail size={26} className="text-gold" /></div>
          <p className="text-sm mt-4">If an account exists for <span className="font-semibold">{email}</span>, a reset link is on its way.</p>
          {devLink && (
            <div className="mt-4 text-left bg-surface p-3 text-[11px] break-all">
              <div className="text-gold font-semibold mb-1">Dev reset link:</div>
              <a href={devLink} className="text-ink underline">{devLink}</a>
            </div>
          )}
          <Link to="/login" className="inline-block mt-6 text-xs text-gold font-semibold hover:underline">← Back to sign in</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="you@example.com" />
          </div>
          <button type="submit" disabled={submitting} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {submitting ? 'Sending…' : 'Send Reset Link'}
          </button>
          <p className="text-center text-xs text-gray">
            Remembered it? <Link to="/login" className="text-gold font-semibold hover:underline">Sign in</Link>
          </p>
        </form>
      )}
    </div>
  )
}
