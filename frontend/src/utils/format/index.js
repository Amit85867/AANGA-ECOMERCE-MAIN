/* Formatting shared by the storefront. */

// Whole rupees stay whole (₹999); anything else shows paise in full (₹99.90).
export const inr = (value) => {
  const amount = Number(value || 0)
  return `₹${amount.toLocaleString('en-IN', {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  })}`
}

export const formatDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : ''

export const formatDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit',
      })
    : ''

export const humanize = (value) =>
  String(value || '').replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

/* status -> [label a customer understands, badge tone] */
export const ORDER_STATUS = {
  pending: ['Order placed', 'accent'],
  confirmed: ['Confirmed', 'neutral'],
  packed: ['Packed', 'neutral'],
  shipped: ['Shipped', 'neutral'],
  out_for_delivery: ['Out for delivery', 'neutral'],
  delivered: ['Delivered', 'dark'],
  cancelled: ['Cancelled', 'danger'],
  return_requested: ['Return requested', 'accent'],
  returned: ['Returned', 'neutral'],
}

export const RETURN_STATUS = {
  requested: ['Requested', 'accent'],
  approved: ['Approved', 'neutral'],
  pickup_scheduled: ['Pickup scheduled', 'neutral'],
  picked_up: ['Picked up', 'neutral'],
  inspected: ['Being inspected', 'neutral'],
  resolved: ['Completed', 'dark'],
  rejected: ['Declined', 'danger'],
}

export const RETURN_REASONS = [
  ['size_issue', 'Size does not fit'],
  ['wrong_item', 'Wrong item received'],
  ['damaged', 'Arrived damaged'],
  ['quality_issue', 'Quality not as expected'],
  ['not_as_described', 'Not as described'],
  ['changed_mind', 'Changed my mind'],
  ['other', 'Other'],
]
