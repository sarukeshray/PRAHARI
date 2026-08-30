/**
 * Placeholder analytics for the trend, backtest and cross-role screens.
 *
 * Figures are illustrative and internally consistent with the works dataset;
 * none of them measure anything real.
 */

import type { ModuleCode } from './types'

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']

/** Findings raised per month, per module. Rendered as small multiples. */
export const FINDINGS_BY_MODULE: { module: ModuleCode; series: number[] }[] = [
  { module: 'COST', series: [6, 9, 7, 11, 8, 13, 10, 14] },
  { module: 'COMPLIANCE', series: [4, 3, 6, 5, 7, 6, 9, 8] },
  { module: 'DUPLICATE', series: [2, 4, 3, 5, 4, 6, 5, 7] },
  { module: 'DISBURSEMENT', series: [5, 6, 8, 7, 9, 8, 11, 12] },
  { module: 'TIMELINE', series: [7, 8, 6, 9, 11, 10, 12, 11] },
  { module: 'GEOTAG', series: [1, 2, 2, 3, 2, 4, 3, 5] },
]

/**
 * Severity mix per month, one small multiple per tier.
 *
 * Deliberately not a four-series stacked chart: the amber, orange and red steps
 * are close enough in hue that a reader would have to tell them apart by colour
 * alone. Separating them spatially removes that dependency. See DECISIONS.md D-006.
 */
export const SEVERITY_BY_MONTH = {
  CRITICAL: [1, 2, 1, 3, 2, 3, 2, 2],
  HIGH: [4, 5, 6, 5, 7, 8, 7, 8],
  MEDIUM: [8, 9, 7, 11, 10, 12, 13, 12],
  LOW: [11, 13, 12, 15, 14, 17, 16, 18],
} as const

/** Mean deviation from the Schedule of Rates benchmark, by work type. */
export const COST_DEVIATION_BY_TYPE = [
  { workType: 'ROAD_CC', deviation: 22.4, works: 41 },
  { workType: 'COMMUNITY_HALL', deviation: 18.1, works: 27 },
  { workType: 'SCHOOL_BUILDING', deviation: 14.6, works: 33 },
  { workType: 'DRAINAGE', deviation: 11.2, works: 24 },
  { workType: 'WATER_TANK', deviation: 8.7, works: 19 },
  { workType: 'ROAD_BT', deviation: 6.3, works: 38 },
  { workType: 'TOILET_BLOCK', deviation: 4.1, works: 22 },
  { workType: 'BOREWELL', deviation: -3.8, works: 16 },
]

/** Agency performance percentiles within the district's terrain peer group. */
export const AGENCY_PERCENTILES = [
  { name: 'Panchayat Samiti Kherwara', percentile: 14, completed: 31 },
  { name: 'Zila Parishad Udaipur', percentile: 28, completed: 64 },
  { name: 'PWD Division Udaipur', percentile: 46, completed: 88 },
  { name: 'PHED Division Udaipur', percentile: 61, completed: 42 },
  { name: 'Nagar Nigam Udaipur', percentile: 78, completed: 57 },
]

/* -------------------------------------------------------------------------- */
/* CAG backtest                                                                */
/* -------------------------------------------------------------------------- */

export interface BacktestCase {
  caseId: string
  finding: string
  pattern: string
  expected: string[]
  triggered: string[]
  worksReplayed: number
  detected: number
}

/**
 * Patterns documented in CAG performance audits, reconstructed as synthetic
 * records and replayed through the engine.
 */
