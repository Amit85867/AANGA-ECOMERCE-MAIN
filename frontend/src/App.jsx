import { useEffect } from 'react'
import AppRouter from '@/routes/AppRouter'
import ToastContainer from '@/components/ui/Toast'
import { useAuthStore } from '@/store/useAuthStore'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'

function App() {
  const restoreSession = useAuthStore((s) => s.restoreSession)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const fetchCart = useCartStore((s) => s.fetchCart)
  const fetchWishlist = useWishlistStore((s) => s.fetchWishlist)

  // Exchange the httpOnly refresh cookie for an access token on first load.
  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  useEffect(() => {
    if (isAuthenticated) {
      fetchCart()
      fetchWishlist()
    }
  }, [isAuthenticated, fetchCart, fetchWishlist])

  return (
    <>
      <AppRouter />
      <ToastContainer />
    </>
  )
}

export default App
