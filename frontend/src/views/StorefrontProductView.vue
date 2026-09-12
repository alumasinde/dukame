<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { addCartItem } from '../lib/cart'
import { useCartState } from '../lib/cart-state'
import { isFavorite as checkFavorite, toggleFavorite as toggleFavoriteStore } from '../lib/favorites'
import { productShareText, shareContent, whatsappShareUrl } from '../lib/share'
import { getStorefront, getStorefrontProduct, isNewProduct, relatedProducts, type StorefrontProduct } from '../lib/storefront'
import { APP_NAME } from '../lib/branding'

const route = useRoute()
const cartState = useCartState()
const storeSlug = String(route.params.storeSlug)
const product = ref<StorefrontProduct | null>(null)
const catalog = ref<StorefrontProduct[]>([])
const storeName = ref('')
const storeCurrency = ref('KES')
const loading = ref(true)
const adding = ref(false)
const added = ref(false)
const error = ref('')
const selectedImage = ref(0)
const descriptionExpanded = ref(false)
const quantity = ref(1)
const selectedOptions = reactive<Record<string, string>>({})
const DESCRIPTION_LIMIT = 420
const favorite = ref(false)
const shareToast = ref('')

const descriptionPreview = computed(() => { const description = product.value?.description || ''; return description.length <= DESCRIPTION_LIMIT ? description : `${description.slice(0, DESCRIPTION_LIMIT).trimEnd()}…` })
const hasLongDescription = computed(() => (product.value?.description?.length || 0) > DESCRIPTION_LIMIT)
const optionGroups = computed(() => { const groups = new Map<string, { public_id: string; name: string; values: { public_id: string; name: string }[] }>(); for (const variant of product.value?.variants || []) for (const option of variant.options) { const group = groups.get(option.option_public_id) || { public_id: option.option_public_id, name: option.option_name, values: [] }; if (!group.values.some(value => value.public_id === option.value_public_id)) group.values.push({ public_id: option.value_public_id, name: option.value_name }); groups.set(option.option_public_id, group) } return [...groups.values()] })
const selectedVariant = computed(() => { const variants = product.value?.variants || []; if (!variants.length) return null; return variants.find(variant => variant.options.every(option => selectedOptions[option.option_public_id] === option.value_public_id)) || null })
const selectedVariantUnavailable = computed(() => !!product.value?.variants.length && (!selectedVariant.value || (selectedVariant.value.inventory_tracking && selectedVariant.value.inventory_quantity <= 0)))
const simpleProductUnavailable = computed(() => !!product.value && !product.value.variants.length && product.value.inventory_tracking && product.value.inventory_quantity <= 0)
const displayPrice = computed(() => selectedVariant.value?.price_minor ?? product.value?.price_minor ?? 0)
const showStickyCart = computed(() => (cartState.itemCount.value || 0) > 0)
const productUrl = computed(() => (typeof window !== 'undefined' ? window.location.href : ''))
const priceLabel = computed(() => product.value ? money(displayPrice.value, product.value.currency) : '')
const waShare = computed(() => {
  if (!product.value) return ''
  return whatsappShareUrl(productShareText(product.value.name, priceLabel.value, productUrl.value))
})
const related = computed(() => product.value ? relatedProducts(catalog.value, product.value, 4) : [])
const showNew = computed(() => product.value ? isNewProduct(product.value) : false)

