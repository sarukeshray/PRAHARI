import {
  Bar as RBar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useDistrictSummary, useWorks } from '@/api/hooks'
import { ErrorState, Loading, PageHeader, Section } from '@/components/ui-kit'
import { MODULE_LABEL } from '@/lib/labels'
import { useSession } from '@/lib/session'

const SEAL = '#16457e'

/**
 * Charts are single-hue or small multiples, never a stacked categorical bar.
 *
 * The severity palette (slate, amber, orange, red) fails colour-vision
 * validation: amber and orange are 0.7 ΔE apart under deuteranopia. Rather than
 * ask a reader to separate them, nothing here encodes a category by colour —
 * every series is one hue, and identity is carried by position and label.
 */
export function Trends() {
  const { me } = useSession()
  const districtId = me?.scope_district_id ?? undefined
  const summary = useDistrictSummary(districtId)
  const works = useWorks({ only_findings: false, limit: 500 })

  if (summary.isPending) return <Loading rows={8} label="Loading trends" />
  if (summary.isError)
    return <ErrorState message={(summary.error as Error).message} onRetry={() => summary.refetch()} />
  if (!summary.data) return null

  const s = summary.data

  const trend = s.trend.map((p) => ({
    period: p.period.slice(2).replace('-', '/'),
    count: p.count,
  }))

  const radar = s.by_module.map((m) => ({
    module: MODULE_LABEL[m.module].split(' ')[0],
    count: m.count,
  }))

  // Mean cost-to-benchmark position by work type, from what the queue returned.
  const byType = new Map<string, { total: number; n: number }>()
  for (const w of works.data ?? []) {
    const entry = byType.get(w.work_type) ?? { total: 0, n: 0 }
    entry.total += w.composite_score ?? 0
    entry.n += 1
    byType.set(w.work_type, entry)
  }
  const typeRows = [...byType.entries()]
    .map(([work_type, v]) => ({ work_type, score: v.total / v.n, works: v.n }))
    .filter((r) => r.works >= 3)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8)

  return (
    <div>
      <PageHeader
        eyebrow={`${s.district_name} district · ${s.state}`}
        title="Trends"
        meta={`${s.open_findings} open findings across ${s.works_screened.toLocaleString('en-IN')} screened works`}
      />

      <Section
        title="Findings raised per month"
        note="Counted against the month a work was recommended, so the series follows when the risk entered the pipeline rather than when the engine last ran."
      >
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trend} margin={{ top: 4, right: 8, bottom: 4, left: -18 }}>
              <CartesianGrid stroke="#eceeef" vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 10, fill: '#8a939b' }}
                axisLine={{ stroke: '#dce0e2' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: '#8a939b' }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 3,
                  border: '1px solid #dce0e2',
                  boxShadow: 'none',
                }}
                cursor={{ fill: '#f4f5f6' }}
              />
              <RBar dataKey="count" fill={SEAL} radius={[2, 2, 0, 0]} name="Findings" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Section>

      <Section
        title="Which risks dominate this district"
        note="Open findings by module. The shape tells a District Officer where their problem actually is — a district heavy on cost findings needs different attention from one heavy on handover."
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radar} outerRadius="72%">
                <PolarGrid stroke="#e4e7e9" />
                <PolarAngleAxis dataKey="module" tick={{ fontSize: 10, fill: '#5b656e' }} />
                <PolarRadiusAxis tick={{ fontSize: 9, fill: '#8a939b' }} axisLine={false} />
                <Radar
                  name="Open findings"
                  dataKey="count"
                  stroke={SEAL}
                  fill={SEAL}
                  fillOpacity={0.25}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 3,
                    border: '1px solid #dce0e2',
                    boxShadow: 'none',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2 self-center">
            {s.by_module.map((m) => {
              const max = Math.max(...s.by_module.map((x) => x.count), 1)
              return (
                <div key={m.module} className="grid grid-cols-[150px_1fr_44px] items-center gap-3">
                  <span className="text-[11.5px] text-ink-muted">{MODULE_LABEL[m.module]}</span>
                  <div className="h-3.5 rounded-[1px] bg-[#eceeef]">
                    <div
                      className="h-full rounded-[1px]"
                      style={{ width: `${(m.count / max) * 100}%`, backgroundColor: SEAL }}
                    />
                  </div>
                  <span className="text-right font-mono text-[11.5px] tabular-nums">{m.count}</span>
                </div>
              )
            })}
          </div>
        </div>
      </Section>

      <Section
        title="Mean composite score by work type"
        note="Work types are ordered by how much attention their proposals are drawing on average. A type sitting consistently high is a scoping or estimating problem, not a series of unrelated incidents."
      >
        {typeRows.length === 0 ? (
          <p className="text-[12px] text-ink-muted">Not enough screened works yet to compare types.</p>
        ) : (
          <div className="max-w-2xl space-y-2">
            {typeRows.map((r) => {
              const max = Math.max(...typeRows.map((x) => x.score), 1)
              return (
                <div key={r.work_type} className="grid grid-cols-[150px_1fr_78px] items-center gap-3">
                  <span className="font-mono text-[11.5px] text-ink-muted">{r.work_type}</span>
                  <div className="h-3.5 rounded-[1px] bg-[#eceeef]">
                    <div
                      className="h-full rounded-[1px]"
                      style={{ width: `${(r.score / max) * 100}%`, backgroundColor: SEAL }}
                      title={`${r.work_type}: mean score ${r.score.toFixed(1)} across ${r.works} works`}
                    />
                  </div>
                  <span className="text-right font-mono text-[11.5px] tabular-nums">
                    {r.score.toFixed(1)}
                    <span className="ml-1 text-ink-faint">({r.works})</span>
                  </span>
                </div>
              )
            })}
          </div>
        )}
        <p className="mt-3 text-[11px] text-ink-faint">
          Bracketed figures are the number of screened works behind each average. Types with fewer
          than three are not shown.
        </p>
      </Section>
    </div>
  )
}
