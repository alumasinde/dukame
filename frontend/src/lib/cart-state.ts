import { computed, reactive } from 'vue'
import { addCartItem, getCart, type Cart } from './cart'

const state = reactive<{ storeSlug: string; cart: Cart | null; loading: boolean; busy: Set<string> }>({
  storeSlug: '',
  cart: null,
  loading: false,
  busy: new Set(),
})

export function useCartState() {
  const itemCount = computed(() => state.cart?.item_count || 0)
  const loading = computed(() => state.loading)

  function set(storeSlug: string, cart: Cart | null) {
    state.storeSlug = storeSlug
    state.cart = cart
  }

  function update(storeSlug: string, cart: Cart) {
    state.storeSlug = storeSlug
    state.cart = cart
  }

  function clear(storeSlug?: string) {
    if (!storeSlug || state.storeSlug === storeSlug) state.cart = null
  }

  async function load(storeSlug: string, force = false) {
    if (!force && state.storeSlug === storeSlug && state.cart) return state.cart
    state.storeSlug = storeSlug
    state.loading = true
    try {
      state.cart = (await getCart(storeSlug)).data
      return state.cart
    } finally {
      state.loading = false
    }
  }

  async function quickAdd(storeSlug: string, productPublicId: string, quantity = 1) {
    const key = `add:${productPublicId}`
    if (state.busy.has(key)) return state.cart
    state.busy.add(key)
    try {
      const response = await addCartItem(storeSlug, productPublicId, quantity)
      state.storeSlug = storeSlug
      state.cart = response.data
      return state.cart
    } finally {
      state.busy.delete(key)
    }
  }

  function isBusy(key: string) {
    return state.busy.has(key)
  }

  return { cart: computed(() => state.cart), itemCount, loading, storeSlug: computed(() => state.storeSlug), set, update, clear, load, quickAdd, isBusy }
}
