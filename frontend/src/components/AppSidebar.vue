<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { LayoutDashboard, Package, FolderOpen, ShoppingCart, Users, CreditCard, BarChart3, Settings, LogOut, Menu, X, ChevronDown } from '@lucide/vue'

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
function toggleGroup(key: string) { openGroups.value[key] = !openGroups.value[key] }
function navigate(path: string) { router.push(path); mobileMenuOpen.value = false }
async function handleLogout() { await auth.logout(); router.push('/login') }
watch(currentPath, path => { if (path.startsWith('/catalogue/')) openGroups.value.catalogue = true })
</script>

<template>
  <aside class="sidebar">
    <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen" aria-label="Toggle navigation">
      <Menu v-if="!mobileMenuOpen" :size="22" /><X v-else :size="22" />
    </button>
    <div :class="['sidebar-content', { open: mobileMenuOpen }]">
      <button class="logo" type="button" @click="navigate('/dashboard')">
        <span class="logo-icon">D</span><span class="logo-text">DukaMe</span>
      </button>
      <div class="shop-info">
        <div class="shop-avatar">{{ auth.activeTenant?.name?.charAt(0)?.toUpperCase() || 'S' }}</div>
        <div class="shop-details"><p class="shop-name">{{ auth.activeTenant?.name || 'Your workspace' }}</p><p class="shop-role">{{ auth.activeTenant?.role || 'Owner' }}</p></div>
        <ChevronDown :size="15" class="shop-chevron" />
      </div>
      <div class="nav-label">Workspace</div>
      <nav class="nav-list" aria-label="Main navigation">
        <div v-for="item in navItems" :key="item.name" class="nav-group">
          <button v-if="item.children" class="nav-link nav-parent" :class="{ active: isActive(item.path) }" type="button" @click="toggleGroup(item.key!)">
            <component :is="item.icon" :size="18" /><span>{{ item.name }}</span><ChevronDown :size="15" class="group-chevron" :class="{ rotated: openGroups[item.key!] }" />
          </button>
          <button v-else class="nav-link" :class="{ active: isActive(item.path) }" type="button" @click="navigate(item.path)"><component :is="item.icon" :size="18" /><span>{{ item.name }}</span></button>
          <div v-if="item.children && openGroups[item.key!]" class="subnav">
            <button v-for="child in item.children" :key="child.path" class="subnav-link" :class="{ active: isActive(child.path) }" type="button" @click="navigate(child.path)"><component :is="child.icon" :size="15" /><span>{{ child.name }}</span></button>
          </div>
        </div>
      </nav>
      <div class="sidebar-spacer" />
      <button class="logout-btn" type="button" @click="handleLogout"><LogOut :size="18" /><span>Sign out</span></button>
      <div class="sidebar-footer">DukaMe commerce workspace</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar{width:248px;min-width:248px;height:100vh;position:sticky;top:0;background:#102a27;color:#dce9e7;display:flex;z-index:30}.sidebar-content{height:100%;min-height:0;overflow-y:auto;padding:18px 14px 14px;display:flex;flex-direction:column}.mobile-menu-btn{display:none}.logo{width:100%;display:flex;align-items:center;gap:10px;padding:4px 8px 20px;border:0;background:none;color:#fff;text-align:left}.logo-icon{width:36px;height:36px;display:grid;place-items:center;border-radius:10px;background:#18b7a6;color:#fff;font-weight:850;box-shadow:0 7px 18px rgb(24 183 166 / .18)}.logo-text{font-size:19px;font-weight:800;letter-spacing:-.025em}.shop-info{display:flex;align-items:center;gap:10px;padding:11px;margin-bottom:22px;background:#173a35;border:1px solid #28504a;border-radius:12px}.shop-avatar{width:36px;height:36px;flex:0 0 36px;display:grid;place-items:center;border-radius:10px;background:#d8f4ee;color:#086e64;font-weight:800}.shop-details{min-width:0;flex:1}.shop-name,.shop-role{margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.shop-name{color:#fff;font-size:12px;font-weight:750}.shop-role{margin-top:3px;color:#8eaaa5;font-size:10px;text-transform:capitalize}.shop-chevron{color:#7f9d98}.nav-label{padding:0 10px 8px;color:#6f8d88;font-size:9px;font-weight:800;letter-spacing:.11em;text-transform:uppercase}.nav-list,.nav-group,.subnav{display:flex;flex-direction:column}.nav-list{gap:3px}.nav-link,.subnav-link,.logout-btn{width:100%;display:flex;align-items:center;border:0;background:transparent;color:#9bb4b0;text-align:left;font-weight:650;transition:background .15s ease,color .15s ease}.nav-link{min-height:42px;gap:11px;padding:0 11px;border-radius:9px;font-size:12px}.nav-link:hover,.nav-link.active{color:#fff;background:#173b36}.nav-link.active{box-shadow:inset 3px 0 0 #18b7a6}.group-chevron{margin-left:auto;transition:transform .18s ease}.group-chevron.rotated{transform:rotate(180deg)}.subnav{gap:2px;padding:3px 0 4px 14px}.subnav-link{min-height:36px;gap:9px;padding:0 10px;border-left:1px solid #31534e;color:#88a5a0;font-size:11px;border-radius:0 8px 8px 0}.subnav-link:hover{color:#fff;background:#173a35}.subnav-link.active{color:#bff2ea;background:#1a433e;border-left:2px solid #18b7a6}.sidebar-spacer{flex:1;min-height:30px}.logout-btn{min-height:42px;gap:11px;padding:0 11px;border-radius:9px;font-size:12px}.logout-btn:hover{color:#ffd5d1;background:rgb(180 35 24 / .12)}.sidebar-footer{padding:12px 10px 2px;color:#5f7e79;font-size:9px}@media(max-width:800px){.sidebar{width:100%;min-width:0;height:auto;position:fixed;top:0;left:0;background:transparent;pointer-events:none}.mobile-menu-btn{display:grid;place-items:center;position:absolute;top:13px;right:14px;width:42px;height:42px;border:1px solid #31554f;border-radius:10px;background:#102a27;color:#fff;pointer-events:auto;z-index:2}.sidebar-content{display:none;width:min(310px,88vw);height:100vh;padding-top:16px;pointer-events:auto;box-shadow:20px 0 50px rgb(15 37 34 / .2)}.sidebar-content.open{display:flex}}
</style>
