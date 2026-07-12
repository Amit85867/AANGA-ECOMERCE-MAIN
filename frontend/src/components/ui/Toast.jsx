import { useEffect } from 'react'
import { create } from 'zustand'
import { IconCheck, IconX, IconAlertTriangle } from '@tabler/icons-react'

const useToastStore = create((set) => ({
  toasts: [],
  add: (toast) => set((s) => ({ toasts: [...s.toasts, { id: Date.now(), ...toast }] })),
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

export const toast = {
  success: (msg) => useToastStore.getState().add({ type: 'success', message: msg }),
  error: (msg) => useToastStore.getState().add({ type: 'error', message: msg }),
  info: (msg) => useToastStore.getState().add({ type: 'info', message: msg }),
}

function ToastItem({ id, type, message }) {
  const remove = useToastStore((s) => s.remove)

  useEffect(() => {
    const timer = setTimeout(() => remove(id), 3000)
    return () => clearTimeout(timer)
  }, [id, remove])

  const Icon = type === 'success' ? IconCheck : type === 'error' ? IconX : IconAlertTriangle
  const bg = type === 'success' ? 'bg-ink' : type === 'error' ? 'bg-maroon' : 'bg-ink'

  return (
    <div className={`${bg} text-white px-4 py-3 flex items-center gap-2.5 text-[13px] shadow-[0_4px_20px_rgba(0,0,0,0.2)] animate-[slideIn_0.2s_ease-out]`}>
      <Icon size={16} className="shrink-0" />
      <span className="flex-1">{message}</span>
      <button onClick={() => remove(id)} className="text-white/50 hover:text-white shrink-0"><IconX size={14} /></button>
    </div>
  )
}

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 w-[340px]">
      {toasts.map((t) => <ToastItem key={t.id} {...t} />)}
    </div>
  )
}
