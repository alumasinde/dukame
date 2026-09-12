import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { removeCartItem, updateCartItem } from './cart'
import { useCartState } from './cart-state'
import { loadFavorites, toggleFavorite as toggleFavoriteStore } from './favorites'
import { clearRecentSearches, loadRecentSearches, pushRecentSearch } from './recent-search'
import { whatsappContactUrl } from './share'
import { APP_NAME } from './branding'
import {
  getStorefront,
  isNewProduct,
  type Storefront,
  type StorefrontCategory,
  type StorefrontProduct,
  type StorefrontSort,
} from './storefront'

export const PAGE_SIZE = 24

export function useStorefrontShop() {
  const route = useRoute()
  const router = useRouter()
  const cartState = useCartState()
  const store = ref<Storefront | null>(null)
  const loading = ref(true)
  const error = ref('')
  const selectedCategory = ref('')
  const searchQuery = ref('')
  const searchInput = ref('')
  const sortBy = ref<StorefrontSort>('featured')
  const page = ref(1)
  const addingProduct = ref('')
  const addedProduct = ref('')
  const addError = ref('')
  const quantityBusy = ref('')
  const showCartDrawer = ref(false)
  const favorites = ref<string[]>([])
  const recentSearches = ref<string[]>([])
  const showRecent = ref(false)
  const inStockOnly = ref(false)
  let searchDebounce: ReturnType<typeof setTimeout> | undefined
  let addedTimer: ReturnType<typeof setTimeout> | undefined

  const storeSlug = computed(() => String(route.params.storeSlug))
  const categorySlugParam = computed(() =>
    route.name === 'storefront-category' ? String(route.params.categorySlug || '') : '',
  )
  const categoryMap = computed(
    () => new Map((store.value?.categories || []).map((c) => [c.public_id, c])),
  )
  const categoryBySlug = computed(
    () => new Map((store.value?.categories || []).map((c) => [c.slug, c])),
  )
  const topLevelCategories = computed(() =>
    (store.value?.categories || []).filter((c) => !c.parent_public_id),
  )
  const selectedCategoryItem = computed(() =>
    selectedCategory.value ? categoryMap.value.get(selectedCategory.value) || null : null,
  )
  const childCategories = computed(() =>
    selectedCategory.value
      ? (store.value?.categories || []).filter((c) => c.parent_public_id === selectedCategory.value)
      : [],
  )
  const heroProducts = computed(() =>
    (store.value?.products || []).filter((p) => p.media.length).slice(0, 3),
  )
  const favoriteSet = computed(() => new Set(favorites.value))
  const showStickyCart = computed(
    () => (cartState.itemCount.value || 0) > 0 && !showCartDrawer.value,
  )
  const whatsappUrl = computed(() =>
    store.value?.contact_phone
      ? whatsappContactUrl(
          store.value.contact_phone,
          `Hi ${store.value.name}! I saw your shop on ${APP_NAME}.`,
        )
      : null,
  )

  function categoryAndAncestors(categoryId: string): Set<string> {
    const ids = new Set<string>()
    let current = categoryMap.value.get(categoryId)
    const visited = new Set<string>()
    while (current && !visited.has(current.public_id)) {
      visited.add(current.public_id)
      ids.add(current.public_id)
      current = current.parent_public_id
        ? categoryMap.value.get(current.parent_public_id)
        : undefined
    }
    return ids
  }

  function belongsToCategory(product: StorefrontProduct, categoryId: string) {
    return !!product.category && categoryAndAncestors(product.category.public_id).has(categoryId)
  }

  function isAvailable(product: StorefrontProduct) {
    return product.variants.length
      ? product.variants.some((v) => !v.inventory_tracking || v.inventory_quantity > 0)
      : !product.inventory_tracking || product.inventory_quantity > 0
  }

  const categoryCounts = computed(() => {
    const counts = new Map<string, number>()
    for (const product of store.value?.products || []) {
      if (!product.category) continue
      for (const id of categoryAndAncestors(product.category.public_id))
        counts.set(id, (counts.get(id) || 0) + 1)
    }
    return counts
  })

  const filteredProducts = computed(() => {
    const query = searchQuery.value.trim().toLowerCase()
    let list = (store.value?.products || []).filter((product) => {
      if (selectedCategory.value && !belongsToCategory(product, selectedCategory.value)) return false
      if (inStockOnly.value && !isAvailable(product)) return false
      if (!query) return true
      return [product.name, product.description || '', product.category?.name || ''].some((v) =>
        v.toLowerCase().includes(query),
      )
    })
    if (sortBy.value === 'price_asc') list = [...list].sort((a, b) => a.price_minor - b.price_minor)
    else if (sortBy.value === 'price_desc')
      list = [...list].sort((a, b) => b.price_minor - a.price_minor)
    return list
  })

  const totalFiltered = computed(() => filteredProducts.value.length)
  const totalPages = computed(() => Math.max(1, Math.ceil(totalFiltered.value / PAGE_SIZE)))
  const pagedProducts = computed(() => {
    const start = (page.value - 1) * PAGE_SIZE
    return filteredProducts.value.slice(start, start + PAGE_SIZE)
  })
  const resultLabel = computed(() =>
    selectedCategoryItem.value
      ? selectedCategoryItem.value.name
      : searchQuery.value.trim()
        ? `Results for “${searchQuery.value.trim()}”`
        : 'All products',
  )

  function money(minor: number, currency: string) {
    return new Intl.NumberFormat('en-KE', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(minor / 100)
  }
  function image(product: StorefrontProduct) {
    return product.media[0]?.url || ''
  }
  function hasDiscount(product: StorefrontProduct) {
    return product.compare_at_price_minor != null && product.compare_at_price_minor > product.price_minor
  }
  function categoryCount(category: StorefrontCategory) {
    return categoryCounts.value.get(category.public_id) || 0
  }
  function hasVariants(product: StorefrontProduct) {
    return product.variants.length > 0
  }
  function cartItemFor(product: StorefrontProduct) {
    return (
      cartState.cart.value?.items.find(
        (i) => i.product_public_id === product.public_id && !i.variant_public_id,
      ) || null
    )
  }
  function isFavorite(productId: string) {
    return favoriteSet.value.has(productId)
  }
  function toggleFavorite(productId: string) {
    favorites.value = toggleFavoriteStore(storeSlug.value, productId)
  }
  function closeDrawer() {
    showCartDrawer.value = false
  }
  function onSearchInput(value: string) {
    searchInput.value = value
    if (searchDebounce) clearTimeout(searchDebounce)
    searchDebounce = setTimeout(() => {
      searchQuery.value = value
    }, 220)
  }
  function commitSearch() {
    const q = searchInput.value.trim()
    searchQuery.value = q
    if (q) recentSearches.value = pushRecentSearch(storeSlug.value, q)
    showRecent.value = false
  }
  function applyRecent(q: string) {
    searchInput.value = q
    searchQuery.value = q
    recentSearches.value = pushRecentSearch(storeSlug.value, q)
    showRecent.value = false
  }
  function clearSearch() {
    searchInput.value = ''
    searchQuery.value = ''
    showRecent.value = false
  }
  function clearAllFilters() {
    clearSearch()
    selectCategory('')
    inStockOnly.value = false
  }
  function suggestedCategories() {
    return topLevelCategories.value.filter((c) => categoryCount(c) > 0).slice(0, 6)
  }
  function selectCategory(id: string) {
    selectedCategory.value = id
    page.value = 1
    const cat = id ? categoryMap.value.get(id) : null
    if (cat) {
      router.push({
        name: 'storefront-category',
        params: { storeSlug: storeSlug.value, categorySlug: cat.slug },
      })
    } else {
      router.push({ name: 'storefront', params: { storeSlug: storeSlug.value } })
    }
    const section = document.querySelector('.storefront-products-section')
    if (section)
      window.scrollTo({
        top: window.scrollY + section.getBoundingClientRect().top - 82,
        behavior: 'smooth',
      })
  }
  function applyCategoryFromRoute() {
    const slug = categorySlugParam.value
    if (!slug || !store.value) {
      if (!slug) selectedCategory.value = ''
      return
    }
    selectedCategory.value = categoryBySlug.value.get(slug)?.public_id || ''
  }

  async function addProduct(product: StorefrontProduct) {
    if (hasVariants(product) || !isAvailable(product) || addingProduct.value || quantityBusy.value)
      return
    addingProduct.value = product.public_id
    addError.value = ''
    try {
      await cartState.quickAdd(storeSlug.value, product.public_id)
      addedProduct.value = product.public_id
      showCartDrawer.value = true
      if (addedTimer) clearTimeout(addedTimer)
      addedTimer = setTimeout(() => {
        addedProduct.value = ''
      }, 2200)
    } catch (err: any) {
      addError.value =
        err?.response?.data?.detail || 'We could not add that product. Please try again.'
    } finally {
      addingProduct.value = ''
    }
  }

  async function changeProductQuantity(product: StorefrontProduct, delta: number) {
    const item = cartItemFor(product)
    if (!item || quantityBusy.value || !isAvailable(product)) return
    const nextQuantity = item.quantity + delta
    if (nextQuantity < 1) {
      quantityBusy.value = item.public_id
      try {
        const response = await removeCartItem(storeSlug.value, item.public_id)
        cartState.update(storeSlug.value, response.data)
      } catch (err: any) {
        addError.value = err?.response?.data?.detail || 'We could not update your cart.'
      } finally {
        quantityBusy.value = ''
      }
      return
    }
    if (product.inventory_tracking && nextQuantity > product.inventory_quantity) return
    quantityBusy.value = item.public_id
    try {
      const response = await updateCartItem(storeSlug.value, item.public_id, nextQuantity)
      cartState.update(storeSlug.value, response.data)
    } catch (err: any) {
      addError.value = err?.response?.data?.detail || 'We could not update your cart.'
    } finally {
      quantityBusy.value = ''
    }
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

  async function load() {
    try {
      const slug = storeSlug.value
      const [response] = await Promise.all([getStorefront(slug), cartState.load(slug)])
      store.value = response.data
      document.title = response.data.name
      favorites.value = loadFavorites(slug)
      recentSearches.value = loadRecentSearches(slug)
      applyCategoryFromRoute()
    } catch (err: any) {
      error.value = err?.response?.data?.detail || 'This store could not be found.'
    } finally {
      loading.value = false
    }
  }

  watch(storeSlug, () => {
    favorites.value = loadFavorites(storeSlug.value)
    recentSearches.value = loadRecentSearches(storeSlug.value)
  })
  watch([searchQuery, sortBy, selectedCategory, inStockOnly], () => {
    page.value = 1
  })
  watch(categorySlugParam, () => applyCategoryFromRoute())

  return {
    store,
    loading,
    error,
    selectedCategory,
    searchQuery,
    searchInput,
    sortBy,
    page,
    addingProduct,
    addedProduct,
    addError,
    quantityBusy,
    showCartDrawer,
    favorites,
    recentSearches,
    showRecent,
    inStockOnly,
    storeSlug,
    topLevelCategories,
    selectedCategoryItem,
    childCategories,
    heroProducts,
    showStickyCart,
    whatsappUrl,
    filteredProducts,
    totalFiltered,
    totalPages,
    pagedProducts,
    resultLabel,
    cartState,
    money,
    image,
    hasDiscount,
    categoryCount,
    hasVariants,
    isAvailable,
    cartItemFor,
    isFavorite,
    toggleFavorite,
    closeDrawer,
    onSearchInput,
    commitSearch,
    applyRecent,
    clearSearch,
    clearAllFilters,
    suggestedCategories,
    selectCategory,
    addProduct,
    changeProductQuantity,
    changeDrawerQuantity,
    load,
    isNewProduct,
    clearRecentSearches,
  }
}
