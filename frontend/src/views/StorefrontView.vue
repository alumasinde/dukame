<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getStorefront, type Storefront } from '../lib/storefront'

const route = useRoute()
const store = ref<Storefront | null>(null)
const loading = ref(true)
const error = ref('')
const selectedCategory = ref('')

const products = computed(() => selectedCategory.value
  ? store.value?.products.filter(product => product.category?.public_id === selectedCategory.value) || []
  : store.value?.products || [])

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}

function image(product: Storefront['products'][number]) {
  return product.media[0]?.url || ''
}

onMounted(async () => {
  try {
    const response = await getStorefront(String(route.params.storeSlug))
    store.value = response.data
    document.title = response.data.name
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'This store could not be found.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="storefront-page">
    <div v-if="loading" class="storefront-state"><div class="status-spinner" /><p>Loading store…</p></div>
    <div v-else-if="error" class="storefront-state"><div class="storefront-empty-icon">!</div><h1>Store unavailable</h1><p>{{ error }}</p><RouterLink to="/login" class="button button-primary">Go to DukaMe</RouterLink></div>
    <template v-else-if="store">
      <header class="storefront-header">
        <div class="storefront-brand"><span class="storefront-mark">{{ store.name.charAt(0).toUpperCase() }}</span><div><strong>{{ store.name }}</strong><small>Powered by DukaMe</small></div></div>
        <div class="storefront-header-actions"><button class="storefront-cart" type="button" disabled>Cart <span>0</span></button></div>
      </header>

      <section class="storefront-hero">
        <div><span class="storefront-eyebrow">Welcome to our store</span><h1>{{ store.name }}</h1><p>{{ store.description || 'Browse our latest products and find something you will love.' }}</p></div>
      </section>

      <section class="storefront-content">
        <div class="storefront-toolbar">
          <div><h2>Shop</h2><p>{{ products.length }} product{{ products.length === 1 ? '' : 's' }}</p></div>
          <div v-if="store.categories.length" class="storefront-categories">
            <button type="button" :class="{ active: !selectedCategory }" @click="selectedCategory = ''">All</button>
            <button v-for="category in store.categories" :key="category.public_id" type="button" :class="{ active: selectedCategory === category.public_id }" @click="selectedCategory = category.public_id">{{ category.name }}</button>
          </div>
        </div>

        <div v-if="products.length" class="storefront-grid">
          <RouterLink v-for="product in products" :key="product.public_id" :to="`/${store.slug}/products/${product.slug}`" class="storefront-product">
            <div class="storefront-product-image">
              <img v-if="image(product)" :src="image(product)" :alt="product.media[0]?.alt_text || product.name" />
              <span v-else>No image</span>
            </div>
            <div class="storefront-product-info"><small v-if="product.category">{{ product.category.name }}</small><h3>{{ product.name }}</h3><strong>{{ money(product.price_minor, product.currency) }}</strong><del v-if="product.compare_at_price_minor">{{ money(product.compare_at_price_minor, product.currency) }}</del></div>
          </RouterLink>
        </div>
        <div v-else class="storefront-empty"><div class="storefront-empty-icon">⌂</div><h2>No products yet</h2><p>This store is getting ready. Please check back soon.</p></div>
      </section>

      <footer class="storefront-footer">{{ store.name }} · Powered by DukaMe</footer>
    </template>
  </main>
</template>
