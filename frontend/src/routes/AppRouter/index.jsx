import { Suspense, lazy } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import AuthLayout from '@/layouts/AuthLayout'
import DashboardLayout from '@/layouts/DashboardLayout'
import AdminLayout from '@/layouts/AdminLayout'

import Home from '@/pages/Home'
import Shop from '@/pages/Shop'
import ProductDetail from '@/pages/ProductDetail'
import Cart from '@/pages/Cart'
import Checkout from '@/pages/Checkout'
import Wishlist from '@/pages/Wishlist'
import OrderTracking from '@/pages/OrderTracking'
import Contact from '@/pages/Contact'
import About from '@/pages/About'
import Offers from '@/pages/Offers'
import FAQ from '@/pages/FAQ'
import Wholesale from '@/pages/Wholesale'
import Returns from '@/pages/Returns'
import Privacy from '@/pages/Privacy'
import Terms from '@/pages/Terms'
import NotFound from '@/pages/NotFound'
import StyleGuide from '@/pages/StyleGuide'
import Login from '@/pages/auth/Login'
import Register from '@/pages/auth/Register'
import ForgotPassword from '@/pages/auth/ForgotPassword'
import ResetPassword from '@/pages/auth/ResetPassword'
import Dashboard from '@/pages/account/Dashboard'

// Admin pages are lazy-loaded so ordinary shoppers never download the entire
// admin panel with the storefront bundle — it loads on demand under /admin.
const AdminLogin = lazy(() => import('@/pages/admin/AdminLogin'))
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const AdminProducts = lazy(() => import('@/pages/admin/AdminProducts'))
const AdminProductForm = lazy(() => import('@/pages/admin/AdminProductForm'))
const AdminCategories = lazy(() => import('@/pages/admin/AdminCategories'))
const AdminOrders = lazy(() => import('@/pages/admin/AdminOrders'))
const AdminOrderDetail = lazy(() => import('@/pages/admin/AdminOrderDetail'))
const AdminReturns = lazy(() => import('@/pages/admin/AdminReturns'))
const AdminSettlements = lazy(() => import('@/pages/admin/AdminSettlements'))
const AdminUsers = lazy(() => import('@/pages/admin/AdminUsers'))
const AdminUserDetail = lazy(() => import('@/pages/admin/AdminUserDetail'))
const AdminCoupons = lazy(() => import('@/pages/admin/AdminCoupons'))
const AdminOffers = lazy(() => import('@/pages/admin/AdminOffers'))
const AdminInquiries = lazy(() => import('@/pages/admin/AdminInquiries'))
const AdminMessages = lazy(() => import('@/pages/admin/AdminMessages'))
const AdminNewsletter = lazy(() => import('@/pages/admin/AdminNewsletter'))
const AdminSettings = lazy(() => import('@/pages/admin/AdminSettings'))
const AdminBanners = lazy(() => import('@/pages/admin/AdminBanners'))
const AdminAnnouncements = lazy(() => import('@/pages/admin/AdminAnnouncements'))
const AdminPromoBanners = lazy(() => import('@/pages/admin/AdminPromoBanners'))
const AdminSiteSettings = lazy(() => import('@/pages/admin/AdminSiteSettings'))
const AdminTestimonials = lazy(() => import('@/pages/admin/AdminTestimonials'))
const AdminFeatures = lazy(() => import('@/pages/admin/AdminFeatures'))

// Suspense wrapper for the lazily-loaded admin routes.
const admin = (Component) => (
  <Suspense
    fallback={<div className="p-10 text-center text-sm text-gray-400">Loading…</div>}
  >
    <Component />
  </Suspense>
)

const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: '/', element: <Home /> },
      { path: '/shop', element: <Shop /> },
      { path: '/product/:slug', element: <ProductDetail /> },
      { path: '/cart', element: <Cart /> },
      { path: '/checkout', element: <Checkout /> },
      { path: '/wishlist', element: <Wishlist /> },
      { path: '/track-order', element: <OrderTracking /> },
      { path: '/contact', element: <Contact /> },
      { path: '/about', element: <About /> },
      { path: '/offers', element: <Offers /> },
      { path: '/faq', element: <FAQ /> },
      { path: '/wholesale', element: <Wholesale /> },
      { path: '/returns', element: <Returns /> },
      { path: '/privacy-policy', element: <Privacy /> },
      { path: '/terms', element: <Terms /> },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <Login /> },
      { path: '/register', element: <Register /> },
      { path: '/forgot-password', element: <ForgotPassword /> },
      { path: '/reset-password', element: <ResetPassword /> },
    ],
  },
  {
    element: <DashboardLayout />,
    children: [{ path: '/account', element: <Dashboard /> }],
  },
  // Internal design-system reference (not linked from the storefront).
  { path: '/style-guide', element: <StyleGuide /> },
  { path: '/admin/login', element: admin(AdminLogin) },
  {
    element: <AdminLayout />,
    children: [
      { index: true, path: '/admin', element: admin(AdminDashboard) },
      { path: '/admin/products', element: admin(AdminProducts) },
      { path: '/admin/products/new', element: admin(AdminProductForm) },
      { path: '/admin/products/:id', element: admin(AdminProductForm) },
      { path: '/admin/categories', element: admin(AdminCategories) },
      { path: '/admin/orders', element: admin(AdminOrders) },
      { path: '/admin/orders/:id', element: admin(AdminOrderDetail) },
      { path: '/admin/returns', element: admin(AdminReturns) },
      { path: '/admin/settlements', element: admin(AdminSettlements) },
      { path: '/admin/users', element: admin(AdminUsers) },
      { path: '/admin/users/:id', element: admin(AdminUserDetail) },
      { path: '/admin/coupons', element: admin(AdminCoupons) },
      { path: '/admin/offers', element: admin(AdminOffers) },
      { path: '/admin/inquiries', element: admin(AdminInquiries) },
      { path: '/admin/messages', element: admin(AdminMessages) },
      { path: '/admin/newsletter', element: admin(AdminNewsletter) },
      { path: '/admin/banners', element: admin(AdminBanners) },
      { path: '/admin/announcements', element: admin(AdminAnnouncements) },
      { path: '/admin/promo-banners', element: admin(AdminPromoBanners) },
      { path: '/admin/testimonials', element: admin(AdminTestimonials) },
      { path: '/admin/features', element: admin(AdminFeatures) },
      { path: '/admin/site-settings', element: admin(AdminSiteSettings) },
      { path: '/admin/settings', element: admin(AdminSettings) },
    ],
  },
  { path: '*', element: <NotFound /> },
])

export default function AppRouter() {
  return <RouterProvider router={router} />
}
