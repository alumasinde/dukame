<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

interface NavItem {
  label: string
  path?: string
  icon: string
  children?: NavItem[]
}

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const userMenuOpen = ref(false)
const openGroups = ref<Record<string, boolean>>({ Catalogue: true })

const nav: NavItem[] = [
  { label: 'Overview', path: '/dashboard', icon: 'fa-solid fa-grid-2' },
  {
    label: 'Catalogue',
    icon: 'fa-solid fa-boxes-stacked',
    children: [
      { label: 'Products', path: '/catalogue/products', icon: 'fa-solid fa-box' },
      { label: 'Categories', path: '/catalogue/categories', icon: 'fa-solid fa-layer-group' },
      { label: 'Options', path: '/catalogue/options', icon: 'fa-solid fa-sliders' },
    ],
  },
  { label: 'Orders', path: '/orders', icon: 'fa-solid fa-receipt' },
  { label: 'Customers', path: '/customers', icon: 'fa-solid fa-users' },
  { label: 'Payments', path: '/payments', icon: 'fa-solid fa-credit-card' },
  { label: 'Analytics', path: '/analytics', icon: 'fa-solid fa-chart-line' },
]

const settingsItem: NavItem = { label: 'Settings', path: '/settings', icon: 'fa-solid fa-gear' }
const hasRoute = (item: NavItem) => item.path ? route.path === item.path || route.path.startsWith(`${item.path}/`) : item.children?.some(hasRoute) ?? false
const pageTitle = computed(() => {
  const match = [...nav, settingsItem].find((item) => hasRoute(item))
  if (match) return match.label
  return route.path.split('/').filter(Boolean).at(-1)?.replace(/-/g, ' ') || 'Overview'
})

function toggleGroup(label: string) {
  openGroups.value[label] = !openGroups.value[label]
}

function changeTenant(event: Event) {
  auth.setActiveTenant((event.target as HTMLSelectElement).value)
}

async function logout() {
  userMenuOpen.value = false
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ open: mobileOpen }">
      <div class="brand-row">
        <RouterLink to="/dashboard" class="brand" @click="mobileOpen = false">
          <span class="brand-mark">D</span><span>DukaMe</span>
        </RouterLink>
        <button class="icon-button mobile-close" type="button" aria-label="Close menu" @click="mobileOpen = false">
          <i class="fa-solid fa-xmark" aria-hidden="true"></i>
        </button>
      </div>

      <div v-if="auth.activeTenant" class="workspace-card">
        <span class="workspace-avatar">{{ auth.activeTenant.name.charAt(0).toUpperCase() }}</span>
        <div class="workspace-copy"><strong>{{ auth.activeTenant.name }}</strong><span>{{ auth.activeTenant.role }}</span></div>
      </div>

      <nav class="main-nav" aria-label="Main navigation">
        <template v-for="item in nav" :key="item.label">
          <button v-if="item.children" type="button" class="nav-item nav-group-toggle" :class="{ active: hasRoute(item) }" @click="toggleGroup(item.label)">
            <span class="nav-icon"><i :class="item.icon" aria-hidden="true"></i></span>
            <span>{{ item.label }}</span>
            <i class="fa-solid fa-chevron-down nav-chevron" :class="{ rotated: openGroups[item.label] }" aria-hidden="true"></i>
          </button>
          <RouterLink v-else :to="item.path!" class="nav-item" :class="{ active: hasRoute(item) }" @click="mobileOpen = false">
            <span class="nav-icon"><i :class="item.icon" aria-hidden="true"></i></span>{{ item.label }}
          </RouterLink>
          <div v-if="item.children && openGroups[item.label]" class="nav-children">
            <RouterLink v-for="child in item.children" :key="child.path" :to="child.path!" class="nav-child" :class="{ active: hasRoute(child) }" @click="mobileOpen = false">
              <span class="nav-child-dot"></span>{{ child.label }}
            </RouterLink>
          </div>
        </template>
      </nav>

      <div class="sidebar-bottom">
        <RouterLink :to="settingsItem.path!" class="nav-item" :class="{ active: hasRoute(settingsItem) }" @click="mobileOpen = false">
          <span class="nav-icon"><i :class="settingsItem.icon" aria-hidden="true"></i></span>{{ settingsItem.label }}
        </RouterLink>
        <button class="profile-mini" type="button" @click="userMenuOpen = !userMenuOpen">
          <span class="avatar">{{ auth.user?.first_name?.charAt(0) }}{{ auth.user?.last_name?.charAt(0) }}</span>
          <span class="profile-text"><strong>{{ auth.user?.first_name }} {{ auth.user?.last_name }}</strong><small>{{ auth.user?.email }}</small></span>
          <span class="chevron"><i class="fa-solid fa-chevron-down" aria-hidden="true"></i></span>
        </button>
        <div v-if="userMenuOpen" class="user-menu">
          <RouterLink to="/settings" @click="userMenuOpen = false">Account settings</RouterLink>
          <button type="button" @click="logout">Sign out</button>
        </div>
      </div>
    </aside>

    <div v-if="mobileOpen" class="sidebar-backdrop" @click="mobileOpen = false"></div>

    <main class="main-content">
      <header class="topbar">
        <button class="icon-button menu-toggle" type="button" aria-label="Open menu" @click="mobileOpen = true">
          <i class="fa-solid fa-bars" aria-hidden="true"></i>
        </button>
        <div class="topbar-title"><span class="eyebrow">Commerce workspace</span><h1>{{ pageTitle }}</h1></div>
        <div class="topbar-actions">
          <div v-if="auth.tenants.length > 1" class="tenant-switcher">
            <select :value="auth.activeTenantId || ''" aria-label="Active shop" @change="changeTenant">
              <option v-for="tenant in auth.tenants" :key="tenant.public_id" :value="tenant.public_id">{{ tenant.name }}</option>
            </select>
          </div>
          <RouterLink to="/shops" class="button button-primary button-sm"><i class="fa-solid fa-plus" aria-hidden="true"></i> New shop</RouterLink>
        </div>
      </header>
      <section class="page-content"><RouterView /></section>
    </main>
  </div>
</template>

<style scoped>
.nav-icon::before { content: none !important; }
.nav-icon { display: inline-grid; place-items: center; width: 18px; height: 18px; flex: 0 0 18px; }
.nav-icon i { font-size: 13px; line-height: 1; }
.icon-button i { line-height: 1; }
.nav-group-toggle { width: 100%; border: 0; background: transparent; font: inherit; text-align: left; cursor: pointer; }
.nav-group-toggle > span:nth-child(2) { flex: 1; }
.nav-chevron { margin-left: auto; font-size: 10px; transition: transform .15s ease; }
.nav-chevron.rotated { transform: rotate(180deg); }
.nav-children { display: grid; gap: 2px; margin: 2px 0 6px 26px; padding-left: 12px; border-left: 1px solid var(--border-color, #e5e7eb); }
.nav-child { display: flex; align-items: center; gap: 9px; min-height: 34px; padding: 0 10px; border-radius: 7px; color: inherit; text-decoration: none; font-size: 13px; }
.nav-child:hover, .nav-child.active { background: var(--surface-hover, #f3f4f6); }
.nav-child.active { font-weight: 600; }
.nav-child-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; opacity: .45; }
</style>
