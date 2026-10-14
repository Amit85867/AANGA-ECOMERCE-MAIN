import { create } from 'zustand'

/*
 * A promise-based replacement for window.confirm().
 *
 *   if (!(await confirm({ title: 'Delete coupon?', danger: true }))) return
 *
 * The native dialog cannot be styled, cannot say what will actually happen,
 * and blocks the whole tab. This one is mounted once (in AdminLayout) and
 * resolves true / false.
 */
export const useConfirmStore = create(() => ({ request: null }))

export function confirm(options) {
  return new Promise((resolve) => {
    useConfirmStore.setState({
      request: {
        title: 'Are you sure?',
        message: '',
        confirmLabel: 'Confirm',
        cancelLabel: 'Cancel',
        danger: false,
        ...(typeof options === 'string' ? { message: options } : options),
        resolve,
      },
    })
  })
}
