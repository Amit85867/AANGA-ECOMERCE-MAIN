/**
 * Per-page document metadata.
 *
 * React 19 hoists <title>, <meta> and <link> rendered anywhere in the tree into
 * <head>, so no helmet dependency is needed. The JSON-LD <script> stays inline
 * in the body, which search engines read fine.
 *
 * Usage:
 *   <Seo title="Silk Kurta" description="…" image={url} type="product" jsonLd={…} />
 */
const SITE_NAME = 'AANGA'
const DEFAULT_TITLE = 'AANGA — Premium Fashion for Men, Women & Kids'
const DEFAULT_DESCRIPTION =
  'AANGA — premium fashion for men, women and kids. Discover curated ' +
  'clothing, accessories and more, with fast delivery across India.'

export default function Seo({
  title,
  description = DEFAULT_DESCRIPTION,
  image,
  type = 'website',
  canonical,
  jsonLd,
  noindex = false,
}) {
  const fullTitle = title ? `${title} — ${SITE_NAME}` : DEFAULT_TITLE
  const url =
    canonical ||
    (typeof window !== 'undefined'
      ? window.location.origin + window.location.pathname
      : undefined)

  return (
    <>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      {noindex && <meta name="robots" content="noindex,nofollow" />}
      {url && <link rel="canonical" href={url} />}

      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:type" content={type} />
      {url && <meta property="og:url" content={url} />}
      {image && <meta property="og:image" content={image} />}

      <meta name="twitter:card" content={image ? 'summary_large_image' : 'summary'} />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      {image && <meta name="twitter:image" content={image} />}

      {jsonLd && (
        <script
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
    </>
  )
}
