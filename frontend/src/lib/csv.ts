/**
 * CSV export.
 *
 * Real, not a placeholder: the rows are the ones already on screen, so what a
 * reviewer downloads is exactly what they were looking at. Values are quoted and
 * internal quotes doubled, so a description containing a comma survives the trip
 * into a spreadsheet.
 */

function cell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const s = String(value)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(rows: Record<string, unknown>[], columns?: string[]): string {
  if (rows.length === 0) return ''
  const keys = columns ?? Object.keys(rows[0])
  const header = keys.map(cell).join(',')
  const body = rows.map((r) => keys.map((k) => cell(r[k])).join(','))
  return [header, ...body].join('\n')
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[], columns?: string[]) {
  const csv = toCsv(rows, columns)
  if (!csv) return
  // A byte-order mark so Excel opens rupee symbols and Devanagari correctly.
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
