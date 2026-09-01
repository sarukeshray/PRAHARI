import { useState } from 'react'

import { useDistrictSummary, useWorks } from '@/api/hooks'
import type { ModuleCode, Severity } from '@/api/types'
import {
  EmptyState,
  ErrorState,
  Loading,
  PageHeader,
  SeverityChip,
  SEVERITY_ORDER,
  Td,
  Th,
  WorkLink,
} from '@/components/ui-kit'
import { downloadCsv } from '@/lib/csv'
import { MODULE_LABEL } from '@/lib/labels'
import { rupeesShort, shortDate } from '@/lib/format'
import { useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

export function ReviewQueue() {
  const { me } = useSession()
  const districtId = me?.scope_district_id ?? undefined

  const [severity, setSeverity] = useState<Severity | 'ALL'>('ALL')
  const [module, setModule] = useState<ModuleCode | 'ALL'>('ALL')
  const [onlyFindings, setOnlyFindings] = useState(true)
  const [search, setSearch] = useState('')

  const summary = useDistrictSummary(districtId)
  const works = useWorks({
    severity,
    module,
    only_findings: onlyFindings,
    search: search || undefined,
    limit: 200,
  })

  const counts = summary.data?.tier_counts

  return (
    <div>
      <PageHeader
        eyebrow={
          summary.data ? `${summary.data.district_name} district · ${summary.data.state}` : ' '
        }
        title="Review queue"
        meta={
          summary.data
            ? `${summary.data.open_findings} findings awaiting a decision · ${summary.data.works_screened.toLocaleString('en-IN')} of ${summary.data.works_total.toLocaleString('en-IN')} works screened`
            : 'Loading district position…'
        }
        actions={
          <>
          <a
            href={`/api/v1/reports/district/${districtId}.pdf`}
            className="rounded-[2px] border border-rule-strong px-2.5 py-1 text-[12px] hover:border-seal hover:text-seal"
          >
            Findings PDF
          </a>
          <button
            type="button"
            disabled={!works.data?.length}
            onClick={() =>
              downloadCsv(
                `review-queue-${new Date().toISOString().slice(0, 10)}.csv`,
                (works.data ?? []) as unknown as Record<string, unknown>[],
                [
                  'work_id', 'work_type', 'block', 'estimated_cost', 'status',
                  'severity_tier', 'composite_score', 'open_flag_count',
                  'primary_finding_title', 'primary_finding', 'days_open',
                ],
              )
            }
            className="rounded-[2px] border border-rule-strong px-2.5 py-1 text-[12px] hover:border-seal hover:text-seal disabled:opacity-40"
          >
            Export queue
          </button>
          </>
        }
      />

      {/* Counters double as filters. */}
      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule sm:grid-cols-4">
        {SEVERITY_ORDER.map((tier) => {
          const active = severity === tier
          return (
            <button
              key={tier}
              type="button"
              aria-pressed={active}
              onClick={() => setSeverity(active ? 'ALL' : tier)}
              className={cn(
                'px-5 py-3 text-left transition-colors',
                active ? 'bg-seal-tint' : 'bg-surface hover:bg-[#fafbfb]',
              )}
            >
              <SeverityChip severity={tier} size="sm" />
              <div className="mt-1.5 font-mono text-[24px] leading-none font-medium tabular-nums">
                {counts ? counts[tier] : '—'}
              </div>
              <div className="mt-1 text-[11px] text-ink-muted">works</div>
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-5 py-2.5">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search work ID or description"
          className="w-56 rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12px]"
        />
        <select
          value={module}
          onChange={(e) => setModule(e.target.value as ModuleCode | 'ALL')}
          className="rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12px]"
        >
          <option value="ALL">All modules</option>
          {(Object.keys(MODULE_LABEL) as ModuleCode[]).map((m) => (
            <option key={m} value={m}>
              {MODULE_LABEL[m]}
            </option>
          ))}
        </select>
        <label className="ml-auto flex items-center gap-2 text-[12px] text-ink-muted">
          <input
            type="checkbox"
            checked={onlyFindings}
            onChange={(e) => setOnlyFindings(e.target.checked)}
            className="size-3.5 accent-[#16457e]"
          />
          Only works with findings
        </label>
        {(severity !== 'ALL' || module !== 'ALL' || search) && (
          <button
            type="button"
            onClick={() => {
              setSeverity('ALL')
              setModule('ALL')
              setSearch('')
            }}
            className="text-[12px] text-seal hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {works.isPending && <Loading rows={8} label="Loading the review queue" />}
      {works.isError && (
        <ErrorState message={(works.error as Error).message} onRetry={() => works.refetch()} />
      )}

      {works.data && works.data.length === 0 && (
        <EmptyState
          title="Nothing matches these filters"
          body="Widen the module filter, clear the severity selection, or untick 'only works with findings' to see everything screened in this district."
        />
      )}

      {works.data && works.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb]">
                <Th className="w-[150px]">Work ID</Th>
                <Th className="w-[140px]">Type</Th>
                <Th className="w-[100px]">Block</Th>
                <Th className="w-[100px] text-right">Estimate</Th>
                <Th className="w-[96px]">Severity</Th>
                <Th>Primary finding</Th>
                <Th className="w-[74px] text-right">Days</Th>
              </tr>
            </thead>
            <tbody>
              {works.data.map((w) => (
                <tr
                  key={w.work_id}
                  className="ledger-row border-b border-rule"
                  style={
                    {
                      '--row-accent': w.severity_tier
                        ? `var(--sev-${w.severity_tier.toLowerCase()})`
                        : 'transparent',
                    } as React.CSSProperties
                  }
                >
                  <Td>
                    <WorkLink workId={w.work_id} to={`/district/works/${w.work_id}`} />
                    <div className="mt-0.5 text-[11px] text-ink-faint">
                      {w.recommended_date ? shortDate(w.recommended_date) : 'No recommendation'}
                    </div>
                  </Td>
                  <Td>
                    <span className="font-mono text-[11.5px]">{w.work_type}</span>
                    <div className="mt-0.5 text-[11px] text-ink-faint">
                      {w.status.replace('_', ' ').toLowerCase()}
                    </div>
                  </Td>
                  <Td className="text-ink-muted">{w.block}</Td>
                  <Td className="text-right font-mono tabular-nums">
                    {rupeesShort(w.estimated_cost)}
                  </Td>
                  <Td>
                    <SeverityChip severity={w.severity_tier} size="sm" />
                  </Td>
                  <Td>
                    {w.primary_finding ? (
                      <>
                        <div className="font-mono text-[10.5px] text-ink-faint">
                          {w.primary_finding_title}
                        </div>
                        <div className="mt-0.5 line-clamp-2 text-[11.5px] leading-snug">
                          {w.primary_finding}
                        </div>
                        {w.open_flag_count > 1 && (
                          <div className="mt-1 text-[11px] text-ink-faint">
                            +{w.open_flag_count - 1} further{' '}
                            {w.open_flag_count === 2 ? 'finding' : 'findings'}
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="text-[11.5px] text-ink-faint">
                        Screened, no finding raised
                      </span>
                    )}
                  </Td>
                  <Td className="text-right font-mono text-ink-muted tabular-nums">
                    {w.days_open ?? '—'}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
