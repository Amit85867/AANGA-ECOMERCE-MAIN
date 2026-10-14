import { useEffect } from 'react'
import { IconAlertCircle, IconCircleCheck, IconInfoCircle, IconX } from '@tabler/icons-react'
import { useToastStore } from '@/components/ui/toastStore'

// Errors stay longer: they usually need reading, sometimes acting on.
const DURATION = { success: 3500, info: 4500, error: 6500 }
const ICONS = { success: IconCircleCheck, info: IconInfoCircle, error: IconAlertCircle }

function ToastItem({ id, type, message }) {
  const remove = useToastStore((s) => s.remove)

  useEffect(() => {
    const timer = setTimeout(() => remove(id), DURATION[type] || 4000)
    return () => clearTimeout(timer)
  }, [id, type, remove])

  const Icon = ICONS[type] || IconInfoCircle

  return (
    <div
      // An error interrupts a screen reader; anything else waits its turn.
      role={type === 'error' ? 'alert' : 'status'}
      className={`flex items-start gap-3 rounded-card px-4 py-3 text-sm shadow-lift animate-[slideIn_0.2s_ease-out] ${
        type === 'error' ? 'bg-danger text-on-primary' : 'bg-primary text-on-primary'
      }`}
    >
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <span className="flex-1 leading-snug">{message}</span>
      <button
        type="button" onClick={() => remove(id)} aria-label="Dismiss"
        className="-m-1 shrink-0 rounded p-1 text-white/70 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
      >
        <IconX size={14} />
      </button>
    </div>
  )
}

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  if (toasts.length === 0) return null

  return (
    <div className="fixed inset-x-4 top-4 z-[9999] flex flex-col gap-2 sm:left-auto sm:right-4 sm:w-[22rem]">
      {toasts.map((t) => <ToastItem key={t.id} {...t} />)}
    </div>
  )
}
