<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { removeCartItem, updateCartItem } from '../lib/cart'
import { useCartState } from '../lib/cart-state'
import { loadFavorites, toggleFavorite as toggleFavoriteStore } from '../lib/favorites'
import { whatsappContactUrl } from '../lib/share'
import { getStorefront, type Storefront, type StorefrontCategory, type StorefrontProduct, type StorefrontSort } from '../lib/storefront'

const PAGE_SIZE = 24

const route = useRoute()
const router = useRouter()
const cartState = useCartState()
const store = ref<Storefront | null>(null)
const loading = ref(true)
const error = ref('')
const selectedCategory = ref('')
const searchQuery = ref('')
const sortBy = ref<StorefrontSort>('featured')
const page = ref(1)
const addingProduct = ref('')
const addedProduct = ref('')
const addError = ref('')
const quantityBusy = ref('')
const showCartDrawer = ref(false)
const favorites = ref<string[]>([])
let addedTimer: ReturnType<typeof setTimeout> | undefined

const storeSlug = computed(() => String(route.params.storeSlug))
const categorySlugParam = computed(() => (route.name === 'storefront-category' ? String(route.params.categorySlug || '') : ''))
const categoryMap = computed(() => new Map((store.value?.categories || []).map(category => [category.public_id, category])))
const categoryBySlug = computed(() => new Map((store.value?.categories || []).map(category => [category.slug, category])))
const topLevelCategories = computed(() => (store.value?.categories || []).filter(category => !category.parent_public_id))
const selectedCategoryItem = computed(() => selectedCategory.value ? categoryMap.value.get(selectedCategory.value) || null : null)
const childCategories = computed(() => selectedCategory.value ? (store.value?.categories || []).filter(category => category.parent_public_id === selectedCategory.value) : [])
const heroProducts = computed(() => (store.value?.products || []).filter(product => product.media.length).slice(0, 3))
const favoriteSet = computed(() => new Set(favorites.value))
const showStickyCart = computed(() => (cartState.itemCount.value || 0) > 0 && !showCartDrawer.value)
const whatsappUrl = computed(() => store.value?.contact_phone ? whatsappContactUrl(store.value.contact_phone, `Hi ${store.value.name}! I saw your shop on DukaMe.`) : null)

function categoryAndAncestors(categoryId: string): Set<string> {
  const ids = new Set<string>(); let current = categoryMap.value.get(categoryId); const visited = new Set<string>()
  while (current && !visited.has(current.public_id)) { visited.add(current.public_id); ids.add(current.public_id); current = current.parent_public_id ? categoryMap.value.get(current.parent_public_id) : undefined }
  return ids
}
function belongsToCategory(product: StorefrontProduct, categoryId: string) { return !!product.category && categoryAndAncestors(product.category.public_id).has(categoryId) }
const categoryCounts = computed(() => { const counts = new Map<string, number>(); for (const product of store.value?.products || []) { if (!product.category) continue; for (const id of categoryAndAncestors(product.category.public_id)) counts.set(id, (counts.get(id) || 0) + 1) } return counts })

const filteredProducts = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  let list = (store.value?.products || []).filter(product => {
    if (selectedCategory.value && !belongsToCategory(product, selectedCategory.value)) return false
    if (!query) return true
    return [product.name, product.description || '', product.category?.name || ''].some(value => value.toLowerCase().includes(query))
  })
  if (sortBy.value === 'price_asc') list = [...list].sort((a, b) => a.price_minor - b.price_minor)
  else if (sortBy.value === 'price_desc') list = [...list].sort((a, b) => b.price_minor - a.price_minor)
  else if (sortBy.value === 'newest') list = [...list] // API already newest-first; keep order
  return list
})

const totalFiltered = computed(() => filteredProducts.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalFiltered.value / PAGE_SIZE)))
const pagedProducts = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return filteredProducts.value.slice(start, start + PAGE_SIZE)
})
const resultLabel = computed(() => selectedCategoryItem.value ? selectedCategoryItem.value.name : searchQuery.value.trim() ? `Results for “${searchQuery.value.trim()}”` : 'All products')

