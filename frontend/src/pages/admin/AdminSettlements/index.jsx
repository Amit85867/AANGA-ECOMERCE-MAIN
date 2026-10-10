import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import {
  IconExternalLink,
  IconBuildingBank,
  IconInfoCircle,
  IconCurrencyRupee,
} from '@tabler/icons-react'

const RAZORPAY_DASHBOARD_URL = 'https://dashboard.razorpay.com/'
const RAZORPAY_BANK_SETTINGS_URL =
  'https://dashboard.razorpay.com/app/settings/business'

const STATUS_COLORS = {
  processed: 'bg-green-100 text-green-700',
  created: 'bg-yellow-100 text-yellow-700',
  failed: 'bg-red-100 text-red-700',
}

const fmtInr = (n) =>
  `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

export default function AdminSettlements() {
  const [settlements, setSettlements] = useState([])
  const [configured, setConfigured] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    adminApi
      .get('/admin/settlements')
      .then((r) => {
        setConfigured(r.data.configured)
        setSettlements(r.data.settlements || [])
      })
      .catch(() => setError('Could not load settlements from Razorpay.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-gray-900">Payments &amp; Settlements</h1>
        <a
          href={RAZORPAY_DASHBOARD_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-[#0A0A0A] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#C8963E]"
        >
          <IconExternalLink size={18} stroke={1.5} />
          Open Razorpay Dashboard
        </a>
      </div>

      {/* How payouts work — the company bank account is managed in Razorpay. */}
      <div className="mb-6 flex gap-3 rounded-xl border border-blue-100 bg-blue-50 p-5">
        <IconInfoCircle size={22} stroke={1.5} className="mt-0.5 shrink-0 text-blue-500" />
        <div className="text-sm text-blue-900">
          <p className="mb-1 font-medium">Where does the money go?</p>
          <p className="text-blue-800/90">
            Online payments are captured by Razorpay and automatically settled to the
            company bank account registered on your Razorpay account (usually within
            2 business days). To add or change that bank account, open the Razorpay
            dashboard —{' '}
            <a
              href={RAZORPAY_BANK_SETTINGS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium underline underline-offset-2"
            >
              Business &amp; Banking settings <IconExternalLink size={13} />
            </a>
            . For security, bank details are managed there and are never stored in this admin.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center text-sm text-gray-400">Loading settlements…</div>
      ) : !configured ? (
        <div className="rounded-xl border border-gray-200 bg-white p-10 text-center">
          <IconBuildingBank size={36} stroke={1.5} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium text-gray-700">Online payments are not configured yet</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-gray-400">
            Set <code className="rounded bg-gray-100 px-1">RAZORPAY_KEY_ID</code> and{' '}
            <code className="rounded bg-gray-100 px-1">RAZORPAY_KEY_SECRET</code> on the
            server, then complete KYC in the Razorpay dashboard. Until then the store runs
            cash-on-delivery only.
          </p>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-100 bg-red-50 p-10 text-center text-sm text-red-600">
          {error}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center gap-2 border-b border-gray-100 px-6 py-4">
            <IconCurrencyRupee size={18} stroke={1.5} className="text-[#C8963E]" />
            <h2 className="font-medium text-gray-900">Recent settlements</h2>
          </div>
          {settlements.length === 0 ? (
            <div className="px-6 py-10 text-center text-sm text-gray-400">
              No settlements yet. They appear here once Razorpay pays out captured orders.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                    <th className="px-6 py-3 font-medium">Date</th>
                    <th className="px-6 py-3 font-medium">Amount</th>
                    <th className="px-6 py-3 font-medium">Fees</th>
                    <th className="px-6 py-3 font-medium">Tax</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                    <th className="px-6 py-3 font-medium">UTR</th>
                  </tr>
                </thead>
                <tbody>
                  {settlements.map((s) => (
                    <tr key={s.id} className="border-b border-gray-50 last:border-0">
                      <td className="px-6 py-3 text-gray-500">
                        {s.created_at
                          ? new Date(s.created_at * 1000).toLocaleDateString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                            })
                          : '—'}
                      </td>
                      <td className="px-6 py-3 font-medium text-gray-900">{fmtInr(s.amount)}</td>
                      <td className="px-6 py-3 text-gray-500">{fmtInr(s.fees)}</td>
                      <td className="px-6 py-3 text-gray-500">{fmtInr(s.tax)}</td>
                      <td className="px-6 py-3">
                        <span
                          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[s.status] || 'bg-gray-100 text-gray-600'}`}
                        >
                          {s.status || 'unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-3 font-mono text-xs text-gray-400">{s.utr || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
