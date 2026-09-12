/** Guest cart snapshot so shoppers can return later on the same device. */

export interface SavedCartItem {
  product_public_id: string
  product_name: string
  product_slug: string
  variant_public_id: string | null
  variant_label: string | null
  quantity: number
  unit_price_minor: number
  image_url: string | null
  currency: string
  saved_at: string
}

export interface SavedCart {
  store_slug: string
  items: SavedCartItem[]
  updated_at: string
}

const PREFIX = 'dukame:saved-cart:'

export function savedCartKey(storeSlug: string): string {
  return `${PREFIX}${storeSlug}`
}

export function loadSavedCart(storeSlug: string): SavedCart | null {
  try {
    const raw = localStorage.getItem(savedCartKey(storeSlug))
    if (!raw) return null
    const parsed = JSON.parse(raw) as SavedCart
    if (!parsed || !Array.isArray(parsed.items) || parsed.store_slug !== storeSlug) return null
    return parsed
  } catch {
    return null
  }
}

export function clearSavedCart(storeSlug: string): void {
  localStorage.removeItem(savedCartKey(storeSlug))
}

export function saveCartSnapshot(
  storeSlug: string,
  items: Array<{
    product_public_id: string
    product_name: string
    product_slug: string
    variant_public_id: string | null
    variant_label: string | null
    quantity: number
    unit_price_minor: number
    image_url: string | null
    currency: string
  }>,
): SavedCart {
  const now = new Date().toISOString()
  const snapshot: SavedCart = {
    store_slug: storeSlug,
    updated_at: now,
    items: items.map((item) => ({
      ...item,
      saved_at: now,
    })),
  }
  localStorage.setItem(savedCartKey(storeSlug), JSON.stringify(snapshot))
  return snapshot
}
