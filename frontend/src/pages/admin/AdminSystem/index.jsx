import { useCallback, useEffect, useState } from 'react'
import {
  IconAlertTriangle, IconCircleCheck, IconCircleDashed, IconCircleX, IconPlugConnected,
  IconRefresh, IconTool,
} from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import { CardSkeleton, ErrorState } from '@/components/admin/DataState'
import { PageHeading } from '@/components/admin/controls'
import { formatDateTime, inputCls, notifyError } from '@/components/admin/helpers'
import { useAdminStore } from '@/store/useAdminStore'

/*
 * The three states the API reports. "Not configured" is deliberately neutral:
 * running COD-only without a courier is a valid way to trade, not a fault.
 */
const STATES = {
  ok: { label: 'Configured', icon: IconCircleCheck, text: 'text-green-700', chip: 'bg-green-100 text-green-800' },
  not_configured: { label: 'Not configured', icon: IconCircleDashed, text: 'text-gray-400', chip: 'bg-gray-100 text-gray-600' },
  error: { label: 'Error', icon: IconCircleX, text: 'text-red-600', chip: 'bg-red-100 text-red-800' },
}

const uptime = (seconds) => {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`
}

function Check({ check }) {
  const state = STATES[check.status] || STATES.error
  const Icon = state.icon
  return (
    <li className="flex items-start gap-3 px-6 py-4">
      <Icon size={22} stroke={1.75} className={`mt-0.5 shrink-0 ${state.text}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-gray-900">{check.label}</span>
          {check.mode && (
            <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${
              check.mode === 'live' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {check.mode} mode
            </span>
          )}
        </div>
        <p className="mt-0.5 text-sm text-gray-600">{check.detail}</p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${state.chip}`}>{state.label}</span>
        {check.latency_ms != null && (
          <span className="text-xs tabular-nums text-gray-400">{check.latency_ms} ms</span>
        )}
      </div>
    </li>
  )
}

function MaintenancePanel({ state, onChanged }) {
  const isMaster = useAdminStore((s) => s.admin?.role === 'master')
  const [message, setMessage] = useState(state.message)
  const [saving, setSaving] = useState(false)

  useEffect(() => setMessage(state.message), [state.message])

  const apply = async (enabled) => {
    if (enabled) {
      const sure = await confirm({
        title: 'Close the storefront?',
        message:
          'Customers will see the maintenance page and will not be able to browse, sign in or place orders until you switch this off. The admin panel stays open.',
        confirmLabel: 'Close storefront',
        danger: true,
      })
      if (!sure) return
    }
    setSaving(true)
    try {
      const { data } = await adminApi.put('/admin/system/maintenance', { enabled, message })
      onChanged(data)
      toast.success(enabled ? 'Storefront closed for maintenance.' : 'Storefront is open again.')
    } catch (err) {
      notifyError(err, 'Could not change maintenance mode.')
    }
    setSaving(false)
  }

  return (
    <section className={`rounded-xl border p-6 ${state.enabled ? 'border-amber-300 bg-amber-50' : 'border-gray-200 bg-white'}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-3">
          <IconTool size={22} stroke={1.5} className={state.enabled ? 'text-amber-700' : 'text-gray-400'} />
          <div>
            <h2 className="font-medium text-gray-900">Maintenance mode</h2>
            <p className="mt-0.5 text-sm text-gray-600">
              {state.enabled
                ? 'The storefront is closed. Customers see the message below.'
                : 'The storefront is open to customers.'}
            </p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${state.enabled ? 'bg-amber-200 text-amber-900' : 'bg-green-100 text-green-800'}`}>
          {state.enabled ? 'ON — storefront closed' : 'OFF — storefront open'}
        </span>
      </div>

      <label className="mt-5 block text-sm font-medium text-gray-700" htmlFor="maintenance-message">
        Message shown to customers
      </label>
      <textarea
        id="maintenance-message" rows={2} maxLength={500} value={message} disabled={!isMaster}
        onChange={(e) => setMessage(e.target.value)}
        className={`${inputCls} mt-1.5`}
      />

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {isMaster ? (
          <>
            <button
              type="button" disabled={saving} onClick={() => apply(!state.enabled)}
              className={`rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-60 ${
                state.enabled ? 'bg-green-700 hover:bg-green-800' : 'bg-amber-600 hover:bg-amber-700'
              }`}
            >
              {saving ? 'Saving…' : state.enabled ? 'Reopen storefront' : 'Close storefront for maintenance'}
            </button>
            {state.enabled && message !== state.message && (
              <button
                type="button" disabled={saving} onClick={() => apply(true)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Update message
              </button>
            )}
          </>
        ) : (
          <p className="text-sm text-gray-500">Only a master admin can switch maintenance mode.</p>
        )}
      </div>
    </section>
  )
}

export default function AdminSystem() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [probing, setProbing] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback((probe = false) => {
    if (probe) setProbing(true)
    else setLoading(true)
    setError(null)
    return adminApi
      .get('/admin/system/health', { params: probe ? { probe: 1 } : {} })
      .then((r) => setData(r.data))
      .catch((err) => setError(err.response?.data?.error || 'Could not load system health.'))
      .finally(() => { setLoading(false); setProbing(false) })
  }, [])

  useEffect(() => { load() }, [load])

  if (!data && loading) {
    return (
      <div>
        <PageHeading title="System health" />
        <div className="space-y-4"><CardSkeleton className="h-24" /><CardSkeleton className="h-96" /></div>
      </div>
    )
  }
  if (!data) return <ErrorState message={error} onRetry={() => load()} />

  const problems = data.checks.filter((c) => c.status === 'error')
  const job = data.reconcile_payments

  return (
    <div>
      <PageHeading
        title="System health"
        subtitle="What the store depends on, and whether each part is set up. Secret values are never shown here."
      >
        <button
          type="button" onClick={() => load(true)} disabled={probing}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          <IconPlugConnected size={16} /> {probing ? 'Testing…' : 'Test connections'}
        </button>
        <button
          type="button" onClick={() => load()} aria-label="Refresh"
          className="rounded-lg border border-gray-200 bg-white p-2 text-gray-500 hover:bg-gray-50 hover:text-gray-900"
        >
          <IconRefresh size={18} className={loading ? 'animate-spin' : ''} />
        </button>
      </PageHeading>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800">{error}</div>
      )}

      <div className={`mb-6 flex items-center gap-3 rounded-xl border px-6 py-4 ${
        problems.length ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'
      }`}>
        {problems.length ? (
          <IconAlertTriangle size={24} className="text-red-600" />
        ) : (
          <IconCircleCheck size={24} className="text-green-700" />
        )}
        <div className="flex-1">
          <div className={`font-medium ${problems.length ? 'text-red-900' : 'text-green-900'}`}>
            {problems.length
              ? `${problems.length} thing${problems.length === 1 ? '' : 's'} need${problems.length === 1 ? 's' : ''} attention: ${problems.map((p) => p.label).join(', ')}`
              : 'Everything that is switched on is working'}
          </div>
          <div className="text-xs text-gray-600">
            Checked {formatDateTime(data.checked_at)}
            {data.probed ? ' · connections tested live' : ' · external services read from configuration — use “Test connections” to contact them'}
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <section className="overflow-hidden rounded-xl border border-gray-200 bg-white xl:col-span-2">
          <h2 className="border-b border-gray-100 px-6 py-4 font-medium text-gray-900">Services</h2>
          <ul className="divide-y divide-gray-100">
            {data.checks.map((check) => <Check key={check.key} check={check} />)}
          </ul>
        </section>

        <div className="space-y-6">
          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 font-medium text-gray-900">Application</h2>
            <dl className="space-y-2.5 text-sm">
              {[
                ['Version', data.app.version],
                ['Environment', data.app.environment],
                ['Uptime', uptime(data.app.uptime_seconds)],
                ['Your IP as seen by the server', data.app.client_ip || '—'],
              ].map(([term, value]) => (
                <div key={term} className="flex justify-between gap-4">
                  <dt className="text-gray-500">{term}</dt>
                  <dd className="truncate font-medium text-gray-900">{value}</dd>
                </div>
              ))}
            </dl>
            {data.app.debug && (
              <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Debug mode is on. It must be off in production.
              </p>
            )}
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="font-medium text-gray-900">Payment reconcile job</h2>
            <p className="mt-1 text-xs text-gray-500">
              Refunds payments whose checkout was abandoned. Should run every 30 minutes.
            </p>
            {!job ? (
              <p className="mt-4 rounded-lg bg-gray-50 px-3 py-2.5 text-sm text-gray-600">
                Has never run. Schedule <code className="rounded bg-gray-200 px-1 text-xs">flask reconcile-payments</code> once
                online payments are switched on.
              </p>
            ) : (
              <>
                <dl className="mt-4 space-y-2.5 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Last run</dt>
                    <dd className="font-medium text-gray-900">{formatDateTime(job.ran_at)}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Result</dt>
                    <dd className={`font-medium ${job.ok ? 'text-green-700' : 'text-red-700'}`}>
                      {job.ok ? 'Succeeded' : 'Failed'}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-gray-500">Checked / refunded / failed</dt>
                    <dd className="font-medium tabular-nums text-gray-900">
                      {job.summary.checked ?? 0} / {job.summary.refunded ?? 0} / {job.summary.failed ?? 0}
                    </dd>
                  </div>
                </dl>
                {job.summary.error && (
                  <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">{job.summary.error}</p>
                )}
                {job.stale && (
                  <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    No run in over 6 hours — check that the scheduled job is still active.
                  </p>
                )}
              </>
            )}
          </section>
        </div>
      </div>

      <div className="mt-6">
        <MaintenancePanel
          state={data.maintenance}
          onChanged={(maintenance) => setData((d) => ({ ...d, maintenance }))}
        />
      </div>
    </div>
  )
}
