import { useState } from 'react'
import { IconTruckDelivery, IconDiscount2, IconHeadset, IconPackages } from '@tabler/icons-react'
import PageHeader from '@/components/ui/PageHeader'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'

const FEATURES = [
  { icon: IconDiscount2, title: 'Bulk Discounts', desc: 'Up to 40% off on orders of 50+ items' },
  { icon: IconTruckDelivery, title: 'Free Shipping', desc: 'Free delivery on all wholesale orders' },
  { icon: IconHeadset, title: 'Dedicated Support', desc: 'Priority assistance for wholesale partners' },
  { icon: IconPackages, title: 'Custom Orders', desc: 'Customize sizes, colors, and branding' },
]

const VOLUME_RANGES = [
  { value: 'below_10k', label: 'Below ₹10,000 / month' },
  { value: '10k_50k', label: '₹10,000 – ₹50,000 / month' },
  { value: '50k_1lac', label: '₹50,000 – ₹1 Lakh / month' },
  { value: 'above_1lac', label: 'Above ₹1 Lakh / month' },
]

export default function Wholesale() {
  const [form, setForm] = useState({ owner_name: '', shop_name: '', email: '', phone: '', city: '', state: '', gst_number: '', monthly_volume_range: '' })
  const [submitting, setSubmitting] = useState(false)
  const update = (k, v) => setForm({ ...form, [k]: v })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.monthly_volume_range) return toast.error('Please select your monthly volume')
    setSubmitting(true)
    try {
      await apiClient.post('/wholesale', form)
      toast.success('Inquiry submitted! Our team will reach out shortly.')
      setForm({ owner_name: '', shop_name: '', email: '', phone: '', city: '', state: '', gst_number: '', monthly_volume_range: '' })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not submit inquiry')
    }
    setSubmitting(false)
  }

  return (
    <>
      <PageHeader title="Wholesale Inquiry" crumbs={[{ label: 'Home', to: '/' }, { label: 'Wholesale' }]} />
      <section className="px-6 lg:px-12 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-10">
          {/* Left */}
          <div>
            <h2 className="font-serif text-2xl font-bold mb-2">Partner With AANGA</h2>
            <p className="text-[13px] text-gray leading-[1.8] mb-8">
              Join 200+ retailers and businesses who trust AANGA for quality wholesale fashion.
              We offer competitive pricing, flexible MOQs, and dedicated account management.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {FEATURES.map((f) => (
                <div key={f.title} className="bg-surface p-4">
                  <f.icon size={22} className="text-gold mb-2" />
                  <div className="font-semibold text-sm">{f.title}</div>
                  <div className="text-[11px] text-gray mt-0.5">{f.desc}</div>
                </div>
              ))}
            </div>
            <div className="mt-8 bg-ink p-5 text-center">
              <div className="text-[10px] tracking-[2px] text-gold uppercase font-semibold">Minimum Order</div>
              <div className="text-white font-serif text-2xl font-bold mt-1">10 Pieces</div>
              <div className="text-white/50 text-xs mt-1">Mix & match across categories</div>
            </div>
          </div>

          {/* Form */}
          <div className="bg-surface p-6 lg:p-8">
            <h3 className="font-serif text-lg font-bold mb-5">Submit Inquiry</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Your Name *</label>
                  <input type="text" required value={form.owner_name} onChange={(e) => update('owner_name', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="Full name" />
                </div>
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Business Name *</label>
                  <input type="text" required value={form.shop_name} onChange={(e) => update('shop_name', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="Company / Shop name" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Email *</label>
                  <input type="email" required value={form.email} onChange={(e) => update('email', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="you@business.com" />
                </div>
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Phone *</label>
                  <input type="tel" required value={form.phone} onChange={(e) => update('phone', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="10-digit mobile" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">City *</label>
                  <input type="text" required value={form.city} onChange={(e) => update('city', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="City" />
                </div>
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">State *</label>
                  <input type="text" required value={form.state} onChange={(e) => update('state', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="State" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">GST Number</label>
                  <input type="text" value={form.gst_number} onChange={(e) => update('gst_number', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white" placeholder="Optional" />
                </div>
                <div>
                  <label className="text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5">Monthly Volume *</label>
                  <select value={form.monthly_volume_range} onChange={(e) => update('monthly_volume_range', e.target.value)} className="w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors bg-white">
                    <option value="">Select range</option>
                    {VOLUME_RANGES.map((v) => <option key={v.value} value={v.value}>{v.label}</option>)}
                  </select>
                </div>
              </div>
              <button type="submit" disabled={submitting} className="px-8 py-3.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-60">{submitting ? 'Submitting…' : 'Submit Inquiry'}</button>
            </form>
          </div>
        </div>
      </section>
    </>
  )
}
