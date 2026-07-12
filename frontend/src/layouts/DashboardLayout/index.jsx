import { Outlet } from 'react-router-dom'
import AnnounceBar from '@/components/layout/AnnounceBar'
import Navbar from '@/components/layout/Navbar'
import Footer from '@/components/layout/Footer'

export default function DashboardLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <AnnounceBar />
      <Navbar />
      <main className="flex-1 grid grid-cols-[240px_1fr]">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
