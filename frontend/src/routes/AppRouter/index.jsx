import { Suspense, lazy } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import AuthLayout from '@/layouts/AuthLayout'
import DashboardLayout from '@/layouts/DashboardLayout'
import { RouteError } from '@/components/ErrorBoundary'
import CmsPage from '@/components/common/CmsPage'
import Home from '@/pages/Home'
import Shop from '@/pages/Shop'
import ProductDetail from '@/pages/ProductDetail'
const AdminLayout = lazy(() => import('@/layouts/AdminLayout'))

const Cart = lazy(() => import('@/pages/Cart'))
const Checkout = lazy(() => import('@/pages/Checkout'))
const Wishlist = lazy(() => import('@/pages/Wishlist'))
const OrderTracking = lazy(() => import('@/pages/OrderTracking'))
const Contact = lazy(() => import('@/pages/Contact'))
const About = lazy(() => import('@/pages/About'))
const Offers = lazy(() => import('@/pages/Offers'))
const FAQ = lazy(() => import('@/pages/FAQ'))
const Wholesale = lazy(() => import('@/pages/Wholesale'))
const Returns = lazy(() => import('@/pages/Returns'))
const Privacy = lazy(() => import('@/pages/Privacy'))
const Terms = lazy(() => import('@/pages/Terms'))
const NotFound = lazy(() => import('@/pages/NotFound'))
const StyleGuide = lazy(() => import('@/pages/StyleGuide'))
const Login = lazy(() => import('@/pages/auth/Login'))
const Register = lazy(() => import('@/pages/auth/Register'))
const ForgotPassword = lazy(() => import('@/pages/auth/ForgotPassword'))
const ResetPassword = lazy(() => import('@/pages/auth/ResetPassword'))
const Orders = lazy(() => import('@/pages/account/Orders'))
const OrderDetail = lazy(() => import('@/pages/account/OrderDetail'))
const AccountReturns = lazy(() => import('@/pages/account/Returns'))
const Addresses = lazy(() => import('@/pages/account/Addresses'))
const Profile = lazy(() => import('@/pages/account/Profile'))
const OrderConfirmed = lazy(() => import('@/pages/OrderConfirmed'))

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
const AdminStaff = lazy(() => import('@/pages/admin/AdminStaff'))
const AdminStoreSettings = lazy(() => import('@/pages/admin/AdminStoreSettings'))
const AdminHomepage = lazy(() => import('@/pages/admin/AdminHomepage'))
const AdminNavigation = lazy(() => import('@/pages/admin/AdminNavigation'))
const AdminPages = lazy(() => import('@/pages/admin/AdminPages'))
const AdminFaq = lazy(() => import('@/pages/admin/AdminFaq'))
const AdminCollections = lazy(() => import('@/pages/admin/AdminCollections'))
const AdminCampaigns = lazy(() => import('@/pages/admin/AdminCampaigns'))
const AdminMedia = lazy(() => import('@/pages/admin/AdminMedia'))
const AdminDemo = lazy(() => import('@/pages/admin/AdminDemo'))
const AdminHelp = lazy(() => import('@/pages/admin/AdminHelp'))
const AdminBanners = lazy(() => import('@/pages/admin/AdminBanners'))
const AdminAnnouncements = lazy(() => import('@/pages/admin/AdminAnnouncements'))
const AdminPromoBanners = lazy(() => import('@/pages/admin/AdminPromoBanners'))
const AdminSiteSettings = lazy(() => import('@/pages/admin/AdminSiteSettings'))
const AdminTestimonials = lazy(() => import('@/pages/admin/AdminTestimonials'))
const AdminFeatures = lazy(() => import('@/pages/admin/AdminFeatures'))
const AdminReviews = lazy(() => import('@/pages/admin/AdminReviews'))
const AdminSystem = lazy(() => import('@/pages/admin/AdminSystem'))
const AdminAuditLog = lazy(() => import('@/pages/admin/AdminAuditLog'))

