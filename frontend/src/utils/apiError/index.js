/*
 * The API reports a failed validation as `{ errors: { field: [messages] } }`
 * and everything else as `{ error: "message" }`. Screens only read `error`,
 * so a rejected form used to show its generic fallback ("Save failed") and the
 * user never learned which field was wrong.
 *
 * This fills in `error` from `errors` so every existing
 * `err.response?.data?.error || 'fallback'` shows the real reason.
 */
const labelFor = (field) =>
  field
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())

const flatten = (errors, prefix = '') =>
  Object.entries(errors).flatMap(([field, value]) => {
    if (Array.isArray(value)) {
      const text = value.filter((v) => typeof v === 'string').join(' ')
      // "_schema" holds whole-form errors that belong to no single field.
      return text ? [field === '_schema' ? text : `${prefix}${labelFor(field)}: ${text}`] : []
    }
    if (value && typeof value === 'object') return flatten(value, prefix)
    return typeof value === 'string' ? [`${prefix}${labelFor(field)}: ${value}`] : []
  })

export function describeApiError(error) {
  const data = error?.response?.data
  if (data && typeof data === 'object' && !data.error && data.errors) {
    const messages = flatten(data.errors)
    if (messages.length) data.error = messages.slice(0, 3).join(' · ')
  }
  return error
}
