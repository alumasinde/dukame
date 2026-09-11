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
    error.value = err?.response?.data?.detail || 'Subscription details could not be loaded.'
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
        <h2>Create your business</h2>
        <p class="lead">Set up your business once, then start adding products.</p>
      </div>
      <RouterLink to="/shops" class="button button-primary">Create business</RouterLink>
    </div>

    <template v-else>
      <div class="welcome-row">
        <div>
          <span class="eyebrow">Overview</span>
          <h2>Good day, {{ firstName }}.</h2>
          <p class="lead">Here is what is happening with {{ activeTenant.name }}.</p>
        </div>
        <RouterLink to="/catalogue/products/new" class="button button-primary"><i class="fa-solid fa-plus" aria-hidden="true"></i> Add product</RouterLink>
      </div>

      <div v-if="error" class="alert alert-warning">{{ error }}</div>

      <div class="stat-grid">
        <div class="stat-card"><span class="stat-label">Business</span><strong>{{ activeTenant.name }}</strong><span class="stat-note">{{ activeTenant.slug }}</span></div>
        <div class="stat-card"><span class="stat-label">Catalogue</span><strong>Ready to build</strong><span class="stat-note">Products, categories and variants</span></div>
        <div class="stat-card"><span class="stat-label">Role</span><strong class="text-capitalize">{{ roleLabel }}</strong><span class="stat-note">Your access level</span></div>
        <div class="stat-card accent-stat"><span class="stat-label">Plan</span><strong>{{ loading ? 'Loading…' : subscription?.plan?.name || 'Free' }}</strong><span class="stat-note">{{ subscription?.status || 'Active' }}</span></div>
      </div>

      <div class="dashboard-grid dashboard-foundation-grid">
        <section class="panel panel-large">
          <div class="panel-heading"><div><span class="eyebrow">Getting started</span><h3>Set up your shop</h3><p>Add the basics before you start taking orders.</p></div></div>
          <div class="steps">
            <div class="step done"><span><i class="fa-solid fa-check" aria-hidden="true"></i></span><div><strong>Business created</strong><small>Your shop is ready to configure.</small></div></div>
            <div class="step"><span>2</span><div><strong>Build your catalogue</strong><small>Add products and organise them with categories and options.</small></div><RouterLink to="/catalogue/products">Open catalogue →</RouterLink></div>
            <div class="step"><span>3</span><div><strong>Set up your shop</strong><small>Add the details customers will see.</small></div><RouterLink to="/shops">Manage shop →</RouterLink></div>
            <div class="step"><span>4</span><div><strong>Start selling</strong><small>Orders, customers and payments will follow as you sell.</small></div></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-heading"><div><span class="eyebrow">Shortcuts</span><h3>Quick actions</h3></div></div>
          <div class="quick-actions">
            <RouterLink to="/catalogue/products/new" class="quick-action"><b><i class="fa-solid fa-box" aria-hidden="true"></i></b><span><strong>Add product</strong><small>Create a product for your catalogue</small></span></RouterLink>
            <RouterLink to="/catalogue/categories" class="quick-action"><b><i class="fa-solid fa-layer-group" aria-hidden="true"></i></b><span><strong>Categories</strong><small>Organise your products</small></span></RouterLink>
            <RouterLink to="/shops" class="quick-action"><b><i class="fa-solid fa-store" aria-hidden="true"></i></b><span><strong>Shop settings</strong><small>Update your shop details</small></span></RouterLink>
            <RouterLink to="/team" class="quick-action"><b><i class="fa-solid fa-users" aria-hidden="true"></i></b><span><strong>Team</strong><small>Manage members and access</small></span></RouterLink>
          </div>
        </section>
      </div>

      <section class="panel dashboard-next-panel">
        <div class="panel-heading"><div><span class="eyebrow">Your business</span><h3>Commerce operations</h3><p>More tools will become part of the workflow as you grow.</p></div></div>
        <div class="dashboard-module-grid">
          <RouterLink to="/orders" class="dashboard-module"><span><i class="fa-solid fa-receipt" aria-hidden="true"></i></span><strong>Orders</strong><small>Manage sales</small></RouterLink>
          <RouterLink to="/customers" class="dashboard-module"><span><i class="fa-solid fa-users" aria-hidden="true"></i></span><strong>Customers</strong><small>Customer records</small></RouterLink>
          <RouterLink to="/payments" class="dashboard-module"><span><i class="fa-solid fa-credit-card" aria-hidden="true"></i></span><strong>Payments</strong><small>Payment activity</small></RouterLink>
          <RouterLink to="/analytics" class="dashboard-module"><span><i class="fa-solid fa-chart-line" aria-hidden="true"></i></span><strong>Analytics</strong><small>Business performance</small></RouterLink>
        </div>
      </section>
    </template>

    <section v-if="!activeTenant" class="empty-state"><div class="empty-illustration">{{ shopInitial }}</div><h3>Create your first business</h3><p>Once it is created, your shop and workspace are ready automatically.</p><RouterLink to="/shops" class="button button-primary">Create business</RouterLink></section>
  </div>
</template>
