<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  LayoutDashboard,
  Package,
  FolderOpen,
  ShoppingCart,
  Users,
  CreditCard,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
} from '@lucide/vue'

const router = useRouter()
const auth = useAuthStore()
const mobileMenuOpen = ref(false)

const navItems = computed(() => [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Catalogue', path: '/catalogue', icon: Package, children: [
    { name: 'Products', path: '/catalogue/products' },
    { name: 'Categories', path: '/catalogue/categories' },
    { name: 'Options', path: '/catalogue/options' },
  ]},
  { name: 'Orders', path: '/orders', icon: ShoppingCart },
  { name: 'Customers', path: '/customers', icon: Users },
  { name: 'Billing', path: '/billing', icon: CreditCard },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Settings', path: '/settings', icon: Settings },
])

const currentPath = computed(() => router.currentRoute.value.path)

function isActive(path: string) {
  return currentPath.value.startsWith(path)
}

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="sidebar">
    <!-- Mobile menu button -->
    <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen" aria-label="Toggle menu">
      <Menu v-if="!mobileMenuOpen" size="24" />
      <X v-else size="24" />
    </button>

    <!-- Sidebar content -->
    <nav :class="['sidebar-content', { open: mobileMenuOpen }]">
      <!-- Logo -->
      <div class="logo">
        <div class="logo-icon">D</div>
        <span class="logo-text">DukaMe</span>
      </div>

      <!-- Shop info -->
      <div class="shop-info">
        <div class="shop-avatar">{{ auth.user?.first_name?.charAt(0) || 'S' }}</div>
        <div class="shop-details">
          <p class="shop-name">{{ auth.activeTenant?.name || 'Shop' }}</p>
          <p class="shop-role">{{ auth.activeTenant?.role || 'Owner' }}</p>
        </div>
      </div>

      <!-- Navigation items -->
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.path" class="nav-item">
          <button
            class="nav-link"
            :class="{ active: isActive(item.path) }"
            @click="router.push(item.path)"
          >
            <component :is="item.icon" size="20" />
            <span>{{ item.name }}</span>
          </button>
        </li>
      </ul>

      <!-- Logout -->
      <button class="logout-btn" @click="handleLogout">
        <LogOut size="20" />
        <span>Sign out</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  position: relative;
  width: 248px;
  height: 100vh;
  background: #0f3d3a;
  color: white;
  display: flex;
  flex-direction: column;
}

.mobile-menu-btn {
  display: none;
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px;
  z-index: 100;
}

@media (max-width: 768px) {
  .mobile-menu-btn {
    display: flex;
    align-items: center;
  }

  .sidebar {
    width: 100%;
    height: auto;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 50;
  }

  .sidebar-content {
    display: none;
    flex-direction: column;
    padding-top: 60px;
    max-height: calc(100vh - 60px);
    overflow-y: auto;
  }

  .sidebar-content.open {
    display: flex;
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #14b8a6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 18px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
}

.shop-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.shop-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #14b8a6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.shop-details {
  flex: 1;
  min-width: 0;
}

.shop-name {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shop-role {
  margin: 2px 0 0;
  font-size: 12px;
  opacity: 0.7;
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  position: relative;
}

.nav-link {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  transition: all 200ms ease;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-link.active {
  background: rgba(20, 184, 166, 0.2);
  color: #14b8a6;
  border-left: 3px solid #14b8a6;
  padding-left: 9px;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  transition: all 200ms ease;
  margin-top: auto;
}

.logout-btn:hover {
  background: rgba(255, 100, 100, 0.1);
  color: #ff6464;
}
</style>
