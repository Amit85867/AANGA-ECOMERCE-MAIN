import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAdminStore } from '@/store/useAdminStore'
import titleImg from '@/assets/images/logo-title.png'

export default function AdminLogin() {
  const { login, isAuthenticated } = useAdminStore()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (isAuthenticated) return <Navigate to="/admin" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/admin')
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center">
          <img src={titleImg} alt="AANGA" className="h-44 object-contain brightness-0 invert" />
          <p className="mt-3 text-sm text-white/40">Admin Dashboard</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl bg-white/5 p-8 backdrop-blur"
        >
          <h2 className="mb-6 text-lg font-medium text-white">Sign in</h2>

          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm text-white/60">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-[#C8963E]"
              placeholder="admin@aanga.in"
            />
          </label>

          <label className="mb-6 block">
            <span className="mb-1.5 block text-sm text-white/60">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-[#C8963E]"
              placeholder="Enter password"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#C8963E] py-3 text-sm font-semibold text-white transition-colors hover:bg-[#b88534] disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
