import { PageHeader } from '@/components/AppShell'
import { SeverityChip } from '@/components/SeverityChip'
import {
  AGENCY_PERCENTILES,
  COST_DEVIATION_BY_TYPE,
  FINDINGS_BY_MODULE,
  MONTHS,
  SEVERITY_BY_MONTH,
} from '@/data/analytics'
import { MODULE_LABEL } from '@/data/types'
import { DISTRICT } from '@/data/works'
import { signedPct } from '@/lib/format'
import { SEVERITIES, SEVERITY_STYLE } from '@/lib/severity'

const SEAL = '#16457e'

export function Trends() {
  const findingsCeiling = Math.max(...FINDINGS_BY_MODULE.flatMap((m) => m.series))
  const severityCeiling = Math.max(...Object.values(SEVERITY_BY_MONTH).flat())
  const deviationCeiling = Math.max(...COST_DEVIATION_BY_TYPE.map((d) => Math.abs(d.deviation)))

  return (
    <div>
      <PageHeader
        eyebrow={`${DISTRICT.name} district · last eight months`}
        title="Trends"
        meta="How findings have accumulated, and where the district's cost estimates sit against benchmark."
      />

      <div className="space-y-px bg-rule">
        <Section
          title="Findings raised per month, by module"
          note="Drawn as separate panels on one shared scale rather than a stacked bar, so no two modules have to be told apart by colour. All panels share a y-axis ceiling of the busiest month."
        >
          <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 xl:grid-cols-3">
            {FINDINGS_BY_MODULE.map((m) => (
              <MiniBars
                key={m.module}
                label={MODULE_LABEL[m.module]}
                series={m.series}
                ceiling={findingsCeiling}
                color={SEAL}
                unit="findings"
              />
            ))}
          </div>
        </Section>

        <Section
          title="Severity mix per month"
          note="One panel per tier, each on its own scale. Tier is named on every panel, never carried by colour alone."
        >
          <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 xl:grid-cols-4">
            {SEVERITIES.map((tier) => (
              <MiniBars
                key={tier}
                label={<SeverityChip severity={tier} size="sm" />}
                series={[...SEVERITY_BY_MONTH[tier]]}
                ceiling={severityCeiling}
                color={SEVERITY_STYLE[tier].hex}
                unit="works"
              />
            ))}
          </div>
        </Section>

        <Section
          title="Mean deviation from Schedule of Rates, by work type"
          note="Average gap between the estimate and the state benchmark for that work type in hilly terrain. Positive is above benchmark."
        >
          <div className="max-w-2xl space-y-2">
            {COST_DEVIATION_BY_TYPE.map((d) => {
              const positive = d.deviation >= 0
              const width = (Math.abs(d.deviation) / deviationCeiling) * 100
              return (
                <div key={d.workType} className="grid grid-cols-[150px_1fr_64px] items-center gap-3">
                  <span className="font-mono text-[11.5px] text-ink-muted">{d.workType}</span>
                  <div className="relative h-4">
                    <div
                      className="absolute inset-y-0 rounded-[1px]"
                      style={{
                        width: `${width}%`,
                        backgroundColor: positive ? SEAL : '#9aa4ad',
                        left: positive ? '0' : undefined,
                        right: positive ? undefined : '100%',
                      }}
                      title={`${d.workType}: ${signedPct(d.deviation)} across ${d.works} works`}
                    />
                  </div>
                  <span className="text-right font-mono text-[11.5px] tabular-nums">
                    {signedPct(d.deviation)}
                  </span>
                </div>
              )
            })}
          </div>
          <p className="mt-3 text-[11px] text-ink-faint">
            Below-benchmark estimates are shown in grey; they are flagged separately, since an
            estimate far under benchmark usually signals incomplete scope rather than a saving.
          </p>
        </Section>

        <Section
          title="Agency performance within the terrain peer group"
          note="Each agency is ranked only against agencies working in comparable hilly districts, never against a national average. The signal contributes at most 15% of a pre-sanction score and is never a gate on its own."
        >
          <div className="max-w-2xl space-y-2">
            {AGENCY_PERCENTILES.map((a) => (
              <div key={a.name} className="grid grid-cols-[190px_1fr_92px] items-center gap-3">
                <span className="truncate text-[11.5px] text-ink-muted" title={a.name}>
                  {a.name}
                </span>
                <div className="h-4 rounded-[1px] bg-[#eceeef]">
                  <div
                    className="h-full rounded-[1px]"
                    style={{
                      width: `${a.percentile}%`,
                      backgroundColor: a.percentile < 20 ? SEVERITY_STYLE.MEDIUM.hex : SEAL,
                    }}
                    title={`${a.name}: ${a.percentile}th percentile, ${a.completed} completed works`}
                  />
                </div>
                <span className="text-right font-mono text-[11.5px] tabular-nums">
                  {a.percentile}th
                  <span className="ml-1 text-ink-faint">({a.completed})</span>
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-ink-faint">
            Bracketed figures are completed works. An agency is never flagged on fewer than fifteen.
          </p>
        </Section>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */

function Section({
  title,
  note,
  children,
}: {
  title: string
  note: string
  children: React.ReactNode
}) {
  return (
    <section className="bg-surface px-5 py-5">
      <h2 className="text-[13.5px] font-semibold">{title}</h2>
      <p className="mt-1 max-w-3xl text-[11.5px] leading-relaxed text-ink-muted">{note}</p>
      <div className="mt-4">{children}</div>
    </section>
  )
}

/**
 * One panel of a small-multiple set.
 *
 * Bars carry a native hover title so a reader can recover the exact value, and
 * the highest and lowest months are labelled directly rather than every bar
 * being numbered.
 */
function MiniBars({
  label,
  series,
  ceiling,
  color,
  unit,
}: {
  label: React.ReactNode
  series: number[]
  ceiling: number
  color: string
  unit: string
}) {
  const total = series.reduce((a, b) => a + b, 0)
  const latest = series[series.length - 1]
  const previous = series[series.length - 2]
  const change = latest - previous

  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-[12px] font-medium">{label}</div>
        <div className="font-mono text-[11px] tabular-nums text-ink-muted">{total}</div>
      </div>

      <div className="mt-2 flex h-[52px] items-end gap-[3px]">
        {series.map((value, i) => (
          <div
            key={MONTHS[i]}
            className="flex-1 rounded-t-[1px]"
            style={{
              height: `${Math.max((value / ceiling) * 100, 3)}%`,
              backgroundColor: color,
              opacity: i === series.length - 1 ? 1 : 0.55,
            }}
            title={`${MONTHS[i]}: ${value} ${unit}`}
          />
        ))}
      </div>

      <div className="mt-1 flex items-baseline justify-between font-mono text-[10px] text-ink-faint">
        <span>{MONTHS[0]}</span>
        <span className="tabular-nums">
          {MONTHS[MONTHS.length - 1]} {latest}
          {change !== 0 && (
            <span className="ml-1">
              ({change > 0 ? '+' : ''}
              {change})
            </span>
          )}
        </span>
      </div>
    </div>
  )
}
