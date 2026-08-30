/**
 * Shapes for the prototype's placeholder dataset.
 *
 * These mirror the eSAKSHI-derived schema the production analytics core will
 * read, so the screens built against them will not need reshaping when the real
 * engine is wired in.  Nothing here is a live record.
 */

import type { Severity } from '@/lib/severity'

export type Stage = 'STAGE_1' | 'STAGE_2'

export type Terrain = 'PLAIN' | 'HILLY' | 'REMOTE' | 'COASTAL' | 'URBAN'

export type WorkStatus =
  | 'RECOMMENDED'
  | 'SANCTIONED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'REJECTED'

export type FlagStatus = 'OPEN' | 'UNDER_INVESTIGATION' | 'OVERRIDDEN' | 'CLEARED'

export type ReviewAction = 'INVESTIGATE' | 'OVERRIDE' | 'CLEAR'

/** Stage 1 modules screen a proposal; Stage 2 modules monitor work underway. */
export type ModuleCode =
  | 'COST'
  | 'DUPLICATE'
  | 'AGENCY'
  | 'COMPLIANCE'
  | 'STATISTICAL'
  | 'DISBURSEMENT'
  | 'GEOTAG'
  | 'VARIANCE'
  | 'TIMELINE'

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
}

export const MODULE_STAGE: Record<ModuleCode, Stage> = {
  COST: 'STAGE_1',
  DUPLICATE: 'STAGE_1',
  AGENCY: 'STAGE_1',
  COMPLIANCE: 'STAGE_1',
  STATISTICAL: 'STAGE_1',
  DISBURSEMENT: 'STAGE_2',
  GEOTAG: 'STAGE_2',
  VARIANCE: 'STAGE_2',
  TIMELINE: 'STAGE_2',
}

/**
 * A single finding.
 *
 * `observed`, `threshold` and `axisMax` exist so the evidence row can draw the
 * measurement to scale.  `explanation` is a templated sentence naming both
 * numbers — in production it is generated deterministically from the computed
 * values, never by a language model.
 */
export interface RiskFlag {
  flagId: string
  stage: Stage
  module: ModuleCode
  code: string
  title: string
  severity: Severity
  observed: number
  observedLabel: string
  observedCaption: string
  threshold: number
  thresholdLabel: string
  thresholdCaption: string
  axisMax: number
  explanation: string
  status: FlagStatus
  raisedOn: string
}

/** One module's contribution to the composite, for the breakdown panel. */
export interface ModuleContribution {
  module: ModuleCode
  score: number
  weight: number
}

export interface ReviewEntry {
  reviewId: string
  reviewerName: string
  reviewerRole: string
  action: ReviewAction
  justification: string
  decidedAt: string
}

export interface Work {
  workId: string
  workType: string
  description: string
  block: string
  panchayat: string
  district: string
  state: string
  terrain: Terrain
  mpName: string
  house: 'LOK_SABHA' | 'RAJYA_SABHA'
  constituency: string
  agencyName: string
  agencyType: string
  estimatedCost: number
  finalCost: number | null
  recommendedOn: string
  sanctionedOn: string | null
  expectedCompletionOn: string
  status: WorkStatus
  lat: number
  lon: number
  isScStArea: boolean
  stage: Stage
  compositeScore: number
  severity: Severity
  contributions: ModuleContribution[]
  flags: RiskFlag[]
  reviews: ReviewEntry[]
  daysOpen: number
}
