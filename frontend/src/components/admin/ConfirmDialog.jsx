import { useEffect, useRef } from 'react'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useConfirmStore } from '@/components/admin/confirm'

export default function ConfirmDialog() {
  const request = useConfirmStore((s) => s.request)
  const confirmRef = useRef(null)
  const cancelRef = useRef(null)

  const settle = (answer) => {
    request?.resolve(answer)
    useConfirmStore.setState({ request: null })
  }

  useEffect(() => {
    if (!request) return undefined
    // A destructive dialog opens on "Cancel", so Enter cannot delete by reflex.
    ;(request.danger ? cancelRef : confirmRef).current?.focus()

    const onKey = (e) => {
      if (e.key === 'Escape') settle(false)
      if (e.key === 'Tab') {
        // Two controls: keep focus cycling between them.
        const next = document.activeElement === confirmRef.current ? cancelRef : confirmRef
        e.preventDefault()
        next.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request])

  if (!request) return null

  return (
    <div
      className="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(e) => e.target === e.currentTarget && settle(false)}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby={request.message ? 'confirm-message' : undefined}
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl"
      >
        <div className="flex gap-4">
          {request.danger && (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
              <IconAlertTriangle size={20} />
            </div>
          )}
          <div className="min-w-0">
            <h2 id="confirm-title" className="text-base font-semibold text-gray-900">
              {request.title}
            </h2>
            {request.message && (
              <p id="confirm-message" className="mt-1.5 text-sm leading-relaxed text-gray-600">
                {request.message}
              </p>
            )}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={() => settle(false)}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
          >
            {request.cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={() => settle(true)}
            className={`rounded-lg px-4 py-2 text-sm font-medium text-white focus-visible:outline-2 focus-visible:outline-offset-2 ${
              request.danger
                ? 'bg-red-600 hover:bg-red-700 focus-visible:outline-red-600'
                : 'bg-gray-900 hover:bg-black focus-visible:outline-gray-900'
            }`}
          >
            {request.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
