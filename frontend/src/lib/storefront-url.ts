const configuredBaseUrl = (
  import.meta.env.VITE_STOREFRONT_BASE_URL || import.meta.env.VITE_APP_URL || ''
).trim()

export function getStorefrontBaseUrl(): string {
  return (configuredBaseUrl || window.location.origin).replace(/\/+$/, '')
}

export function getStorefrontUrl(slug: string): string {
  return `${getStorefrontBaseUrl()}/${encodeURIComponent(slug)}`
}

export function getStorefrontDisplayBase(): string {
  const baseUrl = getStorefrontBaseUrl()
  try {
    const url = new URL(baseUrl, window.location.origin)
    return `${url.host}${url.pathname === '/' ? '/' : `${url.pathname.replace(/\/+$/, '')}/`}`
  } catch {
    return `${baseUrl.replace(/^https?:\/\//, '')}/`
  }
}
