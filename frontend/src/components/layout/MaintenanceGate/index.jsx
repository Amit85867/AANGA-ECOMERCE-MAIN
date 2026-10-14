import { useEffect } from 'react'
import { IconTool } from '@tabler/icons-react'
import { useSettingsStore } from '@/store/useSettingsStore'
import logoMain from '@/assets/images/logo-main.webp'
import logoTitle from '@/assets/images/logo-title.webp'

const DEFAULT_MESSAGE =
  'We are making a few improvements and will be back shortly. Thank you for your patience.'

// How often the page checks whether the store has reopened.
const RECHECK_MS = 60_000

function MaintenancePage({ message, onRetry, checking }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-fill px-6 py-16 text-center">
      <div className="flex items-center gap-2">
        <img src={logoMain} alt="" width="44" height="44" className="h-11 w-11 object-contain" />
        <img src={logoTitle} alt="AANGA" width="36" height="36" className="h-9 w-9 object-contain" />
      </div>

      <div className="mt-12 flex h-16 w-16 items-center justify-center rounded-full bg-bg border border-hairline/60 text-fg">
        <IconTool size={28} stroke={1.5} />
      </div>
      <h1 className="display text-3xl font-bold mt-6">We’ll be right back</h1>
      <p className="text-sm text-muted mt-3 max-w-md leading-relaxed" role="status">
        {message || DEFAULT_MESSAGE}
      </p>

      <button
        type="button"
        onClick={onRetry}
        disabled={checking}
        className="mt-8 px-7 py-3 bg-primary text-on-primary text-xs tracking-[0.08em] uppercase font-bold hover:bg-primary/90 transition-colors disabled:opacity-60"
      >
        {checking ? 'Checking…' : 'Try again'}
      </button>
      <p className="text-xs text-muted mt-4">This page checks again by itself every minute.</p>
    </div>
  )
}

/*
 * Wraps a storefront layout. While the store is closed it shows the
 * maintenance page instead of the layout; the admin panel is not wrapped, so
 * admins can still sign in and reopen the store.
 *
 * Two things can close the gate: the settings loaded at start-up, and any API
 * call answering 503 "maintenance" (the switch was flipped while this tab was
 * already open).
 */
export default function MaintenanceGate({ children }) {
  const enabled = useSettingsStore((s) => s.settings.maintenance_mode === 'true')
  const message = useSettingsStore((s) => s.settings.maintenance_message)
  const loading = useSettingsStore((s) => s.loading)
  const fetchSettings = useSettingsStore((s) => s.fetchSettings)
  const refreshSettings = useSettingsStore((s) => s.refreshSettings)
  const setMaintenance = useSettingsStore((s) => s.setMaintenance)

  useEffect(() => { fetchSettings() }, [fetchSettings])

  useEffect(() => {
    const onClosed = (e) => setMaintenance(e.detail)
    window.addEventListener('aanga:maintenance', onClosed)
    return () => window.removeEventListener('aanga:maintenance', onClosed)
  }, [setMaintenance])

  useEffect(() => {
    if (!enabled) return undefined
    const timer = setInterval(refreshSettings, RECHECK_MS)
    return () => clearInterval(timer)
  }, [enabled, refreshSettings])

  if (enabled) {
    return <MaintenancePage message={message} onRetry={refreshSettings} checking={loading} />
  }
  return children
}
