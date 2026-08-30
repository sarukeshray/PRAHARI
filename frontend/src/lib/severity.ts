/**
 * Severity tiers.
 *
 * The composite score exists for debugging and appears only inside the score
 * breakdown panel.  Everywhere else the tier leads, because the reader is a
 * District Officer, not a data scientist.
 */

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export const SEVERITIES: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

/** Descending urgency, for sorting a queue. */
export const SEVERITY_RANK: Record<Severity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
}

export function tierForScore(score: number): Severity {
  if (score > 75) return 'CRITICAL'
  if (score > 50) return 'HIGH'
  if (score > 25) return 'MEDIUM'
  return 'LOW'
}

interface SeverityStyle {
  /** Text/hairline colour. */
  fg: string
  /** Tinted background for chips and row accents. */
  tint: string
  /** Solid chips for the two urgent tiers, outline for the advisory ones, so
   *  tier never depends on hue alone. */
  solid: boolean
  hex: string
}

export const SEVERITY_STYLE: Record<Severity, SeverityStyle> = {
  LOW: { fg: 'text-sev-low', tint: 'bg-sev-low-tint', solid: false, hex: '#64748b' },
  MEDIUM: { fg: 'text-sev-medium', tint: 'bg-sev-medium-tint', solid: false, hex: '#a9670c' },
  HIGH: { fg: 'text-sev-high', tint: 'bg-sev-high-tint', solid: true, hex: '#c4460b' },
  CRITICAL: {
    fg: 'text-sev-critical',
    tint: 'bg-sev-critical-tint',
    solid: true,
    hex: '#ae1414',
  },
}