function money(minor: number, currency: string) { return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100) }
function setOption(optionId: string, valueId: string) { selectedOptions[optionId] = valueId; added.value = false; error.value = '' }
function variantStockLabel() { if (!selectedVariant.value) return ''; if (!selectedVariant.value.inventory_tracking) return 'Available'; if (selectedVariant.value.inventory_quantity <= 0) return 'Not Available'; return `${selectedVariant.value.inventory_quantity} available` }
function increaseQuantity() { const available = selectedVariant.value?.inventory_tracking ? selectedVariant.value.inventory_quantity : product.value?.inventory_tracking && !product.value.variants.length ? product.value.inventory_quantity : undefined; if (available !== undefined && quantity.value >= available) return; quantity.value += 1 }
function toggleFavorite() {
  if (!product.value) return
  const next = toggleFavoriteStore(storeSlug, product.value.public_id)
  favorite.value = next.includes(product.value.public_id)
}
async function onShare() {
  if (!product.value) return
  const result = await shareContent(product.value.name, productShareText(product.value.name, priceLabel.value, productUrl.value), productUrl.value)
  if (result === 'copied') {
    shareToast.value = 'Link copied'
    setTimeout(() => { shareToast.value = '' }, 2000)
  }
}
async function addToCart() {
  if (!product.value || selectedVariantUnavailable.value || simpleProductUnavailable.value) return
  const available = selectedVariant.value?.inventory_tracking ? selectedVariant.value.inventory_quantity : !product.value.variants.length && product.value.inventory_tracking ? product.value.inventory_quantity : undefined
  if (available !== undefined && available < quantity.value) { error.value = `Only ${available} item(s) are available.`; return }
  adding.value = true; error.value = ''; added.value = false
  try { const response = await addCartItem(storeSlug, product.value.public_id, quantity.value, selectedVariant.value?.public_id); cartState.update(storeSlug, response.data); added.value = true }
  catch (err: any) { error.value = err?.response?.data?.detail || 'We could not add this product to your cart.' }
  finally { adding.value = false }
}

