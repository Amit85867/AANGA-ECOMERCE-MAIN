import { useState } from 'react'
import apiClient from '@/services/apiClient'
import { Container } from '@/components/ui/Display'
import { useSetting } from '@/store/useSettingsStore'

export default function Newsletter({ heading }) {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // The outcome is shown in place, next to the field it belongs to.
  const [result, setResult] = useState(null)   // { ok, message }
  const s = useSetting()

  const subscribe = async (e) => {
    e.preventDefault()
    if (submitting) return
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      setResult({ ok: false, message: 'Enter a valid email address.' })
      return
    }
    setSubmitting(true)
    try {
      const { data } = await apiClient.post('/newsletter/subscribe', { email: email.trim() })
      setResult({ ok: true, message: data.message === 'Already subscribed' ? 'You are already on the list.' : 'You are on the list. Thank you!' })
      setEmail('')
    } catch (err) {
      setResult({
        ok: false,
        message: err.response?.status === 429
          ? 'Too many attempts. Please try again later.'
          : err.response?.data?.error || 'We could not subscribe you. Please try again.',
      })
    }
    setSubmitting(false)
  }

  return (
    <section className="bg-primary py-14 text-on-primary lg:py-20" aria-labelledby="newsletter-heading">
      <Container className="max-w-2xl text-center">
        <h2 id="newsletter-heading" className="display text-3xl sm:text-4xl">{heading?.title || s('newsletter_heading', 'Stay in style')}</h2>
        <p className="mt-3 text-sm leading-relaxed text-white/80">
          {heading?.subtitle || s('newsletter_subheading', 'New arrivals and offers, a couple of times a month. No spam.')}
        </p>

        <form onSubmit={subscribe} className="mx-auto mt-7 flex max-w-md flex-col gap-3 sm:flex-row" noValidate>
          <label htmlFor="newsletter-email" className="sr-only">Email address</label>
          <input
            id="newsletter-email" type="email" autoComplete="email" value={email}
            onChange={(e) => { setEmail(e.target.value); setResult(null) }}
            placeholder="you@example.com"
            aria-describedby={result ? 'newsletter-result' : undefined}
            aria-invalid={result && !result.ok ? true : undefined}
            className="h-12 min-w-0 flex-1 rounded-full border border-white/30 bg-white/10 px-5 text-sm text-white outline-none placeholder:text-white/60 focus:border-white focus:ring-1 focus:ring-white"
          />
          <button
            type="submit" disabled={submitting}
            className="h-12 rounded-full bg-white px-7 text-sm font-semibold text-black transition-colors hover:bg-white/90 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black"
          >
            {submitting ? 'Subscribing…' : 'Subscribe'}
          </button>
        </form>
        <p id="newsletter-result" role="status" className={`mt-3 min-h-5 text-sm ${result?.ok ? 'text-white' : 'text-accent-soft'}`}>
          {result?.message}
        </p>
      </Container>
    </section>
  )
}
