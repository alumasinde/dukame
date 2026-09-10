<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const userMenuOpen = ref(false)

const nav = [
  { label: 'Overview', path: '/dashboard', icon: 'grid' },
  { label: 'My shops', path: '/shops', icon: 'store' },
  { label: 'Billing', path: '/billing', icon: 'card' },
  { label: 'Team', path: '/team', icon: 'users' },
]

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
          <span class="brand-mark">D</span>
          <span>DukaMe</span>
        </RouterLink>
        <button class="icon-button mobile-close" @click="mobileOpen = false">×</button>
      </div>

      <div class="workspace-card" v-if="auth.activeTenant">
        <span class="workspace-avatar">{{ auth.activeTenant.name.charAt(0).toUpperCase() }}</span>
        <div class="workspace-copy">
          <strong>{{ auth.activeTenant.name }}</strong>
          <span>{{ auth.activeTenant.role }}</span>
        </div>
      </div>

      <nav class="main-nav">
        <RouterLink v-for="item in nav" :key="item.path" :to="item.path" class="nav-item" :class="{ active: route.path === item.path }" @click="mobileOpen = false">
          <span class="nav-icon" :data-icon="item.icon"></span>
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="sidebar-bottom">
        <RouterLink to="/settings" class="nav-item" :class="{ active: route.path === '/settings' }" @click="mobileOpen = false">
          <span class="nav-icon" data-icon="settings"></span> Settings
        </RouterLink>
        <button class="profile-mini" @click="userMenuOpen = !userMenuOpen">
          <span class="avatar">{{ auth.user?.first_name?.charAt(0) }}{{ auth.user?.last_name?.charAt(0) }}</span>
          <span class="profile-text"><strong>{{ auth.user?.first_name }} {{ auth.user?.last_name }}</strong><small>{{ auth.user?.email }}</small></span>
          <span class="chevron">⌄</span>
        </button>
        <div v-if="userMenuOpen" class="user-menu">
          <RouterLink to="/settings" @click="userMenuOpen = false">Account settings</RouterLink>
          <button @click="logout">Sign out</button>
        </div>
      </div>
    </aside>

    <div v-if="mobileOpen" class="sidebar-backdrop" @click="mobileOpen = false"></div>

    <main class="main-content">
      <header class="topbar">
        <button class="icon-button menu-toggle" @click="mobileOpen = true">☰</button>
        <div class="topbar-title">
          <span class="eyebrow">Commerce workspace</span>
          <h1>{{ route.path === '/dashboard' ? 'Overview' : route.path.split('/')[1]?.replace('-', ' ') }}</h1>
        </div>
        <div class="topbar-actions">
          <div v-if="auth.tenants.length > 1" class="tenant-switcher">
            <select :value="auth.activeTenantId || ''" @change="auth.setActiveTenant(($event.target as HTMLSelectElement).value)">
              <option v-for="tenant in auth.tenants" :key="tenant.public_id" :value="tenant.public_id">{{ tenant.name }}</option>
            </select>
          </div>
          <RouterLink to="/shops" class="button button-primary button-sm">+ New shop</RouterLink>
        </div>
      </header>
      <section class="page-content"><RouterView /></section>
    </main>
  </div>
</template>