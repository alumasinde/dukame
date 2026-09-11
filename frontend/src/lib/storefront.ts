import axios from 'axios'

export interface StorefrontMedia { url: string; alt_text: string | null }
export interface StorefrontCategory {
  public_id: string
  name: string
  slug: string
  parent_public_id: string | null
}
export interface StorefrontProduct {
  public_id: string
  name: string
  slug: string
  description: string | null
  price_minor: number
  compare_at_price_minor: number | null
  currency: string
  category: StorefrontCategory | null
  media: StorefrontMedia[]
}
export interface Storefront {
  public_id: string
  name: string
  slug: string
  description: string | null
  currency: string
  categories: StorefrontCategory[]
  products: StorefrontProduct[]
}

const storefrontApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
})

export function getStorefront(slug: string) {
  return storefrontApi.get<Storefront>(`/storefront/${encodeURIComponent(slug)}`)
}

export function getStorefrontProduct(storeSlug: string, productSlug: string) {
  return storefrontApi.get<StorefrontProduct>(`/storefront/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}`)
}
