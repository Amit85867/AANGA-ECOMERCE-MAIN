import { useState } from 'react'
import {
  IconCircleCheck, IconDiscount2, IconHeadset, IconPackages, IconTruckDelivery,
} from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import { Select } from '@/components/ui/Field'
import { Container, PageTitle } from '@/components/ui/Display'
import Seo from '@/components/Seo'

const FEATURES = [
  { icon: IconDiscount2, title: 'Bulk discounts', desc: 'Up to 40% off on orders of 50+ items' },
  { icon: IconTruckDelivery, title: 'Free shipping', desc: 'Free delivery on all wholesale orders' },
  { icon: IconHeadset, title: 'Dedicated support', desc: 'Priority assistance for wholesale partners' },
  { icon: IconPackages, title: 'Custom orders', desc: 'Sizes, colours and branding to order' },
]

const VOLUME_RANGES = [
  ['below_10k', 'Below ₹10,000 a month'],
  ['10k_50k', '₹10,000 – ₹50,000 a month'],
  ['50k_1lac', '₹50,000 – ₹1 lakh a month'],
  ['above_1lac', 'Above ₹1 lakh a month'],
]

const EMPTY = {
  owner_name: '', shop_name: '', email: '', phone: '', city: '', state: '', gst_number: '', monthly_volume_range: '',
}

function validate(form) {
  const errors = {}
  if (form.owner_name.trim().length < 2) errors.owner_name = 'Enter your name.'
  if (form.shop_name.trim().length < 2) errors.shop_name = 'Enter the shop or business name.'
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) errors.email = 'Enter a valid email address.'
  if (!/^\+?\d{10,15}$/.test(form.phone.replace(/[\s\-()]/g, ''))) errors.phone = 'Enter a valid phone number.'
  if (!form.city.trim()) errors.city = 'Enter the city.'
  if (!form.state.trim()) errors.state = 'Enter the state.'
  if (!form.monthly_volume_range) errors.monthly_volume_range = 'Choose an expected monthly volume.'
  return errors
}

export default function Wholesale() {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)

  const field = (name) => ({
    name: `wholesale-${name}`,
    value: form[name],
    error: errors[name],
    onChange: (e) => {
      setForm((f) => ({ ...f, [name]: e.target.value }))
      if (errors[name]) setErrors((er) => ({ ...er, [name]: undefined }))
    },
  })

  const submit = async (e) => {
    e.preventDefault()
    if (submitting) return
    const found = validate(form)
    setErrors(found)
    if (Object.keys(found).length) return

    setSubmitting(true)
    try {
      await apiClient.post('/wholesale', {
        ...form,
        owner_name: form.owner_name.trim(), shop_name: form.shop_name.trim(), email: form.email.trim(),
        phone: form.phone.replace(/[\s\-()]/g, ''), city: form.city.trim(), state: form.state.trim(),
        gst_number: form.gst_number.trim() || null,
      })
      setSent(true)
      setForm(EMPTY)
    } catch (err) {
      setErrors({
        form: err.response?.status === 429
          ? 'You have sent several inquiries recently. Please try again in a while.'
          : err.response?.data?.error || 'We could not submit your inquiry. Please try again.',
      })
    }
    setSubmitting(false)
  }

  return (
    <>
      <Seo title="Wholesale" description="Wholesale pricing for retailers and businesses — bulk discounts, free shipping and dedicated support." />
      <Container className="pb-20">
        <PageTitle
          title="Wholesale"
          subtitle="Stock AANGA in your shop. Tell us about your business and our team will be in touch with pricing."
          crumbs={[{ label: 'Home', to: '/' }, { label: 'Wholesale' }]}
        />

        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
          <div>
            <ul className="grid gap-4 sm:grid-cols-2">
              {FEATURES.map(({ icon: Icon, title, desc }) => (
                <li key={title} className="rounded-card bg-fill p-5">
                  <Icon size={24} stroke={1.5} className="text-fg" aria-hidden="true" />
                  <h2 className="mt-3 text-sm font-semibold text-fg">{title}</h2>
                  <p className="mt-1 text-sm text-muted">{desc}</p>
                </li>
              ))}
            </ul>
            <div className="mt-4 rounded-card bg-primary p-6 text-center text-on-primary">
              <p className="text-xs uppercase tracking-[0.1em] text-white/80">Minimum order</p>
              <p className="display mt-1 text-2xl">10 pieces</p>
              <p className="mt-1 text-sm text-white/80">Mix and match across categories</p>
            </div>
          </div>

          <Card className="p-6 sm:p-8">
            {sent ? (
              <div className="py-8 text-center" role="status">
                <IconCircleCheck size={44} stroke={1.25} className="mx-auto text-fg" aria-hidden="true" />
                <h2 className="display mt-4 text-xl text-fg">Inquiry received</h2>
                <p className="mt-2 text-sm text-muted">Thank you. Our wholesale team will contact you within two working days.</p>
                <Button variant="secondary" className="mt-6" onClick={() => setSent(false)}>Submit another</Button>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-4" noValidate>
                <h2 className="display text-xl text-fg">Tell us about your business</h2>
                {errors.form && (
                  <p role="alert" className="rounded-card bg-danger-soft px-4 py-3 text-sm text-danger">{errors.form}</p>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input label="Your name" autoComplete="name" {...field('owner_name')} />
                  <Input label="Shop or business name" autoComplete="organization" {...field('shop_name')} />
                  <Input label="Email" type="email" autoComplete="email" {...field('email')} />
                  <Input label="Phone" type="tel" autoComplete="tel" {...field('phone')} />
                  <Input label="City" autoComplete="address-level2" {...field('city')} />
                  <Input label="State" autoComplete="address-level1" {...field('state')} />
                </div>
                <Input label="GST number (optional)" {...field('gst_number')} />
                <Select label="Expected monthly volume" {...field('monthly_volume_range')}>
                  <option value="">Choose a range</option>
                  {VOLUME_RANGES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
                <Button type="submit" size="lg" disabled={submitting}>
                  {submitting ? 'Submitting…' : 'Submit inquiry'}
                </Button>
              </form>
            )}
          </Card>
        </div>
      </Container>
    </>
  )
}
