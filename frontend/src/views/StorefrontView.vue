<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getCart } from '../lib/cart'
import { useCartState } from '../lib/cart-state'
import { getStorefront, type Storefront, type StorefrontCategory, type StorefrontProduct } from '../lib/storefront'

const route = useRoute()
const cartState = useCartState()
const store = ref<Storefront | null>(null)
const loading = ref(true)
const error = ref('')
const selectedCategory = ref('')
const searchQuery = ref('')

const categoryMap = computed(() => new Map((store.value?.categories || []).map(category => [category.public_id, category])))
const topLevelCategories = computed(() => (store.value?.categories || []).filter(category => !category.parent_public_id))
const selectedCategoryItem = computed(() => selectedCategory.value ? categoryMap.value.get(selectedCategory.value) || null : null)
const childCategories = computed(() => selectedCategory.value ? (store.value?.categories || []).filter(category => category.parent_public_id === selectedCategory.value) : [])

function categoryAndAncestors(categoryId: string): Set<string> {
  const ids = new Set<string>()
  let current = categoryMap.value.get(categoryId)
  const visited = new Set<string>()
  while (current && !visited.has(current.public_id)) {
    visited.add(current.public_id)
    ids.add(current.public_id)
    current = current.parent_public_id ? categoryMap.value.get(current.parent_public_id) : undefined
  }
  return ids
}

function belongsToCategory(product: StorefrontProduct, categoryId: string) {
  return !!product.category && categoryAndAncestors(product.category.public_id).has(categoryId)
}

const categoryCounts = computed(() => {
  const counts = new Map<string, number>()
  for (const product of store.value?.products || []) {
    if (!product.category) continue
    for (const categoryId of categoryAndAncestors(product.category.public_id)) counts.set(categoryId, (counts.get(categoryId) || 0) + 1)
  }
  return counts
})

const filteredProducts = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return store.value?.products.filter(product => {
    if (selectedCategory.value && !belongsToCategory(product, selectedCategory.value)) return false
    if (!query) return true
    return [product.name, product.description || '', product.category?.name || ''].some(value => value.toLowerCase().includes(query))
  }) || []
})

const resultLabel = computed(() => {
  if (selectedCategoryItem.value) return `Showing ${selectedCategoryItem.value.name}`
  if (searchQuery.value.trim()) return `Results for “${searchQuery.value.trim()}”`
  return 'All products'
})

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}
function image(product: StorefrontProduct) { return product.media[0]?.url || '' }
function hasDiscount(product: StorefrontProduct) { return product.compare_at_price_minor != null && product.compare_at_price_minor > product.price_minor }
function categoryCount(category: StorefrontCategory) { return categoryCounts.value.get(category.public_id) || 0 }
function selectCategory(id: string) {
  selectedCategory.value = id
  window.scrollTo({ top: document.querySelector('.storefront-products-section')?.getBoundingClientRect().top ? window.scrollY + document.querySelector('.storefront-products-section')!.getBoundingClientRect().top - 90 : 0, behavior: 'smooth' })
}

onMounted(async () => {
  const slug = String(route.params.storeSlug)
  try {
    const [storeResponse, cartResponse] = await Promise.all([getStorefront(slug), getCart(slug)])
    store.value = storeResponse.data
    cartState.set(slug, cartResponse.data)
    document.title = storeResponse.data.name
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
        <RouterLink :to="`/${store.slug}/cart`" class="storefront-cart storefront-cart-link"><span class="storefront-cart-label">Cart</span><span>{{ cartState.itemCount.value }}</span></RouterLink>
      </header>

      <section class="storefront-hero"><div class="storefront-hero-inner"><span class="storefront-eyebrow">Welcome to our store</span><h1>{{ store.name }}</h1><p>{{ store.description || 'Browse our latest products and find something you will love.' }}</p></div></section>

      <section class="storefront-content">
        <div class="storefront-shop-heading"><div><span class="storefront-eyebrow">Shop</span><h2>{{ resultLabel }}</h2><p>{{ filteredProducts.length }} product{{ filteredProducts.length === 1 ? '' : 's' }}</p></div><label class="storefront-search" aria-label="Search products"><span aria-hidden="true">⌕</span><input v-model="searchQuery" type="search" placeholder="Search products…" autocomplete="off" /><button v-if="searchQuery" type="button" aria-label="Clear search" @click="searchQuery = ''">×</button></label></div>

        <div v-if="store.categories.length" class="storefront-category-panel">
          <div class="storefront-category-heading"><strong>Browse categories</strong><span v-if="selectedCategoryItem">{{ selectedCategoryItem.name }}</span></div>
          <div class="storefront-categories" aria-label="Product categories"><button type="button" :class="{ active: !selectedCategory }" @click="selectedCategory = ''">All <span>{{ store.products.length }}</span></button><button v-for="category in topLevelCategories" :key="category.public_id" type="button" :class="{ active: selectedCategory === category.public_id }" @click="selectCategory(category.public_id)">{{ category.name }} <span>{{ categoryCount(category) }}</span></button></div>
          <div v-if="childCategories.length" class="storefront-subcategories"><span class="storefront-subcategory-label">In {{ selectedCategoryItem?.name }}</span><button v-for="category in childCategories" :key="category.public_id" type="button" :class="{ active: selectedCategory === category.public_id }" @click="selectCategory(category.public_id)">{{ category.name }} <span>{{ categoryCount(category) }}</span></button></div>
        </div>

        <div class="storefront-products-section">
          <div v-if="filteredProducts.length" class="storefront-grid"><RouterLink v-for="product in filteredProducts" :key="product.public_id" :to="`/${store.slug}/products/${product.slug}`" class="storefront-product"><div class="storefront-product-image"><img v-if="image(product)" :src="image(product)" :alt="product.media[0]?.alt_text || product.name" loading="lazy" /><span v-else>No image</span><span v-if="hasDiscount(product)" class="storefront-sale-badge">Sale</span></div><div class="storefront-product-info"><small v-if="product.category">{{ product.category.name }}</small><h3>{{ product.name }}</h3><div class="storefront-product-price"><strong>{{ money(product.price_minor, product.currency) }}</strong><del v-if="hasDiscount(product)">{{ money(product.compare_at_price_minor!, product.currency) }}</del></div><span class="storefront-view-product">View product <span aria-hidden="true">→</span></span></div></RouterLink></div>
          <div v-else-if="searchQuery || selectedCategory" class="storefront-empty storefront-empty-search"><div class="storefront-empty-icon">⌕</div><h2>No products found</h2><p>Try another search or browse a different category.</p><button class="button button-secondary" type="button" @click="searchQuery = ''; selectedCategory = ''">Clear filters</button></div>
          <div v-else class="storefront-empty"><div class="storefront-empty-icon">⌂</div><h2>No products yet</h2><p>This store is getting ready. Please check back soon.</p></div>
        </div>
      </section>
      <footer class="storefront-footer">{{ store.name }} · Powered by DukaMe</footer>
    </template>
  </main>
</template>
