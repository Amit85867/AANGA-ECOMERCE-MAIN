import { Container, PageTitle } from '@/components/ui/Display'

/* Title and breadcrumb at the top of an inner page. */
export default function PageHeader({ title, subtitle, crumbs = [], className = '' }) {
  return (
    <Container className={className}>
      <PageTitle title={title} subtitle={subtitle} crumbs={crumbs.length ? crumbs : undefined} />
    </Container>
  )
}