// Suspense wrappers. `page` is for storefront routes: it renders inside the
// layout, so the header and footer stay put while the page's code arrives.
const page = (Component) => (
  <Suspense fallback={<div className="min-h-screen" aria-busy="true" />}>
    <Component />
  </Suspense>
)

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
    errorElement: <RouteError />,
    children: [
      { path: '/', element: <Home /> },
      { path: '/shop', element: <Shop /> },
      { path: '/product/:slug', element: <ProductDetail /> },
      { path: '/cart', element: page(Cart) },
      { path: '/checkout', element: page(Checkout) },
      { path: '/order-confirmed/:id', element: page(OrderConfirmed) },
      { path: '/wishlist', element: page(Wishlist) },
      { path: '/track-order', element: page(OrderTracking) },
      { path: '/contact', element: page(Contact) },
      { path: '/about', element: <CmsPage slug="about" crumb="About" fallback={page(About)} /> },
      { path: '/shipping', element: <CmsPage slug="shipping" crumb="Shipping" /> },
      { path: '/collections/:slug', element: page(Shop) },
      { path: '/offers', element: page(Offers) },
      { path: '/faq', element: page(FAQ) },
      { path: '/wholesale', element: page(Wholesale) },
      { path: '/returns', element: <CmsPage slug="returns" crumb="Returns" fallback={page(Returns)} /> },
      { path: '/privacy-policy', element: <CmsPage slug="privacy" crumb="Privacy Policy" fallback={page(Privacy)} /> },
      { path: '/terms', element: <CmsPage slug="terms" crumb="Terms" fallback={page(Terms)} /> },
    ],
  },
  {
    element: <AuthLayout />,
    errorElement: <RouteError />,
    children: [
      { path: '/login', element: page(Login) },
      { path: '/register', element: page(Register) },
      { path: '/forgot-password', element: page(ForgotPassword) },
      { path: '/reset-password', element: page(ResetPassword) },
    ],
  },
  {
    element: <DashboardLayout />,
    errorElement: <RouteError />,
    children: [
      { path: '/account', element: <Navigate to="/account/orders" replace /> },
      { path: '/account/orders', element: page(Orders) },
      { path: '/account/orders/:id', element: page(OrderDetail) },
      { path: '/account/returns', element: page(AccountReturns) },
      { path: '/account/addresses', element: page(Addresses) },
      { path: '/account/profile', element: page(Profile) },
    ],
  },
  // Internal design-system reference (not linked from the storefront).
  { path: '/style-guide', element: page(StyleGuide) },
  { path: '/admin/login', element: admin(AdminLogin) },
  {
    element: page(AdminLayout),
    errorElement: <RouteError />,
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
      { path: '/admin/settings', element: admin(AdminStoreSettings) },
      { path: '/admin/staff', element: admin(AdminStaff) },
      { path: '/admin/homepage', element: admin(AdminHomepage) },
      { path: '/admin/navigation', element: admin(AdminNavigation) },
      { path: '/admin/pages', element: admin(AdminPages) },
      { path: '/admin/pages/:slug', element: admin(AdminPages) },
      { path: '/admin/faq', element: admin(AdminFaq) },
      { path: '/admin/collections', element: admin(AdminCollections) },
      { path: '/admin/collections/:id', element: admin(AdminCollections) },
      { path: '/admin/campaigns', element: admin(AdminCampaigns) },
      { path: '/admin/campaigns/:id', element: admin(AdminCampaigns) },
      { path: '/admin/media', element: admin(AdminMedia) },
      { path: '/admin/demo', element: admin(AdminDemo) },
      { path: '/admin/help', element: admin(AdminHelp) },
      { path: '/admin/reviews', element: admin(AdminReviews) },
      { path: '/admin/system', element: admin(AdminSystem) },
      { path: '/admin/audit-log', element: admin(AdminAuditLog) },
    ],
  },
  { path: '*', element: page(NotFound) },
])

export default function AppRouter() {
  return <RouterProvider router={router} />
}
