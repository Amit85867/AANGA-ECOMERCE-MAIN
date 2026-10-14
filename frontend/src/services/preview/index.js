/*
 * Campaign preview.
 *
 * "Preview" in the admin opens the storefront with ?campaign_preview=<token>.
 * The token is kept for this browser tab only and sent with every API request,
 * and the server then answers as if that campaign were live — for display. The
 * cart and checkout ignore it, so a preview cannot buy at sale prices early.
 */
const KEY = 'aanga.campaignPreview'

let token = null
try {
  const url = new URL(window.location.href)
  const fromUrl = url.searchParams.get('campaign_preview')
  if (fromUrl) {
    sessionStorage.setItem(KEY, fromUrl)
    url.searchParams.delete('campaign_preview')
    window.history.replaceState(null, '', url.pathname + url.search + url.hash)
  }
  token = sessionStorage.getItem(KEY)
} catch {
  token = null
}

export const previewToken = () => token

export function exitPreview() {
  try { sessionStorage.removeItem(KEY) } catch { /* nothing to clear */ }
  window.location.assign('/')
}
