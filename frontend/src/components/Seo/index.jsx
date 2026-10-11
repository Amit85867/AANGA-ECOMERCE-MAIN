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
import { useSettingsStore } from '@/store/useSettingsStore'

const SITE_NAME = 'AANGA'
const DEFAULT_TITLE = 'AANGA — Premium Fashion for Men, Women & Kids'
const DEFAULT_DESCRIPTION =
  'AANGA — premium fashion for men, women and kids. Discover curated ' +
  'clothing, accessories and more, with fast delivery across India.'

export default function Seo({
  title,
  description,
  image,
  type = 'website',
  canonical,
  jsonLd,
  noindex = false,
}) {
  // The owner's store name, default title, description and share image
  // (Admin → Store settings), falling back to the built-in ones.
  const settings = useSettingsStore((st) => st.settings)
  const siteName = settings.store_name || SITE_NAME
  const fullTitle = title ? `${title} — ${siteName}` : settings.seo_title || DEFAULT_TITLE
  description = description || settings.seo_description || DEFAULT_DESCRIPTION
  image = image || settings.seo_share_image || undefined
  if (image && image.startsWith('/') && typeof window !== 'undefined') image = window.location.origin + image
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

      <meta property="og:site_name" content={siteName} />
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
