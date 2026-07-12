import { useState } from 'react'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'
import { useSetting } from '@/store/useSettingsStore'

export default function Newsletter() {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const s = useSetting()

  const handleSubscribe = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setSubmitting(true)
    try {
      const { data } = await apiClient.post('/newsletter/subscribe', { email: email.trim() })
      toast.success(data.message || 'Subscribed successfully')
      setEmail('')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not subscribe')
    }
    setSubmitting(false)
  }

  return (
    <div className="bg-ink px-8 lg:px-12 py-14 text-center">
      <h2 className="font-serif text-4xl text-white font-bold">
        {(() => {
          const heading = s('newsletter_heading', 'Stay in Style')
          const parts = heading.split(' ')
          const last = parts.pop()
          return <>{parts.join(' ')} <span className="text-gold-light">{last}</span></>
        })()}
      </h2>
      <p className="text-[13px] text-white/50 mt-3 leading-[1.8]">
        {s('newsletter_subtitle', 'Get early access to new collections, exclusive deals, and seasonal lookbooks.')}
      </p>
      <form onSubmit={handleSubscribe} className="flex max-w-[460px] mx-auto mt-7">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email address"
          className="flex-1 px-5 py-3.5 bg-white/[0.08] border border-white/15 text-white text-[13px] outline-none placeholder:text-white/30"
        />
        <button type="submit" disabled={submitting} className="px-7 py-3.5 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold border-none cursor-pointer hover:bg-gold-light transition-colors disabled:opacity-60">
          {submitting ? '…' : 'Subscribe'}
        </button>
      </form>
    </div>
  )
}
