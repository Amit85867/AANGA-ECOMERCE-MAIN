import { Component } from 'react'
import { useRouteError } from 'react-router-dom'
import { IconAlertTriangle } from '@tabler/icons-react'
import { reportError } from '@/services/monitoring'

/*
 * Without a boundary, an exception while rendering unmounts the whole React
 * tree and the visitor is left looking at a blank white page with no way
 * forward. This catches it, reports it, and offers a way out.
 */
function Fallback({ notFound = false }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-6 py-16">
      <div className="max-w-md text-center" role="alert">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-line text-gold">
          <IconAlertTriangle size={26} stroke={1.5} />
        </div>
        <h1 className="font-serif text-2xl font-bold mt-5">
          {notFound ? 'Page not found' : 'Something went wrong'}
        </h1>
        <p className="text-sm text-gray mt-2 leading-[1.8]">
          {notFound
            ? 'The page you are looking for does not exist or has moved.'
            : 'This page hit an unexpected problem. It has been reported to us. Reloading usually fixes it.'}
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          {!notFound && (
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-6 py-3 bg-ink text-white text-xs tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors"
            >
              Reload page
            </button>
          )}
          {/* A plain link, not a router <Link>: after a crash the router's own
              state may be what is broken, so leave through a full navigation. */}
          <a
            href="/"
            className="px-6 py-3 border border-line text-xs tracking-[2px] uppercase font-bold hover:border-ink transition-colors"
          >
            Go to home
          </a>
        </div>
      </div>
    </div>
  )
}

export default class ErrorBoundary extends Component {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error, info) {
    reportError(error, { componentStack: info?.componentStack })
  }

  render() {
    return this.state.failed ? <Fallback /> : this.props.children
  }
}

/* For the router's `errorElement`: errors thrown inside a route. */
export function RouteError() {
  const error = useRouteError()
  const notFound = error?.status === 404
  if (!notFound) reportError(error instanceof Error ? error : new Error(String(error?.statusText || error)))
  return <Fallback notFound={notFound} />
}
