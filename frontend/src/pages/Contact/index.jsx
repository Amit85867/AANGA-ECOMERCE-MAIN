import { useState } from 'react'
import { IconMapPin, IconPhone, IconMail, IconClock } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'

const INFO = [
  { icon: IconMapPin, title: 'Visit Us', lines: ['Amit Enterprises', 'Boring Road, Patna', 'Bihar — 800001'] },
  { icon: IconPhone, title: 'Call Us', lines: ['+91 98765 43210', '+91 61200 00000'] },
  { icon: IconMail, title: 'Email Us', lines: ['support@aanga.in', 'wholesale@aanga.in'] },
  { icon: IconClock, title: 'Working Hours', lines: ['Mon–Sat: 10 AM – 8 PM', 'Sunday: Closed'] },
]

const SUBJECTS = [
  { value: 'general', label: 'General Inquiry' },
  { value: 'order_support', label: 'Order Support' },
  { value: 'wholesale', label: 'Wholesale' },
  { value: 'returns_refunds', label: 'Returns & Refunds' },
  { value: 'feedback', label: 'Feedback' },
  { value: 'other', label: 'Other' },
]

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', subject: 'general', message: '' })
  const [submitting, setSubmitting] = useState(false)
  const update = (k, v) => setForm({ ...form, [k]: v })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.message.trim().length < 10) return toast.error('Message must be at least 10 characters')
    setSubmitting(true)
    try {
      await apiClient.post('/contact', form)
      toast.success('Message sent! We\'ll get back to you soon.')
      setForm({ name: '', email: '', subject: 'general', message: '' })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not send message')
    }
    setSubmitting(false)
  }

  return (
    <>
      <PageHeader title="Contact Us" crumbs={[{ label: 'Home', to: '/' }, { label: 'Contact' }]} />
      <section className="px-6 lg:px-12 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-10">
          {/* Info */}
          <div>
            <h2 className="font-serif text-2xl font-bold mb-2">Get in Touch</h2>
            <p className="text-[13px] text-gray leading-[1.8] mb-8">Have questions about orders, bulk pricing, or anything else? We'd love to hear from you.</p>
            <div className="space-y-6">
              {INFO.map((i) => (
                <div key={i.title} className="flex gap-4">
                  <div className="w-10 h-10 bg-cream flex items-center justify-center shrink-0"><i.icon size={18} className="text-gold" /></div>
                  <div>
                    <div className="font-semibold text-sm">{i.title}</div>
                    {i.lines.map((l) => <div key={l} className="text-xs text-gray mt-0.5">{l}</div>)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Form */}
          <div className="bg-surface p-6 lg:p-8">
            <h3 className="font-serif text-lg font-bold mb-5">Send a Message</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Name *</label>
                  <input type="text" required value={form.name} onChange={(e) => update('name', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="Your name" />
                </div>
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Email *</label>
                  <input type="email" required value={form.email} onChange={(e) => update('email', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="you@example.com" />
                </div>
              </div>
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Subject *</label>
                <select value={form.subject} onChange={(e) => update('subject', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white">
                  {SUBJECTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Message *</label>
                <textarea required value={form.message} onChange={(e) => update('message', e.target.value)} rows={5} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white resize-none" placeholder="Tell us more... (at least 10 characters)" />
              </div>
              <button type="submit" disabled={submitting} className="px-8 py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-60">{submitting ? 'Sending…' : 'Send Message'}</button>
            </form>
          </div>
        </div>
      </section>
    </>
  )
}
