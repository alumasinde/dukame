<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getStorefrontProduct, type StorefrontProduct } from '../lib/storefront'

const route = useRoute()
const product = ref<StorefrontProduct | null>(null)
const loading = ref(true)
const error = ref('')
const selectedImage = ref(0)
const descriptionExpanded = ref(false)
const DESCRIPTION_LIMIT = 420

const descriptionPreview = computed(() => {
  const description = product.value?.description || ''
  if (description.length <= DESCRIPTION_LIMIT) return description
  return `${description.slice(0, DESCRIPTION_LIMIT).trimEnd()}…`
})

const hasLongDescription = computed(() => (product.value?.description?.length || 0) > DESCRIPTION_LIMIT)

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}

onMounted(async () => {
  try {
    const response = await getStorefrontProduct(String(route.params.storeSlug), String(route.params.productSlug))
    product.value = response.data
    document.title = response.data.name
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'This product could not be found.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="storefront-page">
    <div v-if="loading" class="storefront-state"><div class="status-spinner" /><p>Loading product…</p></div>
    <div v-else-if="error" class="storefront-state"><div class="storefront-empty-icon">!</div><h1>Product unavailable</h1><p>{{ error }}</p><RouterLink :to="`/${route.params.storeSlug}`" class="button button-primary">Back to store</RouterLink></div>
    <template v-else-if="product">
      <header class="storefront-header">
        <RouterLink :to="`/${route.params.storeSlug}`" class="storefront-brand storefront-brand-link"><span class="storefront-mark">{{ product.name.charAt(0).toUpperCase() }}</span><div><strong>Store</strong><small>Powered by DukaMe</small></div></RouterLink>
        <button class="storefront-cart" type="button" disabled>Cart <span>0</span></button>
      </header>

      <section class="storefront-product-page">
        <RouterLink :to="`/${route.params.storeSlug}`" class="storefront-back">← Back to store</RouterLink>
        <div class="storefront-product-detail">
          <div class="storefront-gallery">
            <div class="storefront-main-image"><img v-if="product.media[selectedImage]" :src="product.media[selectedImage].url" :alt="product.media[selectedImage].alt_text || product.name" /><span v-else>No image</span></div>
            <div v-if="product.media.length > 1" class="storefront-thumbs"><button v-for="(media, index) in product.media" :key="media.url" type="button" :class="{ active: selectedImage === index }" @click="selectedImage = index"><img :src="media.url" :alt="media.alt_text || product.name" loading="lazy" /></button></div>
          </div>
          <article class="storefront-detail-copy">
            <span v-if="product.category" class="storefront-eyebrow">{{ product.category.name }}</span>
            <h1>{{ product.name }}</h1>
            <div class="storefront-price"><strong>{{ money(product.price_minor, product.currency) }}</strong><del v-if="product.compare_at_price_minor">{{ money(product.compare_at_price_minor, product.currency) }}</del></div>
            <div v-if="product.description" class="storefront-description-wrap">
              <p class="storefront-description">{{ descriptionExpanded ? product.description : descriptionPreview }}</p>
              <button v-if="hasLongDescription" class="storefront-read-more" type="button" :aria-expanded="descriptionExpanded" @click="descriptionExpanded = !descriptionExpanded">{{ descriptionExpanded ? 'Read less' : 'Read more' }} <span aria-hidden="true">{{ descriptionExpanded ? '↑' : '↓' }}</span></button>
            </div>
            <button class="button button-primary button-lg storefront-add" type="button" disabled>Add to cart</button>
            <small class="storefront-coming">Shopping and checkout will be available in the next commerce phase.</small>
          </article>
        </div>
      </section>
    </template>
  </main>
</template>
