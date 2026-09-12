<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useCartState } from '../lib/cart-state'
import { loadFavorites, toggleFavorite as toggleFavoriteStore } from '../lib/favorites'
import { getStorefront, type Storefront, type StorefrontProduct } from '../lib/storefront'
import { APP_NAME } from '../lib/branding'

const route = useRoute()
const cartState = useCartState()
const storeSlug = computed(() => String(route.params.storeSlug))
const store = ref<Storefront | null>(null)
const loading = ref(true)
const error = ref('')
const favorites = ref<string[]>([])

const favoriteProducts = computed(() => {
  const set = new Set(favorites.value)
  return (store.value?.products || []).filter((p) => set.has(p.public_id))
})

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}
function image(product: StorefrontProduct) {
  return product.media[0]?.url || ''
}
function toggleFavorite(productId: string) {
  favorites.value = toggleFavoriteStore(storeSlug.value, productId)
}

onMounted(async () => {
  try {
    const slug = storeSlug.value
    const [response] = await Promise.all([getStorefront(slug), cartState.load(slug)])
    store.value = response.data
    document.title = `Favourites · ${response.data.name}`
    favorites.value = loadFavorites(slug)
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'This store could not be found.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="storefront-page">
    <div v-if="loading" class="storefront-state"><div class="status-spinner" /><p>Loading favourites…</p></div>
    <div v-else-if="error" class="storefront-state">
      <div class="storefront-empty-icon">!</div>
      <h1>Store unavailable</h1>
      <p>{{ error }}</p>
      <RouterLink to="/login" class="button button-primary">Go to {{ APP_NAME }}</RouterLink>
    </div>
    <template v-else-if="store">
      <header class="storefront-header">
        <RouterLink :to="`/${store.slug}`" class="storefront-brand storefront-brand-link">
          <span class="storefront-mark">{{ store.name.charAt(0).toUpperCase() }}</span>
          <div><strong>{{ store.name }}</strong><small>Powered by {{ APP_NAME }}</small></div>
        </RouterLink>
        <div class="storefront-header-actions">
          <RouterLink :to="`/${store.slug}/favourites`" class="storefront-header-link storefront-fav-badge" aria-label="Favourites">
            ♥<span v-if="favorites.length">{{ favorites.length }}</span>
          </RouterLink>
          <RouterLink :to="`/${store.slug}/cart`" class="storefront-header-link">
            Cart <span v-if="cartState.itemCount.value">{{ cartState.itemCount.value }}</span>
          </RouterLink>
        </div>
      </header>

      <section class="storefront-content" style="padding-top: 28px">
        <div class="storefront-shop-heading" style="grid-template-columns: 1fr">
          <div>
            <RouterLink :to="`/${store.slug}`" class="storefront-back">← Back to store</RouterLink>
            <span class="storefront-eyebrow">Saved</span>
            <h2>Your favourites</h2>
            <p>{{ favoriteProducts.length }} item{{ favoriteProducts.length === 1 ? '' : 's' }} saved on this device</p>
          </div>
        </div>

        <div v-if="favoriteProducts.length" class="storefront-grid">
          <article v-for="product in favoriteProducts" :key="product.public_id" class="storefront-product">
            <div class="storefront-product-image">
              <RouterLink :to="`/${store.slug}/products/${product.slug}`" class="storefront-product-link">
                <img v-if="image(product)" :src="image(product)" :alt="product.name" loading="lazy" />
                <span v-else>No image</span>
              </RouterLink>
              <button type="button" class="storefront-wishlist is-favorite" aria-label="Remove from favourites" @click="toggleFavorite(product.public_id)">
                <svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20.84 8.74c0 5.42-8.84 10.26-8.84 10.26S3.16 14.16 3.16 8.74A4.74 4.74 0 0 1 12 6.46a4.74 4.74 0 0 1 8.84 2.28Z" /></svg>
              </button>
            </div>
            <RouterLink :to="`/${store.slug}/products/${product.slug}`" class="storefront-product-link">
              <div class="storefront-product-info">
                <small v-if="product.category">{{ product.category.name }}</small>
                <h3>{{ product.name }}</h3>
                <div class="storefront-product-price"><strong>{{ money(product.price_minor, product.currency) }}</strong></div>
              </div>
            </RouterLink>
            <div class="storefront-product-action">
              <RouterLink :to="`/${store.slug}/products/${product.slug}`" class="storefront-quick-add storefront-options-link">View product</RouterLink>
            </div>
          </article>
        </div>

        <div v-else class="storefront-empty storefront-favourites-empty">
          <div class="storefront-empty-icon">♥</div>
          <h2>No favourites yet</h2>
          <p>Tap the heart on any product to save it here for later.</p>
          <RouterLink :to="`/${store.slug}`" class="button button-primary">Browse the store</RouterLink>
        </div>
      </section>
      <footer class="storefront-footer">{{ store.name }} · Powered by {{ APP_NAME }}</footer>
    </template>
  </main>
</template>
