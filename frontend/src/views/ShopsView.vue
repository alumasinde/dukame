<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore, type Tenant } from '../stores/auth'
import { api } from '../lib/api'

const router = useRouter()
const auth = useAuthStore()
const name = ref('')
const slug = ref('')
const saving = ref(false)
const switching = ref('')
const error = ref('')
const shops = computed(() => auth.tenants)
const storefrontBase = window.location.origin

function suggestSlug() {
  slug.value = name.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100)
}

function storeUrl(shop: Tenant) {
  return `${storefrontBase}/${shop.slug}`
}

async function createBusiness() {
  error.value = ''
  if (!name.value.trim()) {
    error.value = 'Enter your business name.'
    return
  }
  saving.value = true
  try {
    const { data } = await api.post<Tenant>('/tenants', { name: name.value.trim(), slug: slug.value || undefined })
    auth.tenants.push(data)
    auth.setActiveTenant(data.public_id)
    name.value = ''
    slug.value = ''
    await router.push('/dashboard')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.response?.data?.message || 'We could not create the business.'
  } finally {
    saving.value = false
  }
}

async function selectBusiness(shop: Tenant) {
  if (shop.public_id === auth.activeTenantId) {
    await router.push('/dashboard')
    return
  }
  switching.value = shop.public_id
  try {
    auth.setActiveTenant(shop.public_id)
    await router.push('/dashboard')
  } finally {
    switching.value = ''
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="section-intro">
      <div><span class="eyebrow">Account</span><h2>Businesses</h2><p class="lead">Switch between the businesses you manage.</p></div>
    </div>

    <div class="shop-layout">
      <section class="panel">
        <div class="panel-heading"><div><h3>New business</h3><p>Create another business and start managing its shop.</p></div></div>
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <form class="form-stack" @submit.prevent="createBusiness">
          <label>Business name<input v-model="name" @blur="suggestSlug" placeholder="e.g. Best Collections" required /></label>
          <label>Store link<div class="input-prefix"><span>dukame.shop/</span><input v-model="slug" placeholder="best-collections" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></div></label>
          <button class="button button-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create business' }}</button>
        </form>
      </section>

      <section class="panel">
        <div class="panel-heading"><div><h3>Your businesses</h3><p>Choose the business you want to manage.</p></div></div>
        <div v-if="!shops.length" class="mini-empty">No businesses yet.</div>
        <div v-else class="shop-list">
          <article v-for="shop in shops" :key="shop.public_id" class="shop-card" :class="{ selected: shop.public_id === auth.activeTenantId }">
            <button class="shop-row" :disabled="switching === shop.public_id" @click="selectBusiness(shop)">
              <span class="shop-logo">{{ shop.name.charAt(0).toUpperCase() }}</span>
              <span><strong>{{ shop.name }}</strong><small>{{ shop.slug }} · {{ shop.role }}</small></span>
              <span class="row-arrow" aria-hidden="true">{{ switching === shop.public_id ? '…' : shop.public_id === auth.activeTenantId ? '✓' : '→' }}</span>
            </button>
            <a class="storefront-link" :href="storeUrl(shop)" target="_blank" rel="noopener">View store <span>↗</span></a>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
