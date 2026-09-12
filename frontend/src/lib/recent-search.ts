/** Recent search queries per store (local only). */

const PREFIX = 'dukame:recent-search:'
const MAX = 6

export function recentSearchKey(storeSlug: string): string {
  return `${PREFIX}${storeSlug}`
}

export function loadRecentSearches(storeSlug: string): string[] {
  try {
    const raw = localStorage.getItem(recentSearchKey(storeSlug))
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((q) => typeof q === 'string' && q.trim()).map((q) => q.trim()).slice(0, MAX)
      : []
  } catch {
    return []
  }
}

export function pushRecentSearch(storeSlug: string, query: string): string[] {
  const q = query.trim()
  if (!q) return loadRecentSearches(storeSlug)
  const next = [q, ...loadRecentSearches(storeSlug).filter((item) => item.toLowerCase() !== q.toLowerCase())].slice(0, MAX)
  localStorage.setItem(recentSearchKey(storeSlug), JSON.stringify(next))
  return next
}

export function clearRecentSearches(storeSlug: string): void {
  localStorage.removeItem(recentSearchKey(storeSlug))
}
