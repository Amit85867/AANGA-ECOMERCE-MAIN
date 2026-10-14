import { useEffect } from 'react'
import { IconHeart } from '@tabler/icons-react'
import ProductCard from '@/components/ui/ProductCard'
import Button from '@/components/ui/Button'
import { Container, EmptyState, PageTitle, ProductCardSkeleton } from '@/components/ui/Display'
import { useWishlistStore } from '@/store/useWishlistStore'
import { useAuthStore } from '@/store/useAuthStore'
import Seo from '@/components/Seo'

export default function Wishlist() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const initializing = useAuthStore((s) => s.initializing)
  const { items, loading, fetchWishlist } = useWishlistStore()

  useEffect(() => {
    if (isAuthenticated) fetchWishlist()
  }, [isAuthenticated, fetchWishlist])

  let body
  if (initializing || (isAuthenticated && loading && items.length === 0)) {
    body = (
      <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:gap-x-6 md:grid-cols-3 lg:grid-cols-4" aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => <ProductCardSkeleton key={i} />)}
      </div>
    )
  } else if (!isAuthenticated) {
    body = (
      <EmptyState
        icon={IconHeart} title="Sign in to see your wishlist"
        hint="Save the pieces you like and find them here on any device."
        action={<Button to="/login" state={{ from: '/wishlist' }}>Sign in</Button>}
      />
    )
  } else if (items.length === 0) {
    body = (
      <EmptyState
        icon={IconHeart} title="Nothing saved yet"
        hint="Tap the heart on any product to keep it here for later."
        action={<Button to="/shop">Browse products</Button>}
      />
    )
  } else {
    body = (
      // The card's own heart removes an item, so there is one way to do it
      // everywhere rather than a second control only on this page.
      <ul className="grid grid-cols-2 gap-x-4 gap-y-8 sm:gap-x-6 md:grid-cols-3 lg:grid-cols-4">
        {items.map((p) => (
          <li key={p.wishlist_id}><ProductCard product={{ ...p, id: p.product_id }} /></li>
        ))}
      </ul>
    )
  }

  return (
    <>
      <Seo title="My Wishlist" noindex />
      <Container className="pb-20">
        <PageTitle
          title="Wishlist"
          subtitle={isAuthenticated && items.length > 0 ? `${items.length} saved item${items.length === 1 ? '' : 's'}` : undefined}
          crumbs={[{ label: 'Home', to: '/' }, { label: 'Wishlist' }]}
        />
        {body}
      </Container>
    </>
  )
}