function money(minor: number, currency: string) { return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100) }
function image(product: StorefrontProduct) { return product.media[0]?.url || '' }
function hasDiscount(product: StorefrontProduct) { return product.compare_at_price_minor != null && product.compare_at_price_minor > product.price_minor }
function categoryCount(category: StorefrontCategory) { return categoryCounts.value.get(category.public_id) || 0 }
function hasVariants(product: StorefrontProduct) { return product.variants.length > 0 }
function isAvailable(product: StorefrontProduct) { return product.variants.length ? product.variants.some(variant => !variant.inventory_tracking || variant.inventory_quantity > 0) : !product.inventory_tracking || product.inventory_quantity > 0 }
function cartItemFor(product: StorefrontProduct) { return cartState.cart.value?.items.find(item => item.product_public_id === product.public_id && !item.variant_public_id) || null }
function isFavorite(productId: string) { return favoriteSet.value.has(productId) }
function toggleFavorite(productId: string) { favorites.value = toggleFavoriteStore(storeSlug.value, productId) }
function closeDrawer() { showCartDrawer.value = false }

function selectCategory(id: string) {
  selectedCategory.value = id
  page.value = 1
  const cat = id ? categoryMap.value.get(id) : null
  if (cat) {
    router.push({ name: 'storefront-category', params: { storeSlug: storeSlug.value, categorySlug: cat.slug } })
  } else {
    router.push({ name: 'storefront', params: { storeSlug: storeSlug.value } })
  }
  const section = document.querySelector('.storefront-products-section')
  if (section) window.scrollTo({ top: window.scrollY + section.getBoundingClientRect().top - 82, behavior: 'smooth' })
}

function applyCategoryFromRoute() {
  const slug = categorySlugParam.value
  if (!slug || !store.value) { if (!slug) selectedCategory.value = ''; return }
  const match = categoryBySlug.value.get(slug)
  selectedCategory.value = match?.public_id || ''
}

async function addProduct(product: StorefrontProduct) {
  if (hasVariants(product) || !isAvailable(product) || addingProduct.value || quantityBusy.value) return
  addingProduct.value = product.public_id; addError.value = ''
  try { await cartState.quickAdd(storeSlug.value, product.public_id); addedProduct.value = product.public_id; showCartDrawer.value = true; if (addedTimer) clearTimeout(addedTimer); addedTimer = setTimeout(() => { addedProduct.value = '' }, 2200) }
  catch (err: any) { addError.value = err?.response?.data?.detail || 'We could not add that product. Please try again.' }
  finally { addingProduct.value = '' }
}

async function changeProductQuantity(product: StorefrontProduct, delta: number) {
  const item = cartItemFor(product); if (!item || quantityBusy.value || !isAvailable(product)) return
  const nextQuantity = item.quantity + delta
  if (nextQuantity < 1) { quantityBusy.value = item.public_id; try { const response = await removeCartItem(storeSlug.value, item.public_id); cartState.update(storeSlug.value, response.data) } catch (err: any) { addError.value = err?.response?.data?.detail || 'We could not update your cart.' } finally { quantityBusy.value = '' }; return }
  if (product.inventory_tracking && nextQuantity > product.inventory_quantity) return
  quantityBusy.value = item.public_id
  try { const response = await updateCartItem(storeSlug.value, item.public_id, nextQuantity); cartState.update(storeSlug.value, response.data) }
  catch (err: any) { addError.value = err?.response?.data?.detail || 'We could not update your cart.' }
  finally { quantityBusy.value = '' }
}

async function changeDrawerQuantity(itemId: string, nextQuantity: number) {
  if (quantityBusy.value) return
  quantityBusy.value = itemId
  addError.value = ''
  try {
    if (nextQuantity < 1) {
      const response = await removeCartItem(storeSlug.value, itemId)
      cartState.update(storeSlug.value, response.data)
    } else {
      const response = await updateCartItem(storeSlug.value, itemId, nextQuantity)
      cartState.update(storeSlug.value, response.data)
    }
  } catch (err: any) {
    addError.value = err?.response?.data?.detail || 'We could not update your cart.'
  } finally {
    quantityBusy.value = ''
  }
}

watch(storeSlug, () => { favorites.value = loadFavorites(storeSlug.value) })
watch([searchQuery, sortBy, selectedCategory], () => { page.value = 1 })
watch(categorySlugParam, () => applyCategoryFromRoute())

