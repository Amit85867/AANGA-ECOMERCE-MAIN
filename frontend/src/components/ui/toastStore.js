import { create } from 'zustand'

let nextId = 1

export const useToastStore = create((set) => ({
  toasts: [],
  // A counter, not Date.now(): two toasts in the same millisecond shared an id,
  // and dismissing one removed both.
  add: (toast) => set((s) => ({ toasts: [...s.toasts.slice(-3), { id: nextId++, ...toast }] })),
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

const show = (type) => (message) => useToastStore.getState().add({ type, message })

export const toast = { success: show('success'), error: show('error'), info: show('info') }
