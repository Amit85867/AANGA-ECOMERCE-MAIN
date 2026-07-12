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
import Login from '@/pages/auth/Login'
import Register from '@/pages/auth/Register'
import ForgotPassword from '@/pages/auth/ForgotPassword'
import ResetPassword from '@/pages/auth/ResetPassword'
import Dashboard from '@/pages/account/Dashboard'

import AdminLogin from '@/pages/admin/AdminLogin'
import AdminDashboard from '@/pages/admin/AdminDashboard'
import AdminProducts from '@/pages/admin/AdminProducts'
import AdminProductForm from '@/pages/admin/AdminProductForm'
import AdminCategories from '@/pages/admin/AdminCategories'
import AdminOrders from '@/pages/admin/AdminOrders'
import AdminOrderDetail from '@/pages/admin/AdminOrderDetail'
import AdminUsers from '@/pages/admin/AdminUsers'
import AdminUserDetail from '@/pages/admin/AdminUserDetail'
import AdminCoupons from '@/pages/admin/AdminCoupons'
import AdminOffers from '@/pages/admin/AdminOffers'
import AdminInquiries from '@/pages/admin/AdminInquiries'
import AdminMessages from '@/pages/admin/AdminMessages'
import AdminNewsletter from '@/pages/admin/AdminNewsletter'
import AdminSettings from '@/pages/admin/AdminSettings'
import AdminBanners from '@/pages/admin/AdminBanners'
import AdminAnnouncements from '@/pages/admin/AdminAnnouncements'
import AdminPromoBanners from '@/pages/admin/AdminPromoBanners'
import AdminSiteSettings from '@/pages/admin/AdminSiteSettings'
import AdminTestimonials from '@/pages/admin/AdminTestimonials'
import AdminFeatures from '@/pages/admin/AdminFeatures'

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
  { path: '/admin/login', element: <AdminLogin /> },
  {
    element: <AdminLayout />,
    children: [
      { index: true, path: '/admin', element: <AdminDashboard /> },
      { path: '/admin/products', element: <AdminProducts /> },
      { path: '/admin/products/new', element: <AdminProductForm /> },
      { path: '/admin/products/:id', element: <AdminProductForm /> },
      { path: '/admin/categories', element: <AdminCategories /> },
      { path: '/admin/orders', element: <AdminOrders /> },
      { path: '/admin/orders/:id', element: <AdminOrderDetail /> },
      { path: '/admin/users', element: <AdminUsers /> },
      { path: '/admin/users/:id', element: <AdminUserDetail /> },
      { path: '/admin/coupons', element: <AdminCoupons /> },
      { path: '/admin/offers', element: <AdminOffers /> },
      { path: '/admin/inquiries', element: <AdminInquiries /> },
      { path: '/admin/messages', element: <AdminMessages /> },
      { path: '/admin/newsletter', element: <AdminNewsletter /> },
      { path: '/admin/banners', element: <AdminBanners /> },
      { path: '/admin/announcements', element: <AdminAnnouncements /> },
      { path: '/admin/promo-banners', element: <AdminPromoBanners /> },
      { path: '/admin/testimonials', element: <AdminTestimonials /> },
      { path: '/admin/features', element: <AdminFeatures /> },
      { path: '/admin/site-settings', element: <AdminSiteSettings /> },
      { path: '/admin/settings', element: <AdminSettings /> },
    ],
  },
  { path: '*', element: <NotFound /> },
])

export default function AppRouter() {
  return <RouterProvider router={router} />
}
