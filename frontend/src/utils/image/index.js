/*
 * Product images are stored twice: the original, and a 480px-wide thumbnail
 * named "<name>_480.webp" next to it (see backend/app/services/storage.py —
 * the suffix is a contract between the two files).
 *
 * `responsive(url, sizes)` returns the props for an <img> that lets the browser
 * pick the small one for a product card and the large one for a detail view.
 * Images that are not ours (a pasted external URL) or that predate thumbnails
 * get no srcSet; if a thumbnail turns out to be missing, `onError` drops back
 * to the original so the picture still shows.
 */
const THUMB_WIDTH = 480
const FULL_WIDTH = 1400
const OURS = /\/[0-9a-f]{32}\.webp$/

export function thumbUrl(url) {
  return typeof url === 'string' && OURS.test(url) ? url.replace(/\.webp$/, `_${THUMB_WIDTH}.webp`) : null
}

export function responsive(url, sizes) {
  const thumb = thumbUrl(url)
  if (!thumb) return { src: url }
  return {
    src: url,
    srcSet: `${thumb} ${THUMB_WIDTH}w, ${url} ${FULL_WIDTH}w`,
    sizes,
    onError: (e) => {
      const img = e.currentTarget
      if (img.srcset) {
        img.removeAttribute('srcset')
        img.removeAttribute('sizes')
        img.src = url
      }
    },
  }
}
