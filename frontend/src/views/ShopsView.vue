<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuthStore, type Tenant } from '../stores/auth'
import { api } from '../lib/api'

const auth = useAuthStore(); const name = ref(''); const slug = ref(''); const saving = ref(false); const error = ref(''); const success = ref('')
const shops = computed(() => auth.tenants)

function suggestSlug() { slug.value = name.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
async function createShop() {
  error.value = ''; success.value = ''
  if (!name.value.trim()) { error.value = 'Enter your shop name.'; return }
  saving.value = true
  try {
    const { data } = await api.post<Tenant>('/tenants', { name: name.value.trim(), slug: slug.value || undefined })
    auth.tenants.push(data); auth.setActiveTenant(data.public_id); name.value = ''; slug.value = ''; success.value = `${data.name} is ready.`
  } catch (err: any) { error.value = err?.response?.data?.detail || err?.response?.data?.message || 'We could not create the shop.' }
  finally { saving.value = false }
}
</script>

<template>
  <div class="page-stack"><div class="section-intro"><div><span class="eyebrow">Commerce workspaces</span><h2>My shops</h2><p class="lead">Each shop has its own catalogue, team access and subscription context.</p></div></div>
    <div class="shop-layout"><section class="panel"><div class="panel-heading"><div><h3>Create a shop</h3><p>Start with the identity customers will see.</p></div></div><div v-if="error" class="alert alert-danger">{{ error }}</div><div v-if="success" class="alert alert-success">{{ success }}</div><form class="form-stack" @submit.prevent="createShop"><label>Shop name<input v-model="name" @blur="suggestSlug" placeholder="e.g. Mama Njeri Home Store" required /></label><label>Shop slug <span class="muted">(optional)</span><div class="input-prefix"><span>dukame.shop/</span><input v-model="slug" placeholder="mama-njeri" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></div></label><button class="button button-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create shop' }}</button></form></section>
    <section class="panel"><div class="panel-heading"><div><h3>Your workspaces</h3><p>{{ shops.length }} shop{{ shops.length === 1 ? '' : 's' }} available</p></div></div><div v-if="!shops.length" class="mini-empty">No shops yet.</div><button v-for="shop in shops" :key="shop.public_id" class="shop-row" :class="{ selected: shop.public_id === auth.activeTenantId }" @click="auth.setActiveTenant(shop.public_id)"><span class="shop-logo">{{ shop.name.charAt(0).toUpperCase() }}</span><span><strong>{{ shop.name }}</strong><small>{{ shop.slug }} · {{ shop.role }}</small></span><span class="row-arrow">→</span></button></section></div>
  </div>
</template>