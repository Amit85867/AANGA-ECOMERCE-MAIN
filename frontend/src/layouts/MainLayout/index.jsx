import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import AnnounceBar from '@/components/layout/AnnounceBar'
import Navbar from '@/components/layout/Navbar'
import Footer from '@/components/layout/Footer'
import MaintenanceGate from '@/components/layout/MaintenanceGate'
import { FestiveLayer } from '@/components/layout/Festive'
import { useCampaignEpoch, useLayoutWatcher } from '@/store/useLayoutStore'
import { useSetting } from '@/store/useSettingsStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useCartStore } from '@/store/useCartStore'

export default function MainLayout() {
  useLayoutWatcher()
  const s = useSetting()
  const favicon = s('favicon_url')
  const epoch = useCampaignEpoch()
  const isAuthenticated = useAuthStore((st) => st.isAuthenticated)
  const fetchCart = useCartStore((st) => st.fetchCart)

  // The owner's own browser-tab icon, when they have uploaded one.
  useEffect(() => {
    if (!favicon) return
    const link = document.querySelector('link[rel="icon"]')
    if (link) { link.removeAttribute('type'); link.href = favicon }
  }, [favicon])

  // A campaign started or ended: the prices in the cart may have changed.
  useEffect(() => {
    if (epoch > 0 && isAuthenticated) fetchCart()
  }, [epoch, isAuthenticated, fetchCart])

  return (
    <MaintenanceGate>
      <div className="min-h-screen flex flex-col">
        <AnnounceBar />
        <Navbar />
        <main className="min-h-screen flex-1">
          <Outlet />
        </main>
        <Footer />
        <FestiveLayer />
      </div>
    </MaintenanceGate>
  )
}
