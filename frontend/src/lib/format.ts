/** Formatting helpers. Money is shown the way Indian administration writes it. */

const INR = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

/** Full rupee amount with Indian digit grouping: 1820000 → "₹18,20,000". */
export function rupees(amount: number): string {
  return `₹${INR.format(Math.round(amount))}`
}

/** Compact, in the units officials speak in: "₹18.20 L", "₹12.40 Cr". */
export function rupeesShort(amount: number): string {
  if (Math.abs(amount) >= 1_00_00_000) return `₹${(amount / 1_00_00_000).toFixed(2)} Cr`
  if (Math.abs(amount) >= 1_00_000) return `₹${(amount / 1_00_000).toFixed(2)} L`
  return `₹${INR.format(Math.round(amount))}`
}

export function signedPct(value: number, digits = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`
}

/** "2026-08-14" → "14 Aug 2026". */
export function shortDate(iso: string): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}
