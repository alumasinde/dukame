<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppSidebar from '../components/AppSidebar.vue'

const auth = useAuthStore()
const route = useRoute()
const pageLabel = computed(() => {
  const map: Record<string, string> = { dashboard: 'Overview', 'catalogue-products': 'Products', 'catalogue-product-new': 'New product', 'catalogue-product-editor': 'Edit product', 'catalogue-categories': 'Categories', 'catalogue-options': 'Options & variants', shops: 'Shop', billing: 'Billing', team: 'Team', settings: 'Settings', orders: 'Orders', customers: 'Customers', analytics: 'Analytics' }
  return map[String(route.name)] || 'Workspace'
})

function changeTenant(event: Event) { auth.setActiveTenant((event.target as HTMLSelectElement).value) }
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="main-content">
      <header class="topbar">
        <div class="topbar-left"><span class="topbar-context">{{ auth.activeTenant?.name || 'Business' }}</span><span class="topbar-separator">/</span><strong>{{ pageLabel }}</strong></div>
        <div class="topbar-right">
          <label v-if="auth.tenants.length > 1" class="tenant-select"><span class="sr-only">Switch business</span><select :value="auth.activeTenantId || ''" @change="changeTenant"><option v-for="tenant in auth.tenants" :key="tenant.public_id" :value="tenant.public_id">{{ tenant.name }}</option></select></label>
          <RouterLink to="/shops" class="topbar-shop-link">Manage shop</RouterLink>
        </div>
      </header>
      <section class="page-content"><RouterView /></section>
    </main>
  </div>
</template>
