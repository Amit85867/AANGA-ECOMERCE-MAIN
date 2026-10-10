import { toast } from '@/components/ui/Toast'

/* Formatting and feedback helpers shared by the admin pages. */

export const inputCls =
  'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-[#C8963E] focus:ring-2 focus:ring-[#C8963E]/20 disabled:bg-gray-50 disabled:text-gray-400'

/* Shows the API's own explanation when it gave one. */
export function notifyError(err, fallback = 'Something went wrong. Please try again.') {
  toast.error(err?.response?.data?.error || fallback)
}

export const inr = (value) =>
  `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export const formatDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export const formatDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '—'

export const ORDER_STATUS_TONE = {
  pending: 'amber', confirmed: 'blue', packed: 'blue', shipped: 'purple',
  out_for_delivery: 'purple', delivered: 'green', cancelled: 'red',
  return_requested: 'amber', returned: 'gray',
}

export const RETURN_STATUS_TONE = {
  requested: 'amber', approved: 'blue', pickup_scheduled: 'blue', picked_up: 'purple',
  inspected: 'purple', resolved: 'green', rejected: 'red',
}

export const humanize = (value) =>
  String(value || '').replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
