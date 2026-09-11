<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppSidebar from '../components/AppSidebar.vue'

const auth = useAuthStore()
const router = useRouter()

function changeTenant(event: Event) {
  auth.setActiveTenant((event.target as HTMLSelectElement).value)
}

async function handleNewShop() {
  router.push('/shops')
}
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    
    <main class="main-content">
      <header class="topbar">
        <div class="topbar-left">
          <span class="eyebrow">Commerce workspace</span>
          <h1>{{ auth.activeTenant?.name || 'Shop' }}</h1>
        </div>
        
        <div class="topbar-right">
          <div v-if="auth.tenants.length > 1" class="tenant-select">
            <select :value="auth.activeTenantId || ''" @change="changeTenant" aria-label="Switch shop">
              <option v-for="tenant in auth.tenants" :key="tenant.public_id" :value="tenant.public_id">
                {{ tenant.name }}
              </option>
            </select>
          </div>
          <button class="button button-primary" @click="handleNewShop">
            <span>+</span> New shop
          </button>
        </div>
      </header>

      <section class="page-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: #f8f9fa;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  gap: 24px;
}

.topbar-left {
  flex: 1;
}

.eyebrow {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 4px;
}

.topbar-left h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tenant-select {
  position: relative;
}

.tenant-select select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L6 6L11 1' stroke='%236B7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 28px;
}

.button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease;
}

.button-primary {
  background: #14b8a6;
  color: white;
}

.button-primary:hover {
  background: #0d9488;
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

@media (max-width: 768px) {
  .topbar {
    padding: 12px 16px;
    flex-wrap: wrap;
  }

  .topbar-right {
    width: 100%;
  }

  .page-content {
    padding: 16px;
  }
}
</style>
