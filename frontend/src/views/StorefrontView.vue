<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getStorefront, type Storefront } from '../lib/storefront'

const route = useRoute()
const store = ref<Storefront | null>(null)
const loading = ref(true)
const error = ref('')
const selectedCategory = ref('')
const searchQuery = ref('')

const filteredProducts = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return store.value?.products.filter(product => {
    const matchesCategory = !selectedCategory.value || product.category?.public_id === selectedCategory.value
    if (!matchesCategory) return false
    if (!query) return true
    return [product.name, product.description || '', product.sku || '', product.category?.name || ''].some(value => value.toLowerCase().includes(query))
  }) || []
})

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}

function image(product: Storefront['products'][number]) {
  return product.media[0]?.url || ''
}

function hasDiscount(product: Storefront['products'][number]) {
  return product.compare_at_price_minor != null && product.compare_at_price_minor > product.price_minor
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
        <RouterLink :to="`/${store.slug}`" class="storefront-brand storefront-brand-link"><span class="storefront-mark">{{ store.name.charAt(0).toUpperCase() }}</span><div><strong>{{ store.name }}</strong><small>Powered by DukaMe</small></div></RouterLink>
        <div class="storefront-header-actions"><button class="storefront-cart" type="button" disabled>Cart <span>0</span></button></div>
      </header>

      <section class="storefront-hero">
        <div><span class="storefront-eyebrow">Welcome to our store</span><h1>{{ store.name }}</h1><p>{{ store.description || 'Browse our latest products and find something you will love.' }}</p></div>
      </section>

      <section class="storefront-content">
        <div class="storefront-toolbar">
          <div><h2>Shop</h2><p>{{ filteredProducts.length }} product{{ filteredProducts.length === 1 ? '' : 's' }}</p></div>
          <label class="storefront-search" aria-label="Search products">
            <span aria-hidden="true">⌕</span>
            <input v-model="searchQuery" type="search" placeholder="Search products" autocomplete="off" />
            <button v-if="searchQuery" type="button" aria-label="Clear search" @click="searchQuery = ''">×</button>
          </label>
        </div>

        <div class="storefront-filter-row">
          <div v-if="store.categories.length" class="storefront-categories" aria-label="Product categories">
            <button type="button" :class="{ active: !selectedCategory }" @click="selectedCategory = ''">All</button>
            <button v-for="category in store.categories" :key="category.public_id" type="button" :class="{ active: selectedCategory === category.public_id }" @click="selectedCategory = category.public_id">{{ category.name }}</button>
          </div>
        </div>

        <div v-if="filteredProducts.length" class="storefront-grid">
          <RouterLink v-for="product in filteredProducts" :key="product.public_id" :to="`/${store.slug}/products/${product.slug}`" class="storefront-product">
            <div class="storefront-product-image">
              <img v-if="image(product)" :src="image(product)" :alt="product.media[0]?.alt_text || product.name" loading="lazy" />
              <span v-else>No image</span>
              <span v-if="hasDiscount(product)" class="storefront-sale-badge">Sale</span>
            </div>
            <div class="storefront-product-info">
              <small v-if="product.category">{{ product.category.name }}</small>
              <h3>{{ product.name }}</h3>
              <div class="storefront-product-price"><strong>{{ money(product.price_minor, product.currency) }}</strong><del v-if="hasDiscount(product)">{{ money(product.compare_at_price_minor!, product.currency) }}</del></div>
              <span class="storefront-view-product">View product <span aria-hidden="true">→</span></span>
            </div>
          </RouterLink>
        </div>
        <div v-else-if="searchQuery || selectedCategory" class="storefront-empty storefront-empty-search"><div class="storefront-empty-icon">⌕</div><h2>No products found</h2><p>Try a different search or category.</p><button class="button button-secondary" type="button" @click="searchQuery = ''; selectedCategory = ''">Clear filters</button></div>
        <div v-else class="storefront-empty"><div class="storefront-empty-icon">⌂</div><h2>No products yet</h2><p>This store is getting ready. Please check back soon.</p></div>
      </section>

      <footer class="storefront-footer">{{ store.name }} · Powered by DukaMe</footer>
    </template>
  </main>
</template>