onMounted(async () => {
  try {
    const [productResponse, storeResponse] = await Promise.all([
      getStorefrontProduct(storeSlug, String(route.params.productSlug)),
      getStorefront(storeSlug),
      cartState.load(storeSlug),
    ])
    product.value = productResponse.data
    catalog.value = storeResponse.data.products || []
    storeName.value = storeResponse.data.name
    storeCurrency.value = storeResponse.data.currency
    document.title = `${product.value.name} · ${storeName.value}`
    favorite.value = checkFavorite(storeSlug, product.value.public_id)
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
        <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link">
          <span class="storefront-mark">{{ storeName ? storeName.charAt(0).toUpperCase() : 'S' }}</span>
          <div><strong>{{ storeName || 'Your store' }}</strong><small>Powered by {{ APP_NAME }}</small></div>
        </RouterLink>
        <div class="storefront-header-actions">
          <RouterLink :to="`/${storeSlug}/favourites" class="storefront-header-link storefront-fav-badge" aria-label="Favourites">♥</RouterLink>
          <RouterLink :to="`/${storeSlug}/cart" class="storefront-header-link">
            <span class="storefront-cart-label">Cart</span>
            <span v-if="cartState.itemCount.value">{{ cartState.itemCount.value }}</span>
          </RouterLink>
        </div>
      </header>
      <section class="storefront-product-page">
        <RouterLink :to="`/${storeSlug}`" class="storefront-back">← Back to store</RouterLink>
        <div class="storefront-product-detail">
          <div class="storefront-gallery">
            <div class="storefront-main-image" :class="{ 'storefront-image-unavailable': simpleProductUnavailable }">
              <img v-if="product.media[selectedImage]" :src="product.media[selectedImage].url" :alt="product.media[selectedImage].alt_text || product.name" />
              <span v-else>No image</span>
              <span v-if="showNew" class="storefront-new-badge">New</span>
              <span v-if="simpleProductUnavailable" class="storefront-unavailable-badge">Not Available</span>
            </div>
            <div v-if="product.media.length > 1" class="storefront-thumbs">
              <button v-for="(media, index) in product.media" :key="media.url" type="button" :class="{ active: selectedImage === index }" @click="selectedImage = index">
                <img :src="media.url" :alt="media.alt_text || product.name" loading="lazy" />
              </button>
            </div>
          </div>
          <article class="storefront-detail-copy">
            <span v-if="product.category" class="storefront-eyebrow">{{ product.category.name }}</span>
            <h1>{{ product.name }}</h1>
            <div class="storefront-price">
              <strong>{{ money(displayPrice, product.currency) }}</strong>
              <del v-if="product.compare_at_price_minor && !selectedVariant">{{ money(product.compare_at_price_minor, product.currency) }}</del>
            </div>

            <div class="storefront-share-row">
              <button type="button" class="storefront-share-btn" @click="onShare">Share</button>
              <a class="storefront-share-btn is-wa" :href="waShare" target="_blank" rel="noopener noreferrer">WhatsApp</a>
              <button type="button" class="storefront-share-btn" :class="{ 'is-favorite': favorite }" @click="toggleFavorite">{{ favorite ? 'Saved ♥' : 'Save' }}</button>
            </div>
            <p v-if="shareToast" class="storefront-share-toast">{{ shareToast }}</p>

            <div v-if="optionGroups.length" class="storefront-options">
              <div v-for="group in optionGroups" :key="group.public_id" class="storefront-option-group">
                <div class="storefront-option-heading">
                  <strong>{{ group.name }}</strong>
                  <span>{{ group.values.find(value => value.public_id === selectedOptions[group.public_id])?.name }}</span>
                </div>
                <div class="storefront-option-values">
                  <button v-for="value in group.values" :key="value.public_id" type="button" :class="{ active: selectedOptions[group.public_id] === value.public_id }" @click="setOption(group.public_id, value.public_id)">{{ value.name }}</button>
                </div>
              </div>
              <p v-if="selectedVariant" class="storefront-stock" :class="{ unavailable: selectedVariant.inventory_tracking && selectedVariant.inventory_quantity <= 0 }">{{ variantStockLabel() }}</p>
              <p v-else class="storefront-form-error">Select an option combination to continue.</p>
            </div>
            <p v-else-if="product.inventory_tracking && product.inventory_quantity <= 0" class="storefront-stock unavailable">Not Available</p>
            <div v-if="product.description" class="storefront-description-wrap">
              <p class="storefront-description">{{ descriptionExpanded ? product.description : descriptionPreview }}</p>
              <button v-if="hasLongDescription" class="storefront-read-more" type="button" :aria-expanded="descriptionExpanded" @click="descriptionExpanded = !descriptionExpanded">{{ descriptionExpanded ? 'Read less' : 'Read more' }} <span aria-hidden="true">{{ descriptionExpanded ? '↑' : '↓' }}</span></button>
            </div>
            <div v-if="error" class="storefront-inline-error">{{ error }}</div>
            <div v-if="!product.variants.length || selectedVariant" class="storefront-add-row">
              <div class="storefront-quantity">
                <button type="button" aria-label="Decrease quantity" :disabled="quantity <= 1" @click="quantity--">−</button>
                <span>{{ quantity }}</span>
                <button type="button" aria-label="Increase quantity" :disabled="!!(selectedVariant?.inventory_tracking && quantity >= selectedVariant.inventory_quantity) || !!(!product.variants.length && product.inventory_tracking && quantity >= product.inventory_quantity)" @click="increaseQuantity">+</button>
              </div>
              <button v-if="!simpleProductUnavailable && !selectedVariantUnavailable" class="button button-primary button-lg storefront-add" type="button" :disabled="adding" @click="addToCart">{{ adding ? 'Adding…' : added ? 'Added to cart ✓' : 'Add to cart' }}</button>
              <span v-else class="button button-lg storefront-add storefront-unavailable-action" aria-disabled="true">Not Available</span>
            </div>
            <RouterLink v-if="added" :to="`/${storeSlug}/cart`" class="storefront-go-cart">View cart · {{ cartState.itemCount.value }} {{ cartState.itemCount.value === 1 ? 'item' : 'items' }} →</RouterLink>
          </article>
        </div>
      </section>

      <section v-if="related.length" class="storefront-related">
        <h2>You may also like</h2>
        <div class="storefront-related-grid">
          <RouterLink v-for="item in related" :key="item.public_id" :to="`/${storeSlug}/products/${item.slug}`" class="storefront-related-card">
            <div class="img">
              <img v-if="item.media[0]" :src="item.media[0].url" :alt="item.name" loading="lazy" />
            </div>
            <div class="copy">
              <strong>{{ item.name }}</strong>
              <span>{{ money(item.price_minor, item.currency) }}</span>
            </div>
          </RouterLink>
        </div>
      </section>

      <RouterLink v-if="showStickyCart" :to="`/${storeSlug}/cart`" class="storefront-sticky-cart" aria-label="Open cart and checkout">
        <div class="storefront-sticky-cart-copy">
          <strong>{{ money(cartState.cart.value?.subtotal_minor || 0, cartState.cart.value?.currency || storeCurrency) }}</strong>
          <span>{{ cartState.itemCount.value }} {{ cartState.itemCount.value === 1 ? 'item' : 'items' }} in cart</span>
        </div>
        <span class="storefront-sticky-cart-cta">Checkout →</span>
      </RouterLink>
    </template>
  </main>
</template>
