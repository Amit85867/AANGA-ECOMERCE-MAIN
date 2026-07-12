import { useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconBrandGoogle, IconDeviceMobile, IconMail } from '@tabler/icons-react'
import { toast } from '@/components/ui/Toast'
import { useAuthStore } from '@/store/useAuthStore'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '778737068060-9fouqvi51r4visk5k4rku656fjakunq0.apps.googleusercontent.com'

const TABS = [
  { id: 'phone', label: 'Phone', icon: IconDeviceMobile },
  { id: 'email', label: 'Email', icon: IconMail },
]

function loadGoogleScript() {
  return new Promise((resolve) => {
    if (window.google?.accounts) return resolve()
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.onload = resolve
    document.head.appendChild(script)
  })
}

export default function Login() {
  const navigate = useNavigate()
  const { login, googleAuth, sendOTP, verifyOTP, loading, error, clearError } = useAuthStore()

  const [tab, setTab] = useState('phone')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)

  const [phone, setPhone] = useState('+91')
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [devOtp, setDevOtp] = useState('')

  const handleTabChange = (t) => {
    setTab(t)
    clearError()
  }

  const handleEmailLogin = async (e) => {
    e.preventDefault()
    try {
      await login({ email, password })
      toast.success('Welcome back!')
      navigate('/')
    } catch {}
  }

  const handleSendOTP = async (e) => {
    e.preventDefault()
    if (phone.length !== 13) {
      toast.error('Enter a valid 10-digit mobile number')
      return
    }
    try {
      const res = await sendOTP(phone)
      setOtpSent(true)
      if (res.dev_otp) setDevOtp(res.dev_otp)
      toast.success('OTP sent to ' + phone)
    } catch {}
  }

  const handleVerifyOTP = async (e) => {
    e.preventDefault()
    try {
      await verifyOTP({ phone, code: otp })
      toast.success('Login successful!')
      navigate('/')
    } catch {}
  }

  const handleGoogleLogin = useCallback(async () => {
    try {
      await loadGoogleScript()
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile',
        callback: async (response) => {
          if (response.access_token) {
            try {
              await googleAuth(response.access_token)
              toast.success('Welcome!')
              navigate('/')
            } catch {
              toast.error('Google sign-in failed')
            }
          }
        },
      })
      client.requestAccessToken()
    } catch {
      toast.error('Could not load Google sign-in')
    }
  }, [googleAuth, navigate])

  return (
    <div className="bg-white p-8 md:p-10 max-w-[440px] w-full shadow-[0_4px_40px_rgba(0,0,0,0.06)]">
      <h1 className="font-serif text-2xl text-center font-bold">Welcome Back</h1>
      <p className="text-gray text-xs text-center mt-1">Sign in to your account to continue shopping</p>

      <button onClick={handleGoogleLogin} disabled={loading} className="w-full mt-6 flex items-center justify-center gap-2.5 py-3 border border-line text-sm font-medium hover:border-ink transition-colors disabled:opacity-50">
        <IconBrandGoogle size={18} /> Continue with Google
      </button>

      <div className="flex items-center gap-3 my-5">
        <div className="flex-1 h-px bg-line" />
        <span className="text-[10px] tracking-[2px] uppercase text-gray">or</span>
        <div className="flex-1 h-px bg-line" />
      </div>

      <div className="flex border border-line mb-5">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => handleTabChange(t.id)} className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${tab === t.id ? 'bg-ink text-white' : 'hover:bg-surface'}`}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {error && <div className="text-xs text-maroon-light bg-maroon/5 border border-maroon-light/20 px-3 py-2 mb-4">{error}</div>}

      {tab === 'phone' && !otpSent && (
        <form onSubmit={handleSendOTP} className="space-y-4">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Mobile Number</label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={13} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="+91 XXXXXXXXXX" />
          </div>
          <button type="submit" disabled={loading} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {loading ? 'Sending...' : 'Send OTP'}
          </button>
        </form>
      )}

      {tab === 'phone' && otpSent && (
        <form onSubmit={handleVerifyOTP} className="space-y-4">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Enter OTP sent to {phone}</label>
            <input type="text" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))} maxLength={6} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors tracking-[8px] text-center font-mono text-lg" placeholder="• • • • • •" />
            {devOtp && <p className="text-[11px] text-gold mt-1.5">Dev OTP: <span className="font-mono font-bold">{devOtp}</span></p>}
          </div>
          <button type="submit" disabled={loading} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {loading ? 'Verifying...' : 'Verify & Login'}
          </button>
          <button type="button" onClick={() => { setOtpSent(false); setOtp(''); setDevOtp(''); clearError() }} className="w-full text-xs text-gray hover:text-ink transition-colors">← Change number</button>
        </form>
      )}

      {tab === 'email' && (
        <form onSubmit={handleEmailLogin} className="space-y-4">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="you@example.com" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="••••••••" />
          </div>
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="accent-gold" /> Remember me
            </label>
            <Link to="/forgot-password" className="text-[11px] text-gold font-medium hover:underline">Forgot password?</Link>
          </div>
          <button type="submit" disabled={loading} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      )}

      <p className="text-center text-xs text-gray mt-5">
        Don't have an account? <Link to="/register" className="text-gold font-semibold hover:underline">Create one</Link>
      </p>
    </div>
  )
}
