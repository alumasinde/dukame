<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const error = ref('')
const subscription = ref<any>(null)

const activeTenant = computed(() => auth.activeTenant)
const firstName = computed(() => auth.user?.first_name || 'there')
const roleLabel = computed(() => activeTenant.value?.role || 'Member')
const shopInitial = computed(() => activeTenant.value?.name?.charAt(0).toUpperCase() || 'D')

async function load() {
  if (!activeTenant.value) {
    loading.value = false
    return
  }

  loading.value = true
  error.value = ''

  try {
    const { data } = await api.get(`/subscriptions/${activeTenant.value.public_id}`)
    subscription.value = data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Workspace subscription information could not be loaded.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <div v-if="!activeTenant" class="welcome-row">
      <div>
        <span class="eyebrow">Get started</span>
        <h2>Create your store.</h2>
        <p class="lead">Set up your commerce workspace first. Your catalogue and selling workflows will build on it.</p>
      </div>
      <RouterLink to="/shops" class="button button-primary">Create shop</RouterLink>
    </div>

    <template v-else>
      <div class="welcome-row">
        <div>
          <span class="eyebrow">Commerce workspace</span>
          <h2>Good day, {{ firstName }}.</h2>
          <p class="lead">Manage your store, catalogue and selling operations from one workspace.</p>
        </div>
        <RouterLink to="/catalogue/products" class="button button-primary">
          <i class="fa-solid fa-plus" aria-hidden="true"></i>
          Add product
        </RouterLink>
      </div>

      <div v-if="error" class="alert alert-warning">{{ error }}</div>

      <div class="stat-grid">
        <div class="stat-card">
          <span class="stat-label">Store</span>
          <strong>{{ activeTenant.name }}</strong>
          <span class="stat-note">{{ activeTenant.slug }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Catalogue</span>
          <strong>Ready to build</strong>
          <span class="stat-note">Products, categories and options</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Workspace role</span>
          <strong>{{ roleLabel }}</strong>
          <span class="stat-note">Tenant-scoped access</span>
        </div>
        <div class="stat-card accent-stat">
          <span class="stat-label">Subscription</span>
          <strong>{{ loading ? 'Loading…' : subscription?.plan?.name || 'Free' }}</strong>
          <span class="stat-note">{{ subscription?.status || 'Workspace active' }}</span>
        </div>
      </div>

      <div class="dashboard-grid dashboard-foundation-grid">
        <section class="panel panel-large">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">Store setup</span>
              <h3>Build your commerce foundation</h3>
              <p>Complete the core pieces before orders become your daily workflow.</p>
            </div>
          </div>

          <div class="steps">
            <div class="step done">
              <span><i class="fa-solid fa-check" aria-hidden="true"></i></span>
              <div><strong>Workspace ready</strong><small>Your merchant workspace is active.</small></div>
            </div>
            <div class="step">
              <span>2</span>
              <div><strong>Build your catalogue</strong><small>Add categories, products, options and product variants.</small></div>
              <RouterLink to="/catalogue/products">Open catalogue →</RouterLink>
            </div>
            <div class="step">
              <span>3</span>
              <div><strong>Prepare your storefront</strong><small>Keep your store information and selling experience ready for customers.</small></div>
              <RouterLink to="/shops">Manage shop →</RouterLink>
            </div>
            <div class="step">
              <span>4</span>
              <div><strong>Start receiving orders</strong><small>Orders, customers and payments will connect to the catalogue.</small></div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">Workspace</span>
              <h3>Quick actions</h3>
            </div>
          </div>

          <div class="quick-actions">
            <RouterLink to="/catalogue/products" class="quick-action">
              <b><i class="fa-solid fa-box" aria-hidden="true"></i></b>
              <span><strong>Products</strong><small>Build your product catalogue</small></span>
            </RouterLink>
            <RouterLink to="/catalogue/categories" class="quick-action">
              <b><i class="fa-solid fa-layer-group" aria-hidden="true"></i></b>
              <span><strong>Categories</strong><small>Organize your products</small></span>
            </RouterLink>
            <RouterLink to="/shops" class="quick-action">
              <b><i class="fa-solid fa-store" aria-hidden="true"></i></b>
              <span><strong>My shop</strong><small>Store details and setup</small></span>
            </RouterLink>
            <RouterLink to="/team" class="quick-action">
              <b><i class="fa-solid fa-users" aria-hidden="true"></i></b>
              <span><strong>Team</strong><small>Members and permissions</small></span>
            </RouterLink>
          </div>
        </section>
      </div>

      <section class="panel dashboard-next-panel">
        <div class="panel-heading">
          <div>
            <span class="eyebrow">Coming into the workflow</span>
            <h3>Commerce operations</h3>
            <p>The dashboard is structured to grow as each commerce module becomes available.</p>
          </div>
        </div>
        <div class="dashboard-module-grid">
          <RouterLink to="/orders" class="dashboard-module"><span><i class="fa-solid fa-receipt" aria-hidden="true"></i></span><strong>Orders</strong><small>Order processing</small></RouterLink>
          <RouterLink to="/customers" class="dashboard-module"><span><i class="fa-solid fa-users" aria-hidden="true"></i></span><strong>Customers</strong><small>Customer relationships</small></RouterLink>
          <RouterLink to="/payments" class="dashboard-module"><span><i class="fa-solid fa-credit-card" aria-hidden="true"></i></span><strong>Payments</strong><small>Transactions</small></RouterLink>
          <RouterLink to="/analytics" class="dashboard-module"><span><i class="fa-solid fa-chart-line" aria-hidden="true"></i></span><strong>Analytics</strong><small>Business insights</small></RouterLink>
        </div>
      </section>
    </template>

    <section v-if="!activeTenant" class="empty-state">
      <div class="empty-illustration">{{ shopInitial }}</div>
      <h3>Your commerce workspace is waiting</h3>
      <p>Create your first shop to unlock the merchant dashboard and start building your catalogue.</p>
      <RouterLink to="/shops" class="button button-primary">Create your shop</RouterLink>
    </section>
  </div>
</template>

<style scoped>
.dashboard-foundation-grid { align-items: start; }
.dashboard-next-panel { margin-top: 0; }
.dashboard-module-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.dashboard-module { display: flex; flex-direction: column; gap: 5px; padding: 15px; border: 1px solid var(--line); border-radius: var(--radius-md); color: var(--ink); transition: background .15s ease, border-color .15s ease, transform .15s ease; }
.dashboard-module:hover { background: #f8fbfa; border-color: #c7ddd8; text-decoration: none; transform: translateY(-1px); }
.dashboard-module span { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 8px; background: var(--soft); color: var(--primary); }
.dashboard-module strong { font-size: 13px; }
.dashboard-module small { color: var(--muted); font-size: 10px; }

@media (max-width: 900px) {
  .dashboard-module-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 620px) {
  .dashboard-module-grid { grid-template-columns: 1fr; }
}
</style>
