// The "aanga-web" static site from render.yaml, for scripts/prod_local.sh.
//
// Serves the built storefront (frontend/dist) the way Render's static hosting
// does — compressed, hashed assets cached for a year, everything else falling
// back to index.html — and applies the same rewrites: /api/*, /sitemap.xml
// and /robots.txt go to the API. (/static/uploads/* goes there too, standing
// in for Supabase Storage, which this environment does not use.)
//
// No dependencies: plain Node.
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const DIST = path.resolve(process.env.DIST || 'dist')
const PORT = Number(process.env.PORT || 8080)
const API = new URL(process.env.API_ORIGIN || 'http://127.0.0.1:8000')
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
  '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json',
  '.ico': 'image/x-icon', '.txt': 'text/plain; charset=utf-8', '.woff2': 'font/woff2',
}
const REWRITTEN = (url) => url.startsWith('/api/') || url === '/sitemap.xml' || url === '/robots.txt' || url.startsWith('/static/')

function proxy(req, res) {
  // A proxy appends the address it received the request from; the API trusts
  // exactly one such entry (TRUSTED_PROXY_COUNT=1).
  const forwarded = [req.headers['x-forwarded-for'], req.socket.remoteAddress].filter(Boolean).join(', ')
  const upstream = http.request({
    host: API.hostname, port: API.port, path: req.url, method: req.method,
    // A new connection for each request. Reusing idle ones races with
    // gunicorn closing them (its keep-alive is 2 s): the request lands on a
    // socket that has just been shut and comes back as a 502.
    agent: false,
    headers: { ...req.headers, host: req.headers.host, 'x-forwarded-for': forwarded, 'x-forwarded-proto': 'http', 'x-forwarded-host': req.headers.host },
  }, (answer) => {
    const headers = { ...answer.headers }
    if (req.url.startsWith('/static/uploads/')) headers['cache-control'] = 'public, max-age=31536000, immutable'
    res.writeHead(answer.statusCode, headers)
    answer.pipe(res)
  })
  upstream.on('error', () => { res.writeHead(502, { 'content-type': 'application/json' }); res.end('{"error":"The API is not reachable."}') })
  req.pipe(upstream)
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0]
  if (REWRITTEN(url)) return proxy(req, res)

  let file = path.join(DIST, decodeURIComponent(url))
  if (!file.startsWith(DIST) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(DIST, 'index.html')
  const ext = path.extname(file)
  let body = fs.readFileSync(file)
  const headers = {
    'content-type': TYPES[ext] || 'application/octet-stream',
    'cache-control': url.startsWith('/assets/') ? 'public, max-age=31536000, immutable' : 'no-cache',
    'x-content-type-options': 'nosniff',
  }
  const accepts = req.headers['accept-encoding'] || ''
  if (['.html', '.js', '.css', '.svg', '.json', '.txt'].includes(ext)) {
    if (/\bbr\b/.test(accepts)) { body = zlib.brotliCompressSync(body); headers['content-encoding'] = 'br' }
    else if (/\bgzip\b/.test(accepts)) { body = zlib.gzipSync(body); headers['content-encoding'] = 'gzip' }
  }
  headers['content-length'] = body.length
  res.writeHead(200, headers)
  res.end(req.method === 'HEAD' ? undefined : body)
})
// Keep idle connections open longer than clients reuse them (as a hosting
// provider's edge does); Node's 5 s default drops a request that arrives just
// as the socket is being closed.
server.keepAliveTimeout = 75_000
server.headersTimeout = 80_000
server.listen(PORT, () => console.log(`storefront on :${PORT}, API at ${API.origin}`))
