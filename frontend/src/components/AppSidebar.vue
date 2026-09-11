<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { APP_NAME, APP_TAGLINE, APP_MARK } from '../lib/branding'
import { LayoutDashboard, Package, FolderOpen, ShoppingCart, Users, CreditCard, BarChart3, Settings, LogOut, Menu, X, ChevronDown, PanelLeftClose, PanelLeftOpen } from '@lucide/vue'

const props = defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ toggleCollapse: [] }>()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const mobileMenuOpen = ref(false)
const openGroups = ref<Record<string, boolean>>({ catalogue: true })
const navItems = [
  { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Catalogue', path: '/catalogue/products', key: 'catalogue', icon: Package, children: [
    { name: 'Products', path: '/catalogue/products', icon: Package },
    { name: 'Categories', path: '/catalogue/categories', icon: FolderOpen },
    { name: 'Options & variants', path: '/catalogue/options', icon: Package },
  ]},
  { name: 'Orders', path: '/orders', icon: ShoppingCart },
  { name: 'Customers', path: '/customers', icon: Users },
  { name: 'Payments', path: '/billing', icon: CreditCard },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Settings', path: '/settings', icon: Settings },
]
const currentPath = computed(() => route.path)
function isActive(path: string) { return currentPath.value === path || currentPath.value.startsWith(`${path}/`) }
function toggleGroup(key: string) { if (key === 'catalogue' && props.collapsed) { emit('toggleCollapse'); openGroups.value[key] = true; return }; openGroups.value[key] = !openGroups.value[key] }
function navigate(path: string) { router.push(path); mobileMenuOpen.value = false }
async function handleLogout() { await auth.logout(); router.push('/login') }
watch(currentPath, path => { if (path.startsWith('/catalogue/')) openGroups.value.catalogue = true })
</script>

<template>
  <aside :class="['sidebar', { collapsed }]">
    <div class="sidebar-content" :class="{ open: mobileMenuOpen }">
      <div class="sidebar-header">
        <button class="logo" type="button" @click="navigate('/dashboard')" :aria-label="`${APP_NAME} home`" :title="APP_TAGLINE">
          <span class="logo-icon">{{ APP_MARK }}</span><span class="logo-text">{{ APP_NAME }}</span>
        </button>
        <button class="sidebar-toggle" type="button" :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'" :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'" @click="emit('toggleCollapse')"><PanelLeftOpen v-if="collapsed" :size="17" /><PanelLeftClose v-else :size="17" /></button>
      </div>
      <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen" :aria-label="mobileMenuOpen ? 'Close navigation' : 'Open navigation'"><Menu v-if="!mobileMenuOpen" :size="22" /><X v-else :size="22" /></button>
      <div class="shop-info">
        <div class="shop-avatar">{{ auth.activeTenant?.name?.charAt(0)?.toUpperCase() || 'S' }}</div>
        <div class="shop-details"><p class="shop-name">{{ auth.activeTenant?.name || 'Your business' }}</p><p class="shop-role">{{ auth.activeTenant?.role || 'Owner' }}</p></div>
        <ChevronDown :size="15" class="shop-chevron" />
      </div>
      <div class="nav-label">Workspace</div>
      <nav class="nav-list" aria-label="Main navigation">
        <div v-for="item in navItems" :key="item.name" class="nav-group">
          <button v-if="item.children" class="nav-link nav-parent" :class="{ active: isActive(item.path) }" type="button" :title="collapsed ? item.name : undefined" @click="toggleGroup(item.key!)"><component :is="item.icon" :size="18" /><span>{{ item.name }}</span><ChevronDown :size="15" class="group-chevron" :class="{ rotated: openGroups[item.key!] }" /></button>
          <button v-else class="nav-link" :class="{ active: isActive(item.path) }" type="button" :title="collapsed ? item.name : undefined" @click="navigate(item.path)"><component :is="item.icon" :size="18" /><span>{{ item.name }}</span></button>
          <div v-if="item.children && openGroups[item.key!]" class="subnav"><button v-for="child in item.children" :key="child.path" class="subnav-link" :class="{ active: isActive(child.path) }" type="button" @click="navigate(child.path)"><component :is="child.icon" :size="15" /><span>{{ child.name }}</span></button></div>
        </div>
      </nav>
      <div class="sidebar-spacer" />
      <button class="logout-btn" type="button" title="Sign out" @click="handleLogout"><LogOut :size="18" /><span>Sign out</span></button>
      <div class="sidebar-footer">{{ APP_NAME }}</div>
    </div>
  </aside>
</template>
