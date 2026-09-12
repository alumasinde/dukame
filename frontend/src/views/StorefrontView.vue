<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useStorefrontShop } from '../lib/useStorefrontShop'
import { APP_NAME } from '../lib/branding'

const {
  store, loading, error, selectedCategory, searchQuery, searchInput, sortBy, page,
  addingProduct, addedProduct, addError, quantityBusy, showCartDrawer, favorites,
  recentSearches, showRecent, inStockOnly, storeSlug, topLevelCategories, selectedCategoryItem,
  childCategories, heroProducts, showStickyCart, whatsappUrl, totalFiltered, totalPages,
  pagedProducts, resultLabel, cartState, money, image, hasDiscount, categoryCount, hasVariants,
  isAvailable, cartItemFor, isFavorite, toggleFavorite, closeDrawer, onSearchInput, commitSearch,
  applyRecent, clearSearch, clearAllFilters, suggestedCategories, selectCategory, addProduct,
  changeProductQuantity, changeDrawerQuantity, load, isNewProduct, clearRecentSearches,
} = useStorefrontShop()

function hideRecentSearches(): void {
  window.setTimeout(() => {
    showRecent.value = false
  }, 180)
}

onMounted(() => { void load() })
</script>

<template>
  <main class="storefront-page">
    <div v-if="loading" class="storefront-state"><div class="status-spinner" /><p>Loading store…</p></div>
    <div v-else-if="error" class="storefront-state"><div class="storefront-empty-icon">!</div><h1>Store unavailable</h1><p>{{ error }}</p><RouterLink to="/login" class="button button-primary">Go to {{ APP_NAME }}</RouterLink></div>
    <template v-else-if="store">
      <header class="storefront-header">
        <RouterLink :to="`/${store.slug}`" class="storefront-brand storefront-brand-link">
          <span class="storefront-mark">{{ store.name.charAt(0).toUpperCase() }}</span>
          <div><strong>{{ store.name }}</strong><small>Powered by {{ APP_NAME }}</small></div>
        </RouterLink>
        <div class="storefront-header-actions">
          <a v-if="whatsappUrl" class="storefront-header-link is-wa" :href="whatsappUrl" target="_blank" rel="noopener noreferrer" title="Chat on WhatsApp"><span aria-hidden="true">WA</span><span class="wa-label">WhatsApp</span></a>
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
          <div class="storefront-search-wrap">
            <label class="storefront-search" aria-label="Search products">
              <span aria-hidden="true">⌕</span>
              <input
                :value="searchInput"
                type="search"
                placeholder="Search products…"
                autocomplete="off"
                @input="onSearchInput(($event.target as HTMLInputElement).value)"
                @focus="showRecent = recentSearches.length > 0"
                @keydown.enter.prevent="commitSearch"
                @blur="hideRecentSearches"
              />
              <button v-if="searchInput" type="button" aria-label="Clear search" @mousedown.prevent="clearSearch">×</button>
            </label>
            <div v-if="showRecent && recentSearches.length" class="storefront-recent" role="listbox">
              <div class="storefront-recent-head">
                <span>Recent</span>
                <button type="button" @mousedown.prevent="clearRecentSearches(storeSlug); recentSearches = []">Clear</button>
              </div>
              <button v-for="q in recentSearches" :key="q" type="button" class="item" @mousedown.prevent="applyRecent(q)">{{ q }}</button>
            </div>
          </div>
        </div>

        <div v-if="selectedCategoryItem" class="storefront-category-banner">
          <span class="storefront-eyebrow">Category</span>
          <h2>{{ selectedCategoryItem.name }}</h2>
          <p v-if="selectedCategoryItem.description">{{ selectedCategoryItem.description }}</p>
          <p v-else>{{ totalFiltered }} product{{ totalFiltered === 1 ? '' : 's' }} in this category</p>
        </div>

        <div class="storefront-toolbar">
          <button type="button" class="storefront-filter-chip" :class="{ active: inStockOnly }" @click="inStockOnly = !inStockOnly">
            {{ inStockOnly ? 'In stock only ✓' : 'In stock only' }}
          </button>
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
                  <span v-if="isNewProduct(product)" class="storefront-new-badge">New</span>
                  <span v-if="hasDiscount(product)" class="storefront-sale-badge" :class="{ 'with-new': isNewProduct(product) }">Sale</span>
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
          <div v-else-if="searchQuery || selectedCategory || inStockOnly" class="storefront-empty storefront-empty-search">
            <div class="storefront-empty-icon">⌕</div>
            <h2>No products found</h2>
            <p>Nothing matched your filters. Try a broader search or another category.</p>
            <div class="storefront-empty-actions">
              <button class="button button-secondary" type="button" @click="clearAllFilters">Clear all filters</button>
            </div>
            <div v-if="suggestedCategories().length" class="storefront-empty-suggestions">
              <button v-for="cat in suggestedCategories()" :key="cat.public_id" type="button" @click="clearSearch(); selectCategory(cat.public_id)">{{ cat.name }}</button>
            </div>
          </div>
          <div v-else class="storefront-empty">
            <div class="storefront-empty-icon">⌂</div>
            <h2>No products yet</h2>
            <p>This store is getting ready. Check back soon — new items appear here as the merchant adds them.</p>
            <div v-if="whatsappUrl" class="storefront-empty-actions">
              <a class="button button-primary" :href="whatsappUrl" target="_blank" rel="noopener noreferrer">Ask on WhatsApp</a>
            </div>
          </div>

          <div v-if="totalPages > 1" class="storefront-pagination">
            <button type="button" :disabled="page <= 1" @click="page = Math.max(1, page - 1)">Previous</button>
            <span>Page {{ page }} of {{ totalPages }}</span>
            <button type="button" :disabled="page >= totalPages" @click="page = Math.min(totalPages, page + 1)">Next</button>
          </div>
        </div>
      </section>
      <footer class="storefront-footer">{{ store.name }} · Powered by {{ APP_NAME }}</footer>

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
