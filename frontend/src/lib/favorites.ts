/** Local favourites per store (no account required). */

const PREFIX = 'dukame:favorites:'

export function favoritesKey(storeSlug: string): string {
  return `${PREFIX}${storeSlug}`
}

export function loadFavorites(storeSlug: string): string[] {
  try {
    const raw = localStorage.getItem(favoritesKey(storeSlug))
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : []
  } catch {
    return []
  }
}

export function saveFavorites(storeSlug: string, ids: string[]): void {
  localStorage.setItem(favoritesKey(storeSlug), JSON.stringify([...new Set(ids)]))
}

export function toggleFavorite(storeSlug: string, productId: string): string[] {
  const current = loadFavorites(storeSlug)
  const next = current.includes(productId)
    ? current.filter((id) => id !== productId)
    : [...current, productId]
  saveFavorites(storeSlug, next)
  return next
}

export function isFavorite(storeSlug: string, productId: string): boolean {
  return loadFavorites(storeSlug).includes(productId)
}
