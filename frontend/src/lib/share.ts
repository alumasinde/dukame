/** Native share + WhatsApp fallback for product / store links. */

export function productShareText(name: string, priceLabel: string, url: string): string {
  return `${name} — ${priceLabel}\n${url}`
}

export async function shareContent(title: string, text: string, url: string): Promise<'shared' | 'copied' | 'cancelled'> {
  if (typeof navigator !== 'undefined' && navigator.share) {
    try {
      await navigator.share({ title, text, url })
      return 'shared'
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return 'cancelled'
    }
  }
  try {
    await navigator.clipboard.writeText(url)
    return 'copied'
  } catch {
    return 'cancelled'
  }
}

export function whatsappShareUrl(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`
}

/** Build wa.me chat link from a Kenya-friendly phone string. */
export function whatsappContactUrl(phone: string, message?: string): string | null {
  const digits = (phone || '').replace(/\D/g, '')
  let msisdn = digits
  if (digits.startsWith('0') && digits.length === 10) msisdn = `254${digits.slice(1)}`
  else if (digits.length === 9 && (digits.startsWith('7') || digits.startsWith('1'))) msisdn = `254${digits}`
  if (!/^254[17]\d{8}$/.test(msisdn)) return null
  const base = `https://wa.me/${msisdn}`
  return message ? `${base}?text=${encodeURIComponent(message)}` : base
}
