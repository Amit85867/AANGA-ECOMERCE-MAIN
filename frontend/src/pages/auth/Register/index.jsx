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

export default function Register() {
  const navigate = useNavigate()
  const { register, googleAuth, sendOTP, verifyOTP, loading, error, clearError } = useAuthStore()

  const [tab, setTab] = useState('phone')
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', confirm: '', type: 'retail' })
  const update = (k, v) => setForm({ ...form, [k]: v })

  const [mobilePhone, setMobilePhone] = useState('+91')
  const [mobileName, setMobileName] = useState('')
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [devOtp, setDevOtp] = useState('')
  const [agreed, setAgreed] = useState(false)

  const handleTabChange = (t) => {
    setTab(t)
    clearError()
  }

  const handleEmailRegister = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      toast.error('Passwords do not match')
      return
    }
    if (!agreed) {
      toast.error('Please agree to the Terms & Privacy Policy')
      return
    }
    try {
      await register({
        full_name: form.name,
        email: form.email,
        phone: form.phone || undefined,
        password: form.password,
        account_type: form.type,
      })
      toast.success('Account created successfully!')
      navigate('/')
    } catch {}
  }

  const handleSendOTP = async (e) => {
    e.preventDefault()
    if (mobilePhone.length !== 13) {
      toast.error('Enter a valid 10-digit mobile number')
      return
    }
    if (!mobileName.trim()) {
      toast.error('Please enter your name')
      return
    }
    try {
      const res = await sendOTP(mobilePhone)
      setOtpSent(true)
      if (res.dev_otp) setDevOtp(res.dev_otp)
      toast.success('OTP sent to ' + mobilePhone)
    } catch {}
  }

  const handleVerifyOTP = async (e) => {
    e.preventDefault()
    try {
      await verifyOTP({ phone: mobilePhone, code: otp, full_name: mobileName })
      toast.success('Account created!')
      navigate('/')
    } catch {}
  }

  const handleGoogleSignup = useCallback(async () => {
    try {
      await loadGoogleScript()
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile',
        callback: async (response) => {
          if (response.access_token) {
            try {
              await googleAuth(response.access_token)
              toast.success('Account created with Google!')
              navigate('/')
            } catch {
              toast.error('Google sign-up failed')
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
      <h1 className="font-serif text-2xl text-center font-bold">Create Account</h1>
      <p className="text-gray text-xs text-center mt-1">Join 50,000+ customers. Shop premium fashion.</p>

      <button onClick={handleGoogleSignup} disabled={loading} className="w-full mt-6 flex items-center justify-center gap-2.5 py-3 border border-line text-sm font-medium hover:border-ink transition-colors disabled:opacity-50">
        <IconBrandGoogle size={18} /> Sign up with Google
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
        <form onSubmit={handleSendOTP} className="space-y-3.5">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Full Name *</label>
            <input type="text" value={mobileName} onChange={(e) => setMobileName(e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="Your full name" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Mobile Number *</label>
            <input type="tel" value={mobilePhone} onChange={(e) => setMobilePhone(e.target.value)} maxLength={13} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="+91 XXXXXXXXXX" />
          </div>
          <button type="submit" disabled={loading} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {loading ? 'Sending...' : 'Send OTP'}
          </button>
        </form>
      )}

      {tab === 'phone' && otpSent && (
        <form onSubmit={handleVerifyOTP} className="space-y-4">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Enter OTP sent to {mobilePhone}</label>
            <input type="text" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))} maxLength={6} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors tracking-[8px] text-center font-mono text-lg" placeholder="• • • • • •" />
            {devOtp && <p className="text-[11px] text-gold mt-1.5">Dev OTP: <span className="font-mono font-bold">{devOtp}</span></p>}
          </div>
          <button type="submit" disabled={loading} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {loading ? 'Verifying...' : 'Verify & Create Account'}
          </button>
          <button type="button" onClick={() => { setOtpSent(false); setOtp(''); setDevOtp(''); clearError() }} className="w-full text-xs text-gray hover:text-ink transition-colors">← Change number</button>
        </form>
      )}

      {tab === 'email' && (
        <form onSubmit={handleEmailRegister} className="space-y-3.5">
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Full Name *</label>
            <input type="text" value={form.name} onChange={(e) => update('name', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="Your full name" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Email *</label>
            <input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="you@example.com" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Phone (Optional)</label>
            <input type="tel" value={form.phone} onChange={(e) => update('phone', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="+91 XXXXXXXXXX" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Password *</label>
            <input type="password" value={form.password} onChange={(e) => update('password', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="Min 8 characters" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Confirm Password *</label>
            <input type="password" value={form.confirm} onChange={(e) => update('confirm', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors" placeholder="Re-enter password" />
          </div>
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Account Type</label>
            <div className="flex gap-3">
              {['retail', 'wholesale'].map((t) => (
                <button key={t} type="button" onClick={() => update('type', t)} className={`flex-1 py-2.5 text-xs font-medium border transition-colors capitalize ${form.type === t ? 'border-gold bg-gold text-ink' : 'border-line hover:border-gold'}`}>{t === 'retail' ? 'Personal' : 'Business'}</button>
              ))}
            </div>
          </div>
          <label className="flex items-start gap-2 text-[11px] text-gray cursor-pointer pt-1">
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="accent-gold mt-0.5" /> I agree to the <Link to="/terms" className="text-gold">Terms</Link> and <Link to="/privacy-policy" className="text-gold">Privacy Policy</Link>
          </label>
          <button type="submit" disabled={loading} className="w-full py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50">
            {loading ? 'Creating...' : 'Create Account'}
          </button>
        </form>
      )}

      <p className="text-center text-xs text-gray mt-5">
        Already have an account? <Link to="/login" className="text-gold font-semibold hover:underline">Sign in</Link>
      </p>
    </div>
  )
}