export const BACKTEST_CASES: BacktestCase[] = [
  {
    caseId: 'CAG-01',
    finding: '₹53.74 crore spent on works inadmissible under the Scheme',
    pattern: 'Works whose type falls outside the MPLADS permissible list.',
    expected: ['WORK_TYPE_NOT_PERMISSIBLE'],
    triggered: ['WORK_TYPE_NOT_PERMISSIBLE'],
    worksReplayed: 40,
    detected: 40,
  },
  {
    caseId: 'CAG-02',
    finding: '775 sanctioned works worth ₹10.18 crore never taken up by agencies',
    pattern: 'Sanctioned, funds released, no progress reports and no photographs.',
    expected: ['GHOST_WORK', 'FULLY_PAID_INCOMPLETE', 'NO_COMPLETION_EVIDENCE'],
    triggered: ['GHOST_WORK', 'FULLY_PAID_INCOMPLETE', 'NO_COMPLETION_EVIDENCE'],
    worksReplayed: 60,
    detected: 57,
  },
  {
    caseId: 'CAG-03',
    finding: '568 works costing ₹7.30 crore delayed in completion',
    pattern: 'Sanctioned more than twelve months prior, progress under 100%.',
    expected: ['COMPLETION_OVERDUE_12M'],
    triggered: ['COMPLETION_OVERDUE_12M', 'PROGRESS_REPORTING_STALLED'],
    worksReplayed: 50,
    detected: 48,
  },
  {
    caseId: 'CAG-04',
    finding: '558 works in one state executed without MP recommendation',
    pattern: 'Sanction date recorded against no valid recommendation.',
    expected: ['MISSING_RECOMMENDATION'],
    triggered: ['MISSING_RECOMMENDATION'],
    worksReplayed: 45,
    detected: 45,
  },
  {
    caseId: 'CAG-05',
    finding: 'Inflated cost estimation without detailed survey',
    pattern: 'Estimates set far above the Schedule of Rates for the work type.',
    expected: ['COST_ABOVE_SOR', 'COST_PEER_OUTLIER'],
    triggered: ['COST_ABOVE_SOR', 'COST_PEER_OUTLIER', 'STATISTICAL_OUTLIER'],
    worksReplayed: 55,
    detected: 51,
  },
]

/** Recall against the planted anomalies in the synthetic set. */
export const SENSITIVITY = [
  { anomaly: 'COST_INFLATION', planted: 96, recalled: 89 },
  { anomaly: 'DUPLICATE_WORK', planted: 62, recalled: 53 },
  { anomaly: 'SALAMI_SLICING', planted: 44, recalled: 36 },
  { anomaly: 'PAYMENT_AHEAD', planted: 71, recalled: 66 },
  { anomaly: 'GEOTAG_MISMATCH', planted: 58, recalled: 55 },
  { anomaly: 'PHOTO_REUSE', planted: 33, recalled: 32 },
  { anomaly: 'TIMELINE_BREACH', planted: 84, recalled: 78 },
  { anomaly: 'COST_OVERRUN', planted: 67, recalled: 59 },
  { anomaly: 'GHOST_WORK', planted: 39, recalled: 37 },
  { anomaly: 'ENTITLEMENT_BREACH', planted: 28, recalled: 28 },
  { anomaly: 'QUOTA_SHORTFALL', planted: 21, recalled: 20 },
]

export const FALSE_POSITIVE_RATE = 6.4
export const CLEAN_WORKS_TESTED = 3_524

/* -------------------------------------------------------------------------- */
/* Member of Parliament                                                        */
/* -------------------------------------------------------------------------- */

export const MP_SUMMARY = {
  name: 'Dr. A. Vaishnav',
  house: 'Lok Sabha',
  constituency: 'Udaipur',
  financialYear: '2026–27',
  entitlement: 50_000_000,
  recommended: 38_600_000,
  sanctioned: 31_200_000,
  disbursed: 24_800_000,
  worksRecommended: 46,
  worksCompleted: 19,
  scAllocationPct: 16.8,
  scRequiredPct: 15,
  stAllocationPct: 6.2,
  stRequiredPct: 7.5,
}

/* -------------------------------------------------------------------------- */
/* Ministry                                                                    */
/* -------------------------------------------------------------------------- */

export const STATE_ROLLUP = [
  { state: 'Rajasthan', works: 4128, utilisation: 78.4, openCritical: 12, openHigh: 61 },
  { state: 'Kerala', works: 3610, utilisation: 86.1, openCritical: 5, openHigh: 34 },
  { state: 'Madhya Pradesh', works: 4892, utilisation: 71.2, openCritical: 18, openHigh: 77 },
  { state: 'Maharashtra', works: 5744, utilisation: 82.6, openCritical: 9, openHigh: 52 },
  { state: 'Tamil Nadu', works: 4471, utilisation: 88.3, openCritical: 4, openHigh: 29 },
  { state: 'Uttar Pradesh', works: 7208, utilisation: 68.9, openCritical: 24, openHigh: 103 },
]

export const NATIONAL = {
  worksScreened: 30_053,
  fundsTracked: 41_280_000_000,
  openFindings: 428,
  unresolvedCritical: 72,
  districtsLive: 118,
  medianReviewDays: 9,
}
