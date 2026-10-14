import { useEffect, useState } from 'react'
import apiClient from '@/services/apiClient'
import PageHeader from '@/components/ui/PageHeader'
import { Container, Skeleton } from '@/components/ui/Display'
import Seo from '@/components/Seo'

/* Loads one owner-written page (Admin → Pages). */
function useCmsPage(slug) {
  const [state, setState] = useState({ page: null, loading: true })
  useEffect(() => {
    let cancelled = false
    setState({ page: null, loading: true })
    apiClient.get(`/content/pages/${slug}`)
      .then(({ data }) => { if (!cancelled) setState({ page: data, loading: false }) })
      .catch(() => { if (!cancelled) setState({ page: null, loading: false }) })
    return () => { cancelled = true }
  }, [slug])
  return state
}

/* The text of a page. It was sanitised on the server when the owner saved it
   (backend/app/services/sanitize.py) — an allow-list of formatting tags, no
   scripts, no attributes other than a checked href — which is what makes
   rendering it as HTML safe here. */
export function CmsBody({ html, className = '' }) {
  if (!html) return null
  // eslint-disable-next-line react/no-danger
  return <div className={`cms-prose ${className}`} dangerouslySetInnerHTML={{ __html: html }} />
}

/*
 * A storefront page whose text the owner writes in the dashboard.
 * `fallback` is the built-in version, shown until the owner has written theirs.
 */
export default function CmsPage({ slug, fallback = null, crumb }) {
  const { page, loading } = useCmsPage(slug)

  if (loading) {
    return (
      <Container className="py-10" aria-busy="true">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="mt-8 h-64 max-w-3xl" />
      </Container>
    )
  }

  if (!page?.body_html) {
    if (fallback) return fallback
    return (
      <>
        <PageHeader title={page?.title || crumb} crumbs={[{ label: 'Home', to: '/' }, { label: crumb || page?.title }]} />
        <Container className="pb-16"><p className="text-sm text-muted">This page is being written. Please check back soon.</p></Container>
      </>
    )
  }

  return (
    <>
      <Seo title={page.meta_title || page.title} description={page.meta_description || undefined} image={page.share_image_url || undefined} />
      <PageHeader title={page.title} crumbs={[{ label: 'Home', to: '/' }, { label: crumb || page.title }]} />
      <Container className="pb-16">
        <CmsBody html={page.body_html} className="max-w-3xl" />
      </Container>
    </>
  )
}
