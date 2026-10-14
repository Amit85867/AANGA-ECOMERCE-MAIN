import { useEffect, useState } from 'react'
import { IconCircleCheck, IconClock, IconMail, IconMapPin, IconPhone } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import { Select, Textarea } from '@/components/ui/Field'
import { Container, PageTitle } from '@/components/ui/Display'
import Seo from '@/components/Seo'
import { CmsBody } from '@/components/common/CmsPage'
import { useSetting } from '@/store/useSettingsStore'

// Address, phone and email come from Admin → Store settings; anything the
// owner has left empty is simply not shown.
const contactInfo = (s) => [
  { icon: IconMapPin, title: 'Visit us', lines: s('store_address').split(/\n|,\s*/).map((l) => l.trim()).filter(Boolean) },
  { icon: IconPhone, title: 'Call us', lines: [s('store_phone')].filter(Boolean) },
  { icon: IconMail, title: 'Email us', lines: [s('store_email')].filter(Boolean) },
  { icon: IconClock, title: 'WhatsApp', lines: [s('whatsapp_number')].filter(Boolean) },
].filter((item) => item.lines.length > 0)

const SUBJECTS = [
  ['general', 'General inquiry'],
  ['order_support', 'Help with an order'],
  ['returns_refunds', 'Returns and refunds'],
  ['wholesale', 'Wholesale'],
  ['feedback', 'Feedback'],
  ['other', 'Something else'],
]

const EMPTY = { name: '', email: '', subject: 'general', message: '' }
const MIN_MESSAGE = 10

export default function Contact() {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const s = useSetting()
  const CONTACT_INFO = contactInfo(s)
  // Optional introduction written under Admin → Pages → Contact.
  const [intro, setIntro] = useState('')
  useEffect(() => {
    apiClient.get('/content/pages/contact').then(({ data }) => setIntro(data.body_html || '')).catch(() => {})
  }, [])

  const field = (name) => ({
    name: `contact-${name}`,
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
    const found = {}
    if (form.name.trim().length < 2) found.name = 'Enter your name.'
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) found.email = 'Enter a valid email address.'
    if (form.message.trim().length < MIN_MESSAGE) found.message = `Tell us a little more (at least ${MIN_MESSAGE} characters).`
    setErrors(found)
    if (Object.keys(found).length) return

    setSubmitting(true)
    try {
      await apiClient.post('/contact', {
        name: form.name.trim(), email: form.email.trim(), subject: form.subject, message: form.message.trim(),
      })
      setSent(true)
      setForm(EMPTY)
    } catch (err) {
      setErrors({
        form: err.response?.status === 429
          ? 'You have sent several messages recently. Please try again in a while.'
          : err.response?.data?.error || 'We could not send your message. Please try again.',
      })
    }
    setSubmitting(false)
  }

  return (
    <>
      <Seo title="Contact Us" description="Get in touch with AANGA — order help, returns, wholesale and feedback." />
      <Container className="pb-20">
        <PageTitle
          title="Contact us"
          subtitle="Questions about an order, a return or anything else — we usually reply within one working day."
          crumbs={[{ label: 'Home', to: '/' }, { label: 'Contact' }]}
        />

        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            {intro && <CmsBody html={intro} className="mb-6" />}
            {CONTACT_INFO.map(({ icon: Icon, title, lines }) => (
              <li key={title} className="flex gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-fill text-fg">
                  <Icon size={20} stroke={1.5} aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-fg">{title}</h2>
                  {lines.map((line) => <p key={line} className="text-sm text-muted">{line}</p>)}
                </div>
              </li>
            ))}
          </ul>

          <Card className="p-6 sm:p-8">
            {sent ? (
              <div className="py-8 text-center" role="status">
                <IconCircleCheck size={44} stroke={1.25} className="mx-auto text-fg" aria-hidden="true" />
                <h2 className="display mt-4 text-xl text-fg">Message sent</h2>
                <p className="mt-2 text-sm text-muted">Thank you. We will reply to your email as soon as we can.</p>
                <Button variant="secondary" className="mt-6" onClick={() => setSent(false)}>Send another message</Button>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-4" noValidate>
                <h2 className="display text-xl text-fg">Send us a message</h2>
                {errors.form && (
                  <p role="alert" className="rounded-card bg-danger-soft px-4 py-3 text-sm text-danger">{errors.form}</p>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input label="Your name" autoComplete="name" {...field('name')} />
                  <Input label="Email" type="email" autoComplete="email" {...field('email')} />
                </div>
                <Select label="What is it about?" {...field('subject')}>
                  {SUBJECTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
                <Textarea
                  label="Message" rows={5} maxLength={2000}
                  hint="If it is about an order, include the order number."
                  {...field('message')}
                />
                <Button type="submit" size="lg" disabled={submitting}>
                  {submitting ? 'Sending…' : 'Send message'}
                </Button>
              </form>
            )}
          </Card>
        </div>
      </Container>
    </>
  )
}
