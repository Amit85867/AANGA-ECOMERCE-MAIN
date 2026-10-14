/*
 * Uploaded images are stored three times: the original (up to 1400px) and two
 * smaller copies named "<name>_480.webp" and "<name>_800.webp" next to it (see
 * backend/app/services/storage.py — the widths and suffix are a contract
 * between that file, this one, and the inline script in index.html).
 *
 * `responsive(url, sizes)` returns the props for an <img> that lets the browser
 * pick the smallest copy that is sharp enough for the slot. Images that are not
 * ours (a pasted external URL) get no srcSet; if a copy turns out to be missing,
 * `onError` drops back to the original so the picture still shows.
 */
const WIDTHS = [480, 800]
const FULL_WIDTH = 1400
const OURS = /\/[0-9a-f]{32}\.webp$/

export function srcSetFor(url) {
  if (typeof url !== 'string' || !OURS.test(url)) return null
  return [
    ...WIDTHS.map((w) => `${url.replace(/\.webp$/, `_${w}.webp`)} ${w}w`),
    `${url} ${FULL_WIDTH}w`,
  ].join(', ')
}

export function responsive(url, sizes) {
  const srcSet = srcSetFor(url)
  if (!srcSet) return { src: url }
  return {
    src: url,
    srcSet,
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

// One definition per slot, shared with index.html's early image loader.
export const SIZES = {
  card: '(min-width: 1280px) 300px, (min-width: 768px) 33vw, 50vw',
  gallery: '(min-width: 1024px) 320px, 100vw',
  hero: '(min-width: 1024px) 620px, 100vw',
}
