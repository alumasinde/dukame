import axios from 'axios'

export interface StorefrontMedia { url: string; alt_text: string | null }
export interface StorefrontCategory {
  public_id: string
  name: string
  slug: string
  description?: string | null
  parent_public_id: string | null
}
export interface StorefrontVariantOption {
  option_public_id: string
  option_name: string
  value_public_id: string
  value_name: string
}
export interface StorefrontVariant {
  public_id: string
  sku: string | null
  price_minor: number | null
  inventory_tracking: boolean
  inventory_quantity: number
  options: StorefrontVariantOption[]
}
export interface StorefrontProduct {
  public_id: string
  name: string
  slug: string
  description: string | null
  price_minor: number
  compare_at_price_minor: number | null
  currency: string
  inventory_tracking: boolean
  inventory_quantity: number
  created_at?: string | null
  category: StorefrontCategory | null
  media: StorefrontMedia[]
  variants: StorefrontVariant[]
}
export interface Storefront {
  public_id: string
  name: string
  slug: string
  description: string | null
  contact_phone?: string | null
  currency: string
  categories: StorefrontCategory[]
  products: StorefrontProduct[]
  total_products?: number
}

export type StorefrontSort = 'featured' | 'price_asc' | 'price_desc' | 'newest'

export interface StorefrontQuery {
  sort?: StorefrontSort
  limit?: number
  offset?: number
  q?: string
  category?: string
}

const storefrontApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
  withCredentials: true,
})

export function getStorefront(slug: string, params?: StorefrontQuery) {
  return storefrontApi.get<Storefront>(`/storefront/${encodeURIComponent(slug)}`, { params })
}

export function getStorefrontProduct(storeSlug: string, productSlug: string) {
  return storefrontApi.get<StorefrontProduct>(`/storefront/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}`)
}

/** Products marked New if created within the last N days. */
export function isNewProduct(product: StorefrontProduct, days = 14): boolean {
  if (!product.created_at) return false
  const created = new Date(product.created_at).getTime()
  if (Number.isNaN(created)) return false
  return Date.now() - created < days * 24 * 60 * 60 * 1000
}

export function relatedProducts(
  all: StorefrontProduct[],
  current: StorefrontProduct,
  limit = 4,
): StorefrontProduct[] {
  const others = all.filter((p) => p.public_id !== current.public_id)
  const sameCat = current.category
    ? others.filter((p) => p.category?.public_id === current.category?.public_id)
    : []
  const pool = sameCat.length >= 2 ? sameCat : others
  return pool.slice(0, limit)
}
