/** Formatting helpers.  Money is shown the way Indian administration writes it. */

const INR = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

/** Full rupee amount with Indian digit grouping: 1820000 → "₹18,20,000". */
export function rupees(amount: number): string {
  return `₹${INR.format(Math.round(amount))}`
}

/**
 * Compact rupee amount in the units officials actually speak in:
 * 1820000 → "₹18.20 L", 124000000 → "₹12.40 Cr".
 */
export function rupeesShort(amount: number): string {
  if (Math.abs(amount) >= 1_00_00_000) return `₹${(amount / 1_00_00_000).toFixed(2)} Cr`
  if (Math.abs(amount) >= 1_00_000) return `₹${(amount / 1_00_000).toFixed(2)} L`
  return `₹${INR.format(Math.round(amount))}`
}

/** Signed percentage, always carrying its direction: 41.06 → "+41.1%". */
export function signedPct(value: number, digits = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`
}

export function pct(value: number, digits = 0): string {
  return `${value.toFixed(digits)}%`
}

/** "2026-08-14" → "14 Aug 2026". */
export function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

/** Indian financial year label for a date: April–March. */
export function financialYear(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  const startYear = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1
  return `${startYear}\u2013${String((startYear + 1) % 100).padStart(2, '0')}`
}

export function daysBetween(fromIso: string, toIso: string): number {
  const ms = new Date(`${toIso}T00:00:00`).getTime() - new Date(`${fromIso}T00:00:00`).getTime()
  return Math.round(ms / 86_400_000)
}
