import { useEffect } from 'react'
import AppRouter from '@/routes/AppRouter'
import ToastContainer from '@/components/ui/Toast'
import { useAuthStore } from '@/store/useAuthStore'
import { useCartStore } from '@/store/useCartStore'
import { useWishlistStore } from '@/store/useWishlistStore'

function App() {
  const fetchMe = useAuthStore((s) => s.fetchMe)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const fetchCart = useCartStore((s) => s.fetchCart)
  const fetchWishlist = useWishlistStore((s) => s.fetchWishlist)

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

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
