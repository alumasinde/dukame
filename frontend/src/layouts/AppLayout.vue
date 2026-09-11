<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppSidebar from '../components/AppSidebar.vue'

const auth = useAuthStore()
const router = useRouter()
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
        <div class="topbar-left">
          <span class="topbar-context">{{ auth.activeTenant?.name || 'Workspace' }}</span>
          <span class="topbar-separator">/</span>
          <strong>{{ pageLabel }}</strong>
        </div>
        <div class="topbar-right">
          <label v-if="auth.tenants.length > 1" class="tenant-select">
            <span class="sr-only">Switch workspace</span>
            <select :value="auth.activeTenantId || ''" @change="changeTenant">
              <option v-for="tenant in auth.tenants" :key="tenant.public_id" :value="tenant.public_id">{{ tenant.name }}</option>
            </select>
          </label>
          <RouterLink to="/shops" class="topbar-shop-link">Manage shop</RouterLink>
        </div>
      </header>
      <section class="page-content"><RouterView /></section>
    </main>
  </div>
</template>

<style scoped>
.app-layout{min-height:100vh;display:flex;background:#f6f8f7}.main-content{min-width:0;flex:1;display:flex;flex-direction:column}.topbar{height:68px;flex:0 0 68px;display:flex;align-items:center;gap:20px;padding:0 30px;background:rgb(255 255 255 / .96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px);position:sticky;top:0;z-index:10}.topbar-left{display:flex;align-items:center;gap:9px;min-width:0;color:var(--ink);font-size:13px}.topbar-context{max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted);font-size:12px}.topbar-separator{color:#b8c4c1}.topbar-left strong{font-size:13px}.topbar-right{margin-left:auto;display:flex;align-items:center;gap:10px}.tenant-select select{height:38px;padding:0 30px 0 11px;border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--ink);font-size:12px;box-shadow:var(--shadow-sm)}.topbar-shop-link{height:38px;display:inline-flex;align-items:center;padding:0 12px;border:1px solid #d7e1de;border-radius:9px;color:#36534e;background:#fff;font-size:12px;font-weight:700}.topbar-shop-link:hover{background:#f6faf8;text-decoration:none}.page-content{width:100%;max-width:1440px;margin:0 auto;padding:28px 32px 60px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:800px){.topbar{height:64px;padding:0 68px 0 16px}.topbar-context{max-width:130px}.topbar-right{display:none}.page-content{padding:22px 16px 45px}}
</style>
