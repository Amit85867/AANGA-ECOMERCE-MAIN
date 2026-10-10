import { CURRENCY_SYMBOL } from '@/utils/constants'

export function formatCurrency(amount) {
  const value = Number(amount)
  return `${CURRENCY_SYMBOL}${value.toLocaleString('en-IN', {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  })}`
}