onMounted(async () => {
  try {
    const slug = storeSlug.value
    const [response] = await Promise.all([getStorefront(slug), cartState.load(slug)])
    store.value = response.data
    document.title = response.data.name
    favorites.value = loadFavorites(slug)
    applyCategoryFromRoute()
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
        <RouterLink :to="`/${store.slug}`" class="storefront-brand storefront-brand-link">
          <span class="storefront-mark">{{ store.name.charAt(0).toUpperCase() }}</span>
          <div><strong>{{ store.name }}</strong><small>Powered by DukaMe</small></div>
        </RouterLink>
        <div class="storefront-header-actions">
          <a v-if="whatsappUrl" class="storefront-header-link is-wa" :href="whatsappUrl" target="_blank" rel="noopener noreferrer">WhatsApp</a>
          <RouterLink :to="`/${store.slug}/favourites`" class="storefront-header-link storefront-fav-badge" aria-label="Favourites">
            ♥<span v-if="favorites.length">{{ favorites.length }}</span>
          </RouterLink>
          <RouterLink :to="`/${store.slug}/cart`" class="storefront-header-link" @click.prevent="showCartDrawer = true">
            Cart <span v-if="cartState.itemCount.value">{{ cartState.itemCount.value }}</span>
          </RouterLink>
        </div>
      </header>

      <section class="storefront-hero">
        <div class="storefront-hero-layout">
          <div class="storefront-hero-copy">
            <span class="storefront-eyebrow">Welcome to {{ store.name }}</span>
            <h1>{{ store.name }}</h1>
            <p>{{ store.description || 'Discover products you will love, add them to your cart and checkout in a few simple steps.' }}</p>
            <div class="storefront-trust">
              <a v-if="whatsappUrl" class="storefront-trust-wa" :href="whatsappUrl" target="_blank" rel="noopener noreferrer">Chat on WhatsApp</a>
              <RouterLink class="storefront-trust-track" :to="`/${store.slug}/cart`">Track an order →</RouterLink>
            </div>
          </div>
          <div v-if="heroProducts.length" class="storefront-hero-visual" aria-hidden="true">
            <div class="storefront-hero-visual-main"><img :src="heroProducts[0].media[0].url" alt="" /></div>
            <div class="storefront-hero-visual-side">
              <div v-for="product in heroProducts.slice(1, 3)" :key="product.public_id"><img :src="product.media[0].url" alt="" /></div>
            </div>
          </div>
        </div>
      </section>

      <section class="storefront-content">
        <div class="storefront-shop-heading">
          <div>
            <span class="storefront-eyebrow">Shop</span>
            <h2>{{ resultLabel }}</h2>
            <p>{{ totalFiltered }} product{{ totalFiltered === 1 ? '' : 's' }}</p>
          </div>
          <label class="storefront-search" aria-label="Search products">
            <span aria-hidden="true">⌕</span>
            <input v-model="searchQuery" type="search" placeholder="Search products…" autocomplete="off" />
            <button v-if="searchQuery" type="button" aria-label="Clear search" @click="searchQuery = ''">×</button>
          </label>
        </div>

        <div class="storefront-toolbar">
          <label class="storefront-sort">
            Sort
            <select v-model="sortBy">
              <option value="featured">Featured</option>
              <option value="newest">Newest</option>
              <option value="price_asc">Price · Low to high</option>
              <option value="price_desc">Price · High to low</option>
            </select>
          </label>
        </div>

        <div v-if="addError" class="storefront-inline-error storefront-add-error" role="alert">{{ addError }} <button type="button" @click="addError = ''">Dismiss</button></div>

        <div v-if="store.categories.length" class="storefront-category-panel">
          <div class="storefront-category-heading">
            <strong>Browse categories</strong>
            <span v-if="selectedCategoryItem">{{ selectedCategoryItem.name }}</span>
          </div>
          <div class="storefront-categories" aria-label="Product categories">
            <button type="button" :class="{ active: !selectedCategory }" @click="selectCategory('')">All <span>{{ store.products.length }}</span></button>
            <button v-for="category in topLevelCategories" :key="category.public_id" type="button" :class="{ active: selectedCategory === category.public_id }" @click="selectCategory(category.public_id)">{{ category.name }} <span>{{ categoryCount(category) }}</span></button>
          </div>
          <div v-if="childCategories.length" class="storefront-subcategories">
            <span class="storefront-subcategory-label">In {{ selectedCategoryItem?.name }}</span>
            <button v-for="category in childCategories" :key="category.public_id" type="button" :class="{ active: selectedCategory === category.public_id }" @click="selectCategory(category.public_id)">{{ category.name }} <span>{{ categoryCount(category) }}</span></button>
          </div>
        </div>

        <div class="storefront-products-section">
          <div v-if="pagedProducts.length" class="storefront-grid">
            <article v-for="product in pagedProducts" :key="product.public_id" class="storefront-product" :class="{ 'storefront-product-unavailable': !isAvailable(product) }">
              <div class="storefront-product-image">
                <RouterLink :to="`/${store.slug}/products/${product.slug}`" class="storefront-product-link">
                  <img v-if="image(product)" :src="image(product)" :alt="product.media[0]?.alt_text || product.name" loading="lazy" />
                  <span v-else>No image</span>
                  <span v-if="hasDiscount(product)" class="storefront-sale-badge">Sale</span>
                  <span v-if="!isAvailable(product)" class="storefront-unavailable-badge">Not Available</span>
                </RouterLink>
                <button type="button" class="storefront-wishlist" :class="{ 'is-favorite': isFavorite(product.public_id) }" :aria-label="isFavorite(product.public_id) ? `Remove ${product.name} from favourites` : `Add ${product.name} to favourites`" :aria-pressed="isFavorite(product.public_id)" @click="toggleFavorite(product.public_id)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20.84 8.74c0 5.42-8.84 10.26-8.84 10.26S3.16 14.16 3.16 8.74A4.74 4.74 0 0 1 12 6.46a4.74 4.74 0 0 1 8.84 2.28Z" :fill="isFavorite(product.public_id) ? 'currentColor' : 'none'" /></svg>
                </button>
              </div>
              <RouterLink :to="`/${store.slug}/products/${product.slug}`" class="storefront-product-link">
                <div class="storefront-product-info">
                  <small v-if="product.category">{{ product.category.name }}</small>
                  <h3>{{ product.name }}</h3>
                  <div class="storefront-product-price">
                    <strong>{{ money(product.price_minor, product.currency) }}</strong>
                    <del v-if="hasDiscount(product)">{{ money(product.compare_at_price_minor!, product.currency) }}</del>
                  </div>
                </div>
              </RouterLink>
              <div class="storefront-product-action">
                <template v-if="!hasVariants(product) && isAvailable(product)">
                  <div v-if="cartItemFor(product)" class="storefront-product-quantity" :class="{ busy: quantityBusy === cartItemFor(product)?.public_id }">
                    <button type="button" aria-label="Decrease quantity" :disabled="quantityBusy === cartItemFor(product)?.public_id" @click="changeProductQuantity(product, -1)">−</button>
                    <span aria-live="polite">{{ cartItemFor(product)?.quantity }}</span>
                    <button type="button" aria-label="Increase quantity" :disabled="quantityBusy === cartItemFor(product)?.public_id || (product.inventory_tracking && (cartItemFor(product)?.quantity || 0) >= product.inventory_quantity)" @click="changeProductQuantity(product, 1)">+</button>
                  </div>
                  <button v-else class="storefront-quick-add" type="button" :disabled="addingProduct === product.public_id" @click="addProduct(product)">{{ addingProduct === product.public_id ? 'Adding…' : addedProduct === product.public_id ? 'Added to cart ✓' : 'Add to cart' }}</button>
                </template>
                <span v-else-if="!isAvailable(product)" class="storefront-quick-add storefront-unavailable-action" aria-disabled="true">Not Available</span>
                <RouterLink v-else :to="`/${store.slug}/products/${product.slug}`" class="storefront-quick-add storefront-options-link">Choose options</RouterLink>
              </div>
            </article>
          </div>
          <div v-else-if="searchQuery || selectedCategory" class="storefront-empty storefront-empty-search">
            <div class="storefront-empty-icon">⌕</div>
            <h2>No products found</h2>
            <p>Try another search or browse a different category.</p>
            <button class="button button-secondary" type="button" @click="searchQuery = ''; selectCategory('')">Clear filters</button>
          </div>
          <div v-else class="storefront-empty">
            <div class="storefront-empty-icon">⌂</div>
            <h2>No products yet</h2>
            <p>This store is getting ready. Please check back soon.</p>
          </div>

          <div v-if="totalPages > 1" class="storefront-pagination">
            <button type="button" :disabled="page <= 1" @click="page = Math.max(1, page - 1)">Previous</button>
            <span>Page {{ page }} of {{ totalPages }}</span>
            <button type="button" :disabled="page >= totalPages" @click="page = Math.min(totalPages, page + 1)">Next</button>
          </div>
        </div>
      </section>
      <footer class="storefront-footer">{{ store.name }} · Powered by DukaMe</footer>

      <RouterLink v-if="showStickyCart" :to="`/${store.slug}/cart`" class="storefront-sticky-cart" aria-label="Open cart and checkout">
        <div class="storefront-sticky-cart-copy">
          <strong>{{ money(cartState.cart.value?.subtotal_minor || 0, cartState.cart.value?.currency || store.currency) }}</strong>
          <span>{{ cartState.itemCount.value }} {{ cartState.itemCount.value === 1 ? 'item' : 'items' }} in cart</span>
        </div>
        <span class="storefront-sticky-cart-cta">Checkout →</span>
      </RouterLink>

      <Teleport to="body">
        <div v-if="showCartDrawer" class="storefront-cart-drawer-backdrop" @click="closeDrawer" />
        <aside v-if="showCartDrawer" class="storefront-cart-drawer" aria-label="Shopping cart">
          <div class="storefront-cart-drawer-head">
            <div>
              <strong>Your cart</strong>
              <span v-if="cartState.itemCount.value" style="display:block;color:var(--muted);font-size:10px;margin-top:3px">{{ cartState.itemCount.value }} {{ cartState.itemCount.value === 1 ? 'item' : 'items' }}</span>
            </div>
            <button type="button" class="storefront-drawer-close" aria-label="Close cart" @click="closeDrawer">×</button>
          </div>
          <div class="storefront-cart-drawer-body">
            <article v-for="item in cartState.cart.value?.items || []" :key="item.public_id" class="storefront-mini-cart-item">
              <div class="storefront-mini-cart-image"><img v-if="item.image_url" :src="item.image_url" :alt="item.product_name" /></div>
              <div class="storefront-mini-cart-copy">
                <strong>{{ item.product_name }}</strong>
                <small v-if="item.variant_label">{{ item.variant_label }}</small>
                <div class="storefront-mini-cart-price"><span>{{ money(item.unit_price_minor, item.currency) }} each</span><strong>{{ money(item.line_total_minor, item.currency) }}</strong></div>
                <div class="storefront-mini-cart-actions">
                  <div class="storefront-quantity" :class="{ disabled: quantityBusy === item.public_id }">
                    <button type="button" aria-label="Decrease quantity" :disabled="quantityBusy === item.public_id" @click="changeDrawerQuantity(item.public_id, item.quantity - 1)">−</button>
                    <span aria-live="polite">{{ item.quantity }}</span>
                    <button type="button" aria-label="Increase quantity" :disabled="quantityBusy === item.public_id" @click="changeDrawerQuantity(item.public_id, item.quantity + 1)">+</button>
                  </div>
                  <button type="button" class="storefront-mini-remove" :disabled="quantityBusy === item.public_id" @click="changeDrawerQuantity(item.public_id, 0)">Remove</button>
                </div>
              </div>
            </article>
            <div v-if="!cartState.cart.value?.items.length" class="storefront-empty" style="min-height:240px"><div class="storefront-empty-icon">—</div><h2>Your cart is empty</h2></div>
          </div>
          <div class="storefront-cart-drawer-foot">
            <div class="storefront-drawer-total"><span>Subtotal</span><strong>{{ money(cartState.cart.value?.subtotal_minor || 0, cartState.cart.value?.currency || store.currency) }}</strong></div>
            <div class="storefront-drawer-actions">
              <button type="button" class="button button-secondary" @click="closeDrawer">Continue shopping</button>
              <RouterLink :to="`/${store.slug}/cart`" class="button button-primary" @click="closeDrawer">Checkout</RouterLink>
            </div>
            <p class="storefront-drawer-note">Secure checkout · Never share your M-Pesa PIN with anyone.</p>
          </div>
        </aside>
      </Teleport>
    </template>
  </main>
</template>
