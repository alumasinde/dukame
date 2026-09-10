<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore(); const loading = ref(true); const error = ref('')
const subscription = ref<any>(null); const plans = ref<any[]>([])
const activeTenant = computed(() => auth.activeTenant)

async function load() {
  if (!activeTenant.value) { loading.value = false; return }
  try {
    const [sub, planList] = await Promise.all([
      api.get(`/subscriptions/${activeTenant.value.public_id}`),
      api.get('/subscriptions/plans'),
    ])
    subscription.value = sub.data; plans.value = planList.data
  } catch (err: any) { error.value = err?.response?.data?.detail || 'Some workspace data could not be loaded.' }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <div class="welcome-row"><div><span class="eyebrow">{{ activeTenant ? 'Your business at a glance' : 'First step' }}</span><h2>{{ activeTenant ? `Good evening, ${auth.user?.first_name}.` : 'Create your first shop.' }}</h2><p class="lead">{{ activeTenant ? 'Keep your storefront, customers and sales moving.' : 'Set up a workspace and start building your DukaMe storefront.' }}</p></div><RouterLink v-if="!activeTenant" to="/shops" class="button button-primary">Create shop</RouterLink></div>
    <div v-if="error" class="alert alert-warning">{{ error }}</div>
    <template v-if="activeTenant">
      <div class="stat-grid">
        <div class="stat-card"><span class="stat-label">Active shop</span><strong>{{ activeTenant.name }}</strong><span class="stat-note">{{ activeTenant.slug }}</span></div>
        <div class="stat-card"><span class="stat-label">Plan</span><strong>{{ loading ? 'Loading…' : subscription?.plan?.name || 'Free' }}</strong><span class="stat-note">{{ subscription?.status || 'Workspace active' }}</span></div>
        <div class="stat-card"><span class="stat-label">Team role</span><strong>{{ activeTenant.role }}</strong><span class="stat-note">Workspace access</span></div>
        <div class="stat-card accent-stat"><span class="stat-label">Next milestone</span><strong>First order</strong><span class="stat-note">Add products and share your shop</span></div>
      </div>
      <div class="dashboard-grid">
        <section class="panel panel-large"><div class="panel-heading"><div><span class="eyebrow">Getting started</span><h3>Build your selling flow</h3></div></div><div class="steps"><div class="step done"><span>1</span><div><strong>Account ready</strong><small>Your merchant account is active.</small></div></div><div class="step"><span>2</span><div><strong>Add your products</strong><small>Create categories, products and pricing.</small></div><RouterLink to="/shops">Open shop →</RouterLink></div><div class="step"><span>3</span><div><strong>Share your storefront</strong><small>Turn your shop link into your WhatsApp selling point.</small></div></div><div class="step"><span>4</span><div><strong>Receive your first order</strong><small>Orders will become the center of your daily workflow.</small></div></div></div></section>
        <section class="panel"><div class="panel-heading"><div><span class="eyebrow">Workspace</span><h3>Quick actions</h3></div></div><div class="quick-actions"><RouterLink to="/shops" class="quick-action"><b>＋</b><span><strong>Manage shop</strong><small>Store setup and catalogue</small></span></RouterLink><RouterLink to="/team" class="quick-action"><b>♙</b><span><strong>Manage team</strong><small>Members and permissions</small></span></RouterLink><RouterLink to="/billing" class="quick-action"><b>◈</b><span><strong>View plan</strong><small>Subscription and features</small></span></RouterLink></div></section>
      </div>
    </template>
    <section v-else class="empty-state"><div class="empty-illustration">D</div><h3>Your commerce workspace is waiting</h3><p>Create a shop name and slug. Products, categories and orders will plug into this workspace in the next catalogue phase.</p><RouterLink to="/shops" class="button button-primary">Create your shop</RouterLink></section>
  </div>
</template>