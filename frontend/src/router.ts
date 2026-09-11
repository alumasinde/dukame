import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const phase3View = () => import('./views/ComingSoonView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'login', component: () => import('./views/LoginViewClean.vue'), meta: { guest: true } },
    { path: '/register', name: 'register', component: () => import('./views/RegisterView.vue'), meta: { guest: true } },
    { path: '/verify-email', name: 'verify-email', component: () => import('./views/VerifyEmailView.vue'), meta: { guest: true } },
    { path: '/reset-password', name: 'reset-password', component: () => import('./views/ResetPasswordView.vue'), meta: { guest: true } },
    { path: '/onboarding', name: 'onboarding', component: () => import('./views/OnboardingView.vue'), meta: { auth: true, requiresOnboarding: true } },
    {
      path: '/', component: () => import('./layouts/AppLayout.vue'), meta: { auth: true },
      children: [
        { path: 'dashboard', name: 'dashboard', component: () => import('./views/DashboardView.vue') },
        { path: 'shops', name: 'shops', component: () => import('./views/ShopsView.vue') },
        { path: 'billing', name: 'billing', component: () => import('./views/BillingView.vue') },
        { path: 'team', name: 'team', component: () => import('./views/TeamView.vue') },
        { path: 'settings', name: 'settings', component: () => import('./views/SettingsView.vue') },
        { path: 'catalogue/products', name: 'catalogue-products', component: () => import('./views/CatalogueProductsView.vue') },
        { path: 'catalogue/categories', name: 'catalogue-categories', component: () => import('./views/CatalogueCategoriesView.vue') },
        { path: 'catalogue/options', name: 'catalogue-options', component: () => import('./views/CatalogueOptionsView.vue') },
        { path: 'orders', name: 'orders', component: phase3View, props: { title: 'Orders', description: 'Orders will become the central workflow for receiving, processing and completing customer purchases.' } },
        { path: 'customers', name: 'customers', component: phase3View, props: { title: 'Customers', description: 'Customer profiles, purchase history and customer activity will be managed here.' } },
        { path: 'payments', name: 'payments', component: phase3View, props: { title: 'Payments', description: 'Payment methods, transactions and payment status will be managed here as commerce payments are introduced.' } },
        { path: 'analytics', name: 'analytics', component: phase3View, props: { title: 'Analytics', description: 'Sales, product, customer and business performance analytics will be added as commerce data becomes available.' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.meta.auth && !auth.isAuthenticated) return { name: 'login', replace: true }
  if (to.meta.guest && auth.isAuthenticated) return auth.onboardingComplete ? { name: 'dashboard', replace: true } : { name: 'onboarding', replace: true }
  if (auth.isAuthenticated && !auth.onboardingComplete && !to.meta.requiresOnboarding && to.meta.auth) return { name: 'onboarding', replace: true }
  if (auth.isAuthenticated && auth.onboardingComplete && to.meta.requiresOnboarding) return { name: 'dashboard', replace: true }
})

window.addEventListener('storage', (event) => {
  if (event.key === 'dukame_access_token' && !event.newValue) {
    const auth = useAuthStore()
    auth.logoutLocal()
    if (router.currentRoute.value.name !== 'login') router.replace({ name: 'login' })
  }
})

window.addEventListener('dukame:session-expired', () => {
  const auth = useAuthStore()
  auth.logoutLocal()
  if (router.currentRoute.value.name !== 'login') router.replace({ name: 'login' })
})

setInterval(async () => {
  const auth = useAuthStore()
  if (auth.isAuthenticated && auth.initialized) {
    try { await auth.validateSession() } catch {
      auth.logoutLocal()
      if (router.currentRoute.value.name !== 'login') router.replace({ name: 'login' })
    }
  }
}, 5 * 60 * 1000)

export default router
