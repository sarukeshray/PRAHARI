import type { ModuleCode, Stage } from '@/api/types'

export const MODULE_LABEL: Record<ModuleCode, string> = {
  COST: 'Cost benchmark',
  DUPLICATE: 'Duplicate detection',
  AGENCY: 'Agency record',
  COMPLIANCE: 'Compliance rules',
  STATISTICAL: 'Statistical outlier',
  DISBURSEMENT: 'Payment vs progress',
  GEOTAG: 'Geotag verification',
  VARIANCE: 'Cost variance',
  TIMELINE: 'Timeline adherence',
  HANDOVER: 'Handover & lifecycle',
}

export const STAGE_LABEL: Record<Stage, string> = {
  STAGE_1: 'Stage 1 — pre-sanction screening',
  STAGE_2: 'Stage 2 — post-sanction monitoring',
  STAGE_3: 'Stage 3 — handover and lifecycle',
}

export const STAGE_NOTE: Record<Stage, string> = {
  STAGE_1:
    'Uses only what is known before sanction: cost against the same-year Schedule of Rates, description and location, the agency record, and the compliance rules.',
  STAGE_2:
    'Uses disbursement against reported progress, photograph metadata, final cost, and timelines.',
  STAGE_3:
    'Asks whether the finished asset was actually handed to anyone, and whether that record was kept.',
}

/** A readable title per flag code, for headings above the explanation. */
export const FLAG_TITLE: Record<string, string> = {
  COST_ABOVE_SOR: 'Estimate above the Schedule of Rates benchmark',
  COST_BELOW_SOR: 'Estimate well below benchmark',
  COST_PEER_OUTLIER: 'Cost is an outlier against comparable works',
  DUPLICATE_CANDIDATE: 'Near-identical to an existing work',
  SPLIT_WORK_PATTERN: 'Possible split of one larger work',
  AGENCY_HISTORICAL_CONCERN: 'Agency record below its peer group',
  WORK_TYPE_NOT_PERMISSIBLE: 'Work type not permissible under the Scheme',
  ENTITLEMENT_EXCEEDED: 'Annual entitlement exceeded',
  QUOTA_SHORTFALL: 'Mandated area allocation below requirement',
  OUT_OF_CONSTITUENCY: 'Recommended outside the Member’s constituency',
  SANCTION_DELAY_45D: 'Sanction decision beyond the 45-day guideline',
  MISSING_RECOMMENDATION: 'Sanctioned with no recommendation on record',
  STATISTICAL_OUTLIER: 'Unusual combination of proposal attributes',
  PAYMENT_AHEAD_OF_PROGRESS: 'Disbursement running ahead of physical progress',
  FULLY_PAID_INCOMPLETE: 'Fully paid but incomplete',
  PHOTO_LOCATION_MISMATCH: 'Photograph taken away from the work site',
  PHOTO_TIMESTAMP_INVALID: 'Photograph predates the sanction it evidences',
  PHOTO_REUSED_ACROSS_WORKS: 'Same photograph submitted against several works',
  COST_OVERRUN: 'Final cost above estimate with no recorded revision',
  COMPLETION_OVERDUE_12M: 'Incomplete beyond the 12-month guideline',
  PROGRESS_REPORTING_STALLED: 'No progress report filed recently',
  NO_COMPLETION_EVIDENCE: 'Marked complete with no photograph',
  GHOST_WORK: 'Complete and paid, with no evidence of any kind',
  HANDOVER_OVERDUE: 'Handover to a user agency not recorded',
  UC_MISSING: 'No Utilisation Certificate on file',
  REGISTER_GAP: 'Handed over but not entered in the asset register',
}

export function flagTitle(code: string): string {
  return FLAG_TITLE[code] ?? code.replace(/_/g, ' ').toLowerCase()
}

/** Format a signal or threshold for display, using the flag code as the unit hint. */
export function signalLabel(code: string, value: number): string {
  if (code.startsWith('PHOTO_LOCATION')) {
    return value >= 1000 ? `${(value / 1000).toFixed(1)} km` : `${Math.round(value)} m`
  }
  if (code.includes('DAY') || code.includes('OVERDUE') || code.includes('STALLED')) {
    return `${Math.round(value)} days`
  }
  if (code === 'DUPLICATE_CANDIDATE') return `${(value * 100).toFixed(0)}%`
  if (code === 'ENTITLEMENT_EXCEEDED') return `₹${(value / 1e7).toFixed(2)} Cr`
  if (code.includes('PCT') || code.includes('COST_') || code.includes('PAYMENT') || code.includes('QUOTA')) {
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}
