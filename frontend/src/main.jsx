import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ErrorBoundary from '@/components/ErrorBoundary'
import { initMonitoring, reportError } from '@/services/monitoring'

initMonitoring()

// Failures outside React's render cycle (event handlers, timers, promises)
// never reach an error boundary; report those too.
window.addEventListener('unhandledrejection', (event) => {
  // An API call that answered with an error status is handled where it was
  // made (a toast, an inline message) and is not a crash.
  if (event.reason?.isAxiosError && event.reason.response) return
  reportError(event.reason instanceof Error ? event.reason : new Error(String(event.reason)))
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
