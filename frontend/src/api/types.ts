/** Response shapes, mirroring `backend/app/schemas/api.py`. */

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type RoleKey =
  | 'DISTRICT_AUTHORITY'
  | 'MP'
  | 'MINISTRY'
  | 'STATE_NODAL'
  | 'IMPLEMENTING_AGENCY'
  | 'USER_AGENCY'
  | 'PUBLIC'

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
  | 'HANDOVER'

export type FlagStatus = 'OPEN' | 'UNDER_INVESTIGATION' | 'OVERRIDDEN' | 'CLEARED'
export type ReviewAction = 'INVESTIGATE' | 'OVERRIDE' | 'CLEAR'
export type WorkStatus = 'RECOMMENDED' | 'SANCTIONED' | 'IN_PROGRESS' | 'COMPLETED' | 'REJECTED'
export type Stage = 'STAGE_1' | 'STAGE_2' | 'STAGE_3'

export interface Me {
  user_id: string
  email: string
  display_name: string
  role: RoleKey
  scope: string
  scope_state: string | null
  scope_district_id: string | null
  scope_district_name: string | null
  scope_mp_id: string | null
  scope_agency_id: string | null
  scope_agency_name: string | null
  scope_user_agency_id: string | null
  scope_user_agency_name: string | null
  data_notice: string
}

export interface Health {
  status: string
  engine_version: string
  db_backend: string
  auth: 'firebase' | 'demo'
  works_loaded: number
  data_notice: string
}

export interface Review {
  review_id: number
  reviewer_role: RoleKey
  reviewer_name: string
  action: ReviewAction
  justification: string | null
  decided_at: string
}

export interface Flag {
  flag_id: number
  work_id: string
  module: ModuleCode
  flag_code: string
  signal_value: number
  threshold_value: number
  severity_tier: Severity
  explanation: string
  status: FlagStatus
  created_at: string
  assigned_to_user_id: string | null
  reviews: Review[]
}

export interface Contribution {
  module: ModuleCode
  score: number
  weight: number
}

export interface Assessment {
  assessment_id: number
  stage: Stage
  composite_score: number
  severity_tier: Severity
  engine_version: string
  computed_at: string
  contributions: Contribution[]
  flags: Flag[]
}

export interface WorkSummary {
  work_id: string
  work_type: string
  description: string
  block: string
  district_id: string
  district_name: string | null
  estimated_cost: number
  final_cost: number | null
  status: WorkStatus
  recommended_date: string | null
  sanctioned_date: string | null
  mp_name: string | null
  agency_name: string | null
  latitude: number
  longitude: number
  is_sc_st_area: boolean
  severity_tier: Severity | null
  composite_score: number | null
  open_flag_count: number
  primary_finding: string | null
  primary_finding_title: string | null
  days_open: number | null
}

export interface WorkDetail extends WorkSummary {
  panchayat: string | null
  state: string | null
  terrain_category: string | null
  constituency: string | null
  house: string | null
  agency_type: string | null
  expected_completion_date: string | null
  actual_completion_date: string | null
  disbursed_amount: number
  disbursed_pct: number
  latest_progress_pct: number
  photo_count: number
  report_count: number
  assessments: Assessment[]
}

export interface TierCounts {
  CRITICAL: number
  HIGH: number
  MEDIUM: number
  LOW: number
}

export interface DistrictSummary {
  district_id: string
  district_name: string
  state: string
  works_total: number
  works_screened: number
  open_findings: number
  tier_counts: TierCounts
  by_module: { module: ModuleCode; count: number }[]
  trend: { period: string; count: number }[]
  handover_overdue: number
}

export interface GeoFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    work_id: string
    work_type: string
    block: string
    estimated_cost: number
    status: WorkStatus
    severity_tier: Severity | null
    primary_finding: string | null
  }
}

export interface GeoCollection {
  type: 'FeatureCollection'
  features: GeoFeature[]
}

export interface MPSummary {
  mp_id: string
  name: string
  house: string
  constituency: string
  state: string
  financial_year: string
  entitlement: number
  recommended: number
  sanctioned: number
  disbursed: number
  utilisation_pct: number
  works_recommended: number
  works_completed: number
  works_total_all_years: number
  sc_st_allocation_pct: number
  sc_st_required_pct: number
  sc_required_pct: number
  st_required_pct: number
}

export interface StateRow {
  state: string
  works: number
  sanctioned_amount: number
  disbursed_amount: number
  utilisation_pct: number
  open_critical: number
  open_high: number
}

export interface NationalOverview {
  states: StateRow[]
  totals: {
    works: number
    open_findings: number
    unresolved_critical: number
    districts: number
  }
}

export interface DistrictComparisonRow {
  district_id: string
  district_name: string
  terrain_category: string
  works: number
  open_findings: number
  resolved_findings: number
  flag_rate_pct: number
  resolution_rate_pct: number
}

export interface AgencyPerformance {
  agency_id: string
  name: string
  terrain_category: string
  percentile: number
  peer_count: number
  peer_group_label: string
  completed_works: number
  total_works: number
  completion_rate: number
  mean_delay_days: number
  mean_overrun_pct: number
  peer_percentiles: number[]
  flagged: boolean
  note: string
}

export interface PublicAggregate {
  state: string
  works_total: number
  works_completed: number
  completion_rate_pct: number
  sanctioned_amount: number
  disbursed_amount: number
  utilisation_pct: number
}

export interface Handover {
  handover_id: number
  work_id: string
  user_agency_id: string
  user_agency_name: string | null
  handover_initiated_date: string
  handover_acknowledged_date: string | null
  uc_submitted_date: string | null
  register_entry_date: string | null
  status: string
}

export interface Checkin {
  checkin_id: number
  work_id: string
  checkin_date: string
  photo_reference: string | null
  still_in_use: boolean
  notes: string | null
}

export interface Maintenance {
  recommendation_id: number
  work_id: string
  user_agency_id: string
  raised_date: string
  description: string
  photo_reference: string | null
  status: string
  da_response: string | null
}

export interface AssetSummary {
  work_id: string
  work_type: string
  description: string
  block: string
  completed_on: string | null
  handover: Handover | null
  checkins: Checkin[]
  maintenance: Maintenance[]
}

export interface HandoverQueueRow {
  work_id: string
  work_type: string
  block: string
  district_id: string
  completed_on: string
  days_since_completion: number
  handover_state: string
  uc_on_file: boolean
  register_entry: boolean
}

export interface EngineWeights {
  engine_version: string
  stage1: Record<string, number>
  stage2: Record<string, number>
  stage3: Record<string, number>
  tiers: Record<string, number>
  thresholds: Record<string, number>
  caps: Record<string, number>
  similarity_backend: string
  notes: Record<string, string>
}

export interface DistrictRef {
  district_id: string
  name: string
  state: string
  terrain_category: string
  centroid_lat: number
  centroid_lon: number
}

export interface AgencyRef {
  agency_id: string
  name: string
  agency_type: string
  district_id: string
}
