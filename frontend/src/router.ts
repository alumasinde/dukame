import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: () => import('./views/LoginView.vue'), meta: { guest: true } },
    { path: '/register', component: () => import('./views/RegisterView.vue'), meta: { guest: true } },
    { path: '/verify-email', component: () => import('./views/VerifyEmailView.vue'), meta: { guest: true } },
    { path: '/reset-password', component: () => import('./views/ResetPasswordView.vue'), meta: { guest: true } },
    {
      path: '/',
      component: () => import('./layouts/AppLayout.vue'),
      meta: { auth: true },
      children: [
        { path: 'dashboard', component: () => import('./views/DashboardView.vue') },
        { path: 'shops', component: () => import('./views/ShopsView.vue') },
        { path: 'billing', component: () => import('./views/BillingView.vue') },
        { path: 'team', component: () => import('./views/TeamView.vue') },
        { path: 'settings', component: () => import('./views/SettingsView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.meta.auth && !auth.isAuthenticated) return '/login'
  if (to.meta.guest && auth.isAuthenticated) return '/dashboard'
})

window.addEventListener('dukame:session-expired', () => {
  const auth = useAuthStore()
  auth.logoutLocal()
  if (router.currentRoute.value.path !== '/login') router.push('/login')
})

export default router