<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { addCartItem } from '../lib/cart'
import { useCartState } from '../lib/cart-state'
import { getStorefrontProduct, type StorefrontProduct } from '../lib/storefront'

const route = useRoute()
const cartState = useCartState()
const storeSlug = String(route.params.storeSlug)
const product = ref<StorefrontProduct | null>(null)
const loading = ref(true)
const adding = ref(false)
const added = ref(false)
const error = ref('')
const selectedImage = ref(0)
const descriptionExpanded = ref(false)
const quantity = ref(1)
const selectedOptions = reactive<Record<string, string>>({})
const DESCRIPTION_LIMIT = 420

const descriptionPreview = computed(() => {
  const description = product.value?.description || ''
  if (description.length <= DESCRIPTION_LIMIT) return description
  return `${description.slice(0, DESCRIPTION_LIMIT).trimEnd()}…`
})
const hasLongDescription = computed(() => (product.value?.description?.length || 0) > DESCRIPTION_LIMIT)

const optionGroups = computed(() => {
  const groups = new Map<string, { public_id: string; name: string; values: { public_id: string; name: string }[] }>()
  for (const variant of product.value?.variants || []) {
    for (const option of variant.options) {
      const group = groups.get(option.option_public_id) || { public_id: option.option_public_id, name: option.option_name, values: [] }
      if (!group.values.some(value => value.public_id === option.value_public_id)) group.values.push({ public_id: option.value_public_id, name: option.value_name })
      groups.set(option.option_public_id, group)
    }
  }
  return [...groups.values()]
})

const selectedVariant = computed(() => {
  const variants = product.value?.variants || []
  if (!variants.length) return null
  return variants.find(variant => variant.options.every(option => selectedOptions[option.option_public_id] === option.value_public_id)) || null
})

const displayPrice = computed(() => selectedVariant.value?.price_minor ?? product.value?.price_minor ?? 0)
const selectedVariantUnavailable = computed(() => !!product.value?.variants.length && !selectedVariant.value)

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}

function setOption(optionId: string, valueId: string) {
  selectedOptions[optionId] = valueId
  added.value = false
  error.value = ''
}

function variantStockLabel() {
  if (!selectedVariant.value) return ''
  if (!selectedVariant.value.inventory_tracking) return 'Available'
  if (selectedVariant.value.inventory_quantity <= 0) return 'Out of stock'
  return `${selectedVariant.value.inventory_quantity} available`
}

function increaseQuantity() {
  const available = selectedVariant.value?.inventory_tracking ? selectedVariant.value.inventory_quantity : undefined
  if (available !== undefined && quantity.value >= available) return
  quantity.value += 1
}

async function addToCart() {
  if (!product.value || selectedVariantUnavailable.value || !selectedVariant.value && product.value.variants.length) return
  const available = selectedVariant.value?.inventory_tracking ? selectedVariant.value.inventory_quantity : undefined
  if (available !== undefined && available < quantity.value) {
    error.value = `Only ${available} item(s) are available.`
    return
  }
  adding.value = true
  error.value = ''
  added.value = false
  try {
    const response = await addCartItem(storeSlug, product.value.public_id, quantity.value, selectedVariant.value?.public_id)
    cartState.update(storeSlug, response.data)
    added.value = true
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'We could not add this product to your cart.'
  } finally {
    adding.value = false
  }
}

onMounted(async () => {
  try {
    const response = await getStorefrontProduct(storeSlug, String(route.params.productSlug))
    product.value = response.data
    document.title = response.data.name
    for (const group of optionGroups.value) selectedOptions[group.public_id] = group.values[0]?.public_id || ''
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
    <div v-else-if="error && !product" class="storefront-state"><div class="storefront-empty-icon">!</div><h1>Product unavailable</h1><p>{{ error }}</p><RouterLink :to="`/${storeSlug}`" class="button button-primary">Back to store</RouterLink></div>
    <template v-else-if="product">
      <header class="storefront-header">
        <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link"><span class="storefront-mark">{{ product.name.charAt(0).toUpperCase() }}</span><div><strong>Store</strong><small>Powered by DukaMe</small></div></RouterLink>
        <RouterLink :to="`/${storeSlug}/cart`" class="storefront-cart storefront-cart-link"><span class="storefront-cart-label">Cart</span><span v-if="cartState.itemCount.value">{{ cartState.itemCount.value }}</span></RouterLink>
      </header>

      <section class="storefront-product-page">
        <RouterLink :to="`/${storeSlug}`" class="storefront-back">← Back to store</RouterLink>
        <div class="storefront-product-detail">
          <div class="storefront-gallery">
            <div class="storefront-main-image"><img v-if="product.media[selectedImage]" :src="product.media[selectedImage].url" :alt="product.media[selectedImage].alt_text || product.name" /><span v-else>No image</span></div>
            <div v-if="product.media.length > 1" class="storefront-thumbs"><button v-for="(media, index) in product.media" :key="media.url" type="button" :class="{ active: selectedImage === index }" @click="selectedImage = index"><img :src="media.url" :alt="media.alt_text || product.name" loading="lazy" /></button></div>
          </div>
          <article class="storefront-detail-copy">
            <span v-if="product.category" class="storefront-eyebrow">{{ product.category.name }}</span>
            <h1>{{ product.name }}</h1>
            <div class="storefront-price"><strong>{{ money(displayPrice, product.currency) }}</strong><del v-if="product.compare_at_price_minor && !selectedVariant">{{ money(product.compare_at_price_minor, product.currency) }}</del></div>

            <div v-if="optionGroups.length" class="storefront-options">
              <div v-for="group in optionGroups" :key="group.public_id" class="storefront-option-group">
                <div class="storefront-option-heading"><strong>{{ group.name }}</strong><span>{{ group.values.find(value => value.public_id === selectedOptions[group.public_id])?.name }}</span></div>
                <div class="storefront-option-values"><button v-for="value in group.values" :key="value.public_id" type="button" :class="{ active: selectedOptions[group.public_id] === value.public_id }" @click="setOption(group.public_id, value.public_id)">{{ value.name }}</button></div>
              </div>
              <p v-if="selectedVariant" class="storefront-stock" :class="{ unavailable: selectedVariant.inventory_tracking && selectedVariant.inventory_quantity <= 0 }">{{ variantStockLabel() }}</p>
              <p v-else class="storefront-form-error">Select an option combination to continue.</p>
            </div>

            <div v-if="product.description" class="storefront-description-wrap">
              <p class="storefront-description">{{ descriptionExpanded ? product.description : descriptionPreview }}</p>
              <button v-if="hasLongDescription" class="storefront-read-more" type="button" :aria-expanded="descriptionExpanded" @click="descriptionExpanded = !descriptionExpanded">{{ descriptionExpanded ? 'Read less' : 'Read more' }} <span aria-hidden="true">{{ descriptionExpanded ? '↑' : '↓' }}</span></button>
            </div>

            <div v-if="error" class="storefront-inline-error">{{ error }}</div>
            <div v-if="!product.variants.length || selectedVariant" class="storefront-add-row">
              <div class="storefront-quantity"><button type="button" aria-label="Decrease quantity" :disabled="quantity <= 1" @click="quantity--">−</button><span>{{ quantity }}</span><button type="button" aria-label="Increase quantity" :disabled="!!(selectedVariant?.inventory_tracking && quantity >= selectedVariant.inventory_quantity)" @click="increaseQuantity">+</button></div>
              <button class="button button-primary button-lg storefront-add" type="button" :disabled="adding || !!(selectedVariant?.inventory_tracking && selectedVariant.inventory_quantity < quantity) || selectedVariantUnavailable || !!(selectedVariant?.inventory_tracking && selectedVariant.inventory_quantity <= 0)" @click="addToCart">{{ adding ? 'Adding…' : added ? 'Added to cart ✓' : 'Add to cart' }}</button>
            </div>
            <RouterLink v-if="added" :to="`/${storeSlug}/cart`" class="storefront-go-cart">View cart · {{ cartState.itemCount.value }} {{ cartState.itemCount.value === 1 ? 'item' : 'items' }} →</RouterLink>
          </article>
        </div>
      </section>
    </template>
  </main>
</template>
