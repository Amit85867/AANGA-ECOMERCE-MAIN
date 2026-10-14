/*
 * Error reporting (Sentry).
 *
 * Entirely off unless VITE_SENTRY_DSN is set at build time. When it is off the
 * Sentry SDK is never downloaded: it is loaded with a dynamic import, so the
 * storefront bundle carries none of it.
 */
const dsn = import.meta.env.VITE_SENTRY_DSN

let sentry = null
// Errors raised before the SDK finishes loading are held and sent once it has.
const pending = []

export function initMonitoring() {
  if (!dsn) return

  import('@sentry/react')
    .then((Sentry) => {
      Sentry.init({
        dsn,
        environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
        release: import.meta.env.VITE_APP_RELEASE || undefined,
        // Errors only. Tracing and session replay are separate, billable
        // products and are not switched on here.
        tracesSampleRate: 0,
        // Never attach who the visitor is: no IP-derived user, no cookies.
        sendDefaultPii: false,
        ignoreErrors: [
          // Browser noise that is not a fault in this app.
          'ResizeObserver loop limit exceeded',
          'ResizeObserver loop completed with undelivered notifications',
        ],
        beforeSend(event) {
          // A 4xx is the API saying "no" to a request, by design — a wrong
          // password is not a bug. Only unexpected failures are reported.
          const status = event.contexts?.response?.status_code
          if (status && status < 500) return null
          return event
        },
      })
      sentry = Sentry
      pending.splice(0).forEach(([error, context]) => reportError(error, context))
    })
    .catch(() => {
      // Blocked by an ad blocker or offline: the app must work regardless.
    })
}

export function reportError(error, context) {
  if (!dsn) return
  if (!sentry) {
    if (pending.length < 20) pending.push([error, context])
    return
  }
  sentry.captureException(error, context ? { extra: context } : undefined)
}
