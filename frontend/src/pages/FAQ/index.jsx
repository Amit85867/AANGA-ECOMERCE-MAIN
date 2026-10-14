import { useEffect, useState } from 'react'
import { IconChevronDown } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import PageHeader from '@/components/ui/PageHeader'
import { Container, Skeleton } from '@/components/ui/Display'
import { CmsBody } from '@/components/common/CmsPage'
import Seo from '@/components/Seo'

/* Questions and answers are written by the owner under Admin → FAQ. */
export default function FAQ() {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(0)

  useEffect(() => {
    apiClient.get('/content/faq')
      .then((r) => setData(r.data))
      .catch(() => setData({ items: [], page: null }))
  }, [])

  const items = data?.items || []
  const page = data?.page
  const title = page?.title || 'Frequently Asked Questions'
  const jsonLd = items.length ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: items.map((f) => ({
      '@type': 'Question', name: f.question, acceptedAnswer: { '@type': 'Answer', text: f.answer },
    })),
  } : undefined

  return (
    <>
      <Seo title={page?.meta_title || title} description={page?.meta_description || undefined} jsonLd={jsonLd} />
      <PageHeader title={title} crumbs={[{ label: 'Home', to: '/' }, { label: 'FAQ' }]} />
      <Container className="pb-16">
        <div className="max-w-3xl">
          <CmsBody html={page?.body_html} className="mb-8" />
          {data === null ? (
            <div className="space-y-2" aria-busy="true">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}
            </div>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted">No questions have been added yet. Please contact us and we will be glad to help.</p>
          ) : (
            <div className="space-y-2">
              {items.map((f, i) => (
                <div key={f.id} className="border border-hairline/60">
                  <h2>
                    <button
                      type="button" onClick={() => setOpen(open === i ? -1 : i)}
                      aria-expanded={open === i} aria-controls={`faq-${f.id}`}
                      className="flex w-full items-center justify-between p-4 text-left"
                    >
                      <span className="pr-4 text-sm font-medium text-fg">{f.question}</span>
                      <IconChevronDown size={16} aria-hidden="true" className={`shrink-0 text-muted transition-transform duration-200 ${open === i ? 'rotate-180' : ''}`} />
                    </button>
                  </h2>
                  {open === i && (
                    <p id={`faq-${f.id}`} className="whitespace-pre-line px-4 pb-4 text-sm leading-relaxed text-muted">{f.answer}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Container>
    </>
  )
}
