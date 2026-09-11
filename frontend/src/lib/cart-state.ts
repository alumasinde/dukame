import { computed, reactive } from 'vue'
import type { Cart } from './cart'

const state = reactive<{ storeSlug: string; cart: Cart | null }>({ storeSlug: '', cart: null })

export function useCartState() {
  const itemCount = computed(() => state.cart?.item_count || 0)

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

  return { cart: computed(() => state.cart), itemCount, storeSlug: computed(() => state.storeSlug), set, update, clear }
}
