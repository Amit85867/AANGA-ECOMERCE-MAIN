import { CURRENCY_SYMBOL } from '@/utils/constants'

export function formatCurrency(amount) {
  return `${CURRENCY_SYMBOL}${Number(amount).toLocaleString('en-IN')}`
}
