/** Query hooks. One place, so a screen never assembles a URL itself. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, qs } from './client'
import type {
  AgencyPerformance,
  AgencyRef,
  AssetSummary,
  Assessment,
  Checkin,
  DistrictComparisonRow,
  DistrictRef,
  DistrictSummary,
  EngineWeights,
  Flag,
  GeoCollection,
  HandoverQueueRow,
  Health,
  Maintenance,
  Me,
  ModuleCode,
  MPSummary,
  NationalOverview,
  PublicAggregate,
  ReviewAction,
  Severity,
  WorkDetail,
  WorkSummary,
} from './types'

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: () => api.get<Health>('/health') })
}

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<Me>('/me'),
    enabled,
    retry: false,
  })
}

export interface WorkFilters {
  district?: string
  status?: string
  severity?: Severity | 'ALL'
  module?: ModuleCode | 'ALL'
  work_type?: string
  block?: string
  only_findings?: boolean
  search?: string
  limit?: number
}

export function useWorks(filters: WorkFilters = {}) {
  return useQuery({
    queryKey: ['works', filters],
    queryFn: () => api.get<WorkSummary[]>(`/works${qs(filters as never)}`),
  })
}

export function useWork(workId: string | undefined) {
  return useQuery({
    queryKey: ['work', workId],
    queryFn: () => api.get<WorkDetail>(`/works/${workId}`),
    enabled: Boolean(workId),
  })
}

export function useFlags(filters: { status?: string; severity?: string; module?: string } = {}) {
  return useQuery({
    queryKey: ['flags', filters],
    queryFn: () => api.get<Flag[]>(`/flags${qs(filters)}`),
  })
}

/** Record a decision on a finding, then refresh everything that shows it. */
export function useReviewFlag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { flagId: number; action: ReviewAction; justification: string }) =>
      api.post<Flag>(`/flags/${vars.flagId}/review`, {
        action: vars.action,
        justification: vars.justification,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work'] })
      qc.invalidateQueries({ queryKey: ['works'] })
      qc.invalidateQueries({ queryKey: ['flags'] })
      qc.invalidateQueries({ queryKey: ['districtSummary'] })
    },
  })
}

export function useAssessWork() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workId: string) => api.post<Assessment[]>(`/works/${workId}/assess`),
    onSuccess: (_data, workId) => {
      qc.invalidateQueries({ queryKey: ['work', workId] })
      qc.invalidateQueries({ queryKey: ['works'] })
    },
  })
}

export function useRecommendWork() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<WorkDetail>('/works', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['works'] })
      qc.invalidateQueries({ queryKey: ['mpSummary'] })
    },
  })
}

export function useDistrictSummary(districtId: string | null | undefined) {
  return useQuery({
    queryKey: ['districtSummary', districtId],
    queryFn: () => api.get<DistrictSummary>(`/dashboard/district/${districtId}/summary`),
    enabled: Boolean(districtId),
  })
}

export function useDistrictMap(districtId: string | null | undefined, onlyFindings: boolean) {
  return useQuery({
    queryKey: ['districtMap', districtId, onlyFindings],
    queryFn: () =>
      api.get<GeoCollection>(
        `/dashboard/district/${districtId}/map${qs({ only_findings: onlyFindings })}`,
      ),
    enabled: Boolean(districtId),
  })
}

export function useMPSummary() {
  return useQuery({
    queryKey: ['mpSummary'],
    queryFn: () => api.get<MPSummary>('/dashboard/mp/summary'),
  })
}

export function useNational() {
  return useQuery({
    queryKey: ['national'],
    queryFn: () => api.get<NationalOverview>('/dashboard/national'),
  })
}

export function useStateDistricts(state: string | null | undefined) {
  return useQuery({
    queryKey: ['stateDistricts', state],
    queryFn: () => api.get<DistrictComparisonRow[]>(`/dashboard/state/${state}/districts`),
    enabled: Boolean(state),
  })
}

export function useAgencyPerformance(agencyId: string | null | undefined) {
  return useQuery({
    queryKey: ['agencyPerformance', agencyId],
    queryFn: () => api.get<AgencyPerformance>(`/agencies/${agencyId}/performance`),
    enabled: Boolean(agencyId),
  })
}

export function usePublicAggregates() {
  return useQuery({
    queryKey: ['publicAggregates'],
    queryFn: () => api.get<PublicAggregate[]>('/public/aggregates'),
  })
}

export function useMyAssets() {
  return useQuery({ queryKey: ['assets'], queryFn: () => api.get<AssetSummary[]>('/assets') })
}

export function useAcknowledgeHandover() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workId: string) => api.post(`/assets/${workId}/acknowledge`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assets'] }),
  })
}

export function useLogCheckin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { workId: string; still_in_use: boolean; notes: string }) =>
      api.post<Checkin>(`/assets/${vars.workId}/checkins`, {
        still_in_use: vars.still_in_use,
        notes: vars.notes,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assets'] }),
  })
}

export function useRaiseMaintenance() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { workId: string; description: string }) =>
      api.post<Maintenance>(`/assets/${vars.workId}/maintenance`, {
        description: vars.description,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] })
      qc.invalidateQueries({ queryKey: ['maintenance'] })
    },
  })
}

export function useHandoverQueue() {
  return useQuery({
    queryKey: ['handoverQueue'],
    queryFn: () => api.get<HandoverQueueRow[]>('/handovers/queue'),
  })
}

export function useMaintenanceList() {
  return useQuery({
    queryKey: ['maintenance'],
    queryFn: () => api.get<Maintenance[]>('/maintenance'),
  })
}

export function useWeights() {
  return useQuery({ queryKey: ['weights'], queryFn: () => api.get<EngineWeights>('/engine/weights') })
}

export function useUpdateWeights() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Record<string, Record<string, number>>) =>
      api.put<{ updated: number }>('/engine/weights', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['weights'] }),
  })
}

export function useDistrictRefs() {
  return useQuery({
    queryKey: ['districtRefs'],
    queryFn: () => api.get<DistrictRef[]>('/reference/districts'),
  })
}

export function useAgencyRefs(district?: string) {
  return useQuery({
    queryKey: ['agencyRefs', district],
    queryFn: () => api.get<AgencyRef[]>(`/reference/agencies${qs({ district })}`),
  })
}
