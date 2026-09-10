<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore(); const plans = ref<any[]>([]); const current = ref<any>(null); const loading = ref(true); const busy = ref(''); const error = ref('')
const interval = ref('monthly')
const money = (minor: number, currency = 'KES') => new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 0 }).format((minor || 0) / 100)
async function load() { if (!auth.activeTenant) { loading.value = false; return } try { const [p, s] = await Promise.all([api.get('/subscriptions/plans'), api.get(`/subscriptions/${auth.activeTenant.public_id}`)]); plans.value = p.data; current.value = s.data } catch (err: any) { error.value = err?.response?.data?.detail || 'Unable to load billing.' } finally { loading.value = false } }
async function changePlan(plan: any) { if (!auth.activeTenant || plan.public_id === current.value?.plan?.public_id) return; busy.value = plan.public_id; error.value = ''; try { const { data } = await api.post(`/subscriptions/${auth.activeTenant.public_id}/change`, { plan_public_id: plan.public_id, billing_interval: interval.value }); current.value = data } catch (err: any) { error.value = err?.response?.data?.detail || 'Plan change could not be completed.' } finally { busy.value = '' } }
onMounted(load)
</script>

<template>
  <div class="page-stack"><div class="section-intro"><div><span class="eyebrow">Subscription</span><h2>Plans that grow with your shop</h2><p class="lead">Your subscription is attached to the selected workspace.</p></div><select v-model="interval" class="select-control"><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="yearly">Yearly</option></select></div>
    <div v-if="error" class="alert alert-warning">{{ error }}</div>
    <div v-if="current" class="current-plan"><div><span class="stat-label">Current plan</span><strong>{{ current.plan.name }}</strong><span>{{ current.status }} · {{ current.billing_interval }}</span></div><span class="plan-chip">{{ current.plan.description || 'Active workspace plan' }}</span></div>
    <div class="pricing-grid"><article v-for="plan in plans" :key="plan.public_id" class="pricing-card" :class="{ featured: plan.public_id === current?.plan?.public_id }"><div class="plan-top"><span class="badge">{{ plan.name }}</span><span v-if="plan.public_id === current?.plan?.public_id" class="current-label">Current</span></div><h3>{{ plan.name }}</h3><p>{{ plan.description || 'A flexible plan for your commerce workspace.' }}</p><div class="plan-price"><strong>{{ money(interval === 'monthly' ? plan.monthly_price_minor : interval === 'quarterly' ? plan.quarterly_price_minor : plan.yearly_price_minor, plan.currency) }}</strong><small>/ {{ interval }}</small></div><div class="feature-list"><div v-for="feature in plan.features" :key="feature.feature_key"><span>✓</span>{{ feature.feature_key }} <small>{{ typeof feature.value === 'object' ? JSON.stringify(feature.value) : feature.value }}</small></div></div><button class="button" :class="plan.public_id === current?.plan?.public_id ? 'button-muted' : 'button-primary'" :disabled="busy === plan.public_id || plan.public_id === current?.plan?.public_id" @click="changePlan(plan)">{{ busy === plan.public_id ? 'Updating…' : plan.public_id === current?.plan?.public_id ? 'Current plan' : 'Choose plan' }}</button></article></div>
    <div v-if="loading" class="loading-block">Loading your plans…</div>
  </div>
</template>