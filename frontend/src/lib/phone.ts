/** Kenya mobile phone helpers for storefront checkout (Safaricom / Airtel). */

const MSISDN_RE = /^254[17]\d{8}$/

/** Digits only, strip spaces and symbols. */
export function digitsOnly(value: string): string {
  return (value || '').replace(/\D/g, '')
}

/**
 * Normalize common KE formats to 2547XXXXXXXX / 2541XXXXXXXX.
 * Accepts: 07…, 01…, 7…, 1…, +254…, 254…
 */
export function normalizeKenyaPhone(value: string): string {
  let digits = digitsOnly(value)
  if (digits.startsWith('0') && digits.length === 10) {
    digits = `254${digits.slice(1)}`
  } else if (digits.length === 9 && (digits.startsWith('7') || digits.startsWith('1'))) {
    digits = `254${digits}`
  }
  return digits
}

export function isValidKenyaMsisdn(value: string): boolean {
  return MSISDN_RE.test(normalizeKenyaPhone(value))
}

/** Display as 07XX XXX XXX when possible. */
export function formatKenyaPhoneDisplay(value: string): string {
  const n = normalizeKenyaPhone(value)
  if (!MSISDN_RE.test(n)) return value.trim()
  const local = `0${n.slice(3)}`
  return `${local.slice(0, 4)} ${local.slice(4, 7)} ${local.slice(7)}`
}

export function kenyaPhoneError(value: string): string | null {
  const trimmed = (value || '').trim()
  if (!trimmed) return 'Enter your M-Pesa phone number.'
  if (!isValidKenyaMsisdn(trimmed)) {
    return 'Enter a valid Kenyan mobile number (e.g. 07XX XXX XXX).'
  }
  return null
}
