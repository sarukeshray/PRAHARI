import { PageHeader } from '@/components/AppShell'
import { NATIONAL, STATE_ROLLUP } from '@/data/analytics'
import { pct, rupeesShort } from '@/lib/format'
import { SEVERITY_STYLE } from '@/lib/severity'

const SEAL = '#16457e'

export function MinistryOverview() {
  const utilisationCeiling = 100
  const maxCritical = Math.max(...STATE_ROLLUP.map((s) => s.openCritical))

  return (
    <div>
      <PageHeader
        eyebrow="Ministry of Statistics and Programme Implementation · DIID"
        title="National overview"
        meta="Cross-state comparison and the findings that have stayed open longest. Thresholds set here apply to every district screening."
      />

      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule lg:grid-cols-6">
        <Stat label="Works screened" value={NATIONAL.worksScreened.toLocaleString('en-IN')} />
        <Stat label="Funds tracked" value={rupeesShort(NATIONAL.fundsTracked)} />
        <Stat label="Open findings" value={String(NATIONAL.openFindings)} />
        <Stat
          label="Unresolved critical"
          value={String(NATIONAL.unresolvedCritical)}
          accent={SEVERITY_STYLE.CRITICAL.hex}
        />
        <Stat label="Districts live" value={String(NATIONAL.districtsLive)} />
        <Stat label="Median review" value={`${NATIONAL.medianReviewDays} days`} />
      </div>

      <section className="border-b border-rule bg-surface px-5 py-5">
        <h2 className="text-[13.5px] font-semibold">Fund utilisation by state</h2>
        <p className="mt-1 max-w-3xl text-[11.5px] text-ink-muted">
          Utilisation is the share of released funds accounted for by reported physical progress.
          Persistent under-utilisation is the scheme's most consistently documented problem, and is
          measurable without any inference about intent.
        </p>

        <div className="mt-4 max-w-3xl space-y-2">
          {[...STATE_ROLLUP]
            .sort((a, b) => b.utilisation - a.utilisation)
            .map((s) => (
              <div key={s.state} className="grid grid-cols-[150px_1fr_64px] items-center gap-3">
                <span className="text-[12px] text-ink-muted">{s.state}</span>
                <div className="h-4 rounded-[1px] bg-[#eceeef]">
                  <div
                    className="h-full rounded-[1px]"
                    style={{
                      width: `${(s.utilisation / utilisationCeiling) * 100}%`,
                      backgroundColor: SEAL,
                    }}
                    title={`${s.state}: ${pct(s.utilisation, 1)} utilisation across ${s.works.toLocaleString('en-IN')} works`}
                  />
                </div>
                <span className="text-right font-mono text-[11.5px] tabular-nums">
                  {pct(s.utilisation, 1)}
                </span>
              </div>
            ))}
        </div>
      </section>

      <section className="bg-surface px-5 py-5">
        <h2 className="text-[13.5px] font-semibold">Open findings by state</h2>
        <p className="mt-1 max-w-3xl text-[11.5px] text-ink-muted">
          Counts of findings still awaiting a district decision. A high count is a workload signal,
          not a judgement about a state — a state that screens more works will raise more findings.
        </p>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb] text-left">
                <Th>State</Th>
                <Th className="text-right">Works</Th>
                <Th className="text-right">Utilisation</Th>
                <Th className="text-right">Open critical</Th>
                <Th className="text-right">Open high</Th>
                <Th className="w-[150px]">Critical load</Th>
              </tr>
            </thead>
            <tbody>
              {[...STATE_ROLLUP]
                .sort((a, b) => b.openCritical - a.openCritical)
                .map((s) => (
                  <tr key={s.state} className="border-b border-rule">
                    <td className="px-3 py-2.5">{s.state}</td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                      {s.works.toLocaleString('en-IN')}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                      {pct(s.utilisation, 1)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                      {s.openCritical}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums">{s.openHigh}</td>
                    <td className="px-3 py-2.5">
                      <div className="h-1.5 rounded-[1px] bg-[#eceeef]">
                        <div
                          className="h-full rounded-[1px]"
                          style={{
                            width: `${(s.openCritical / maxCritical) * 100}%`,
                            backgroundColor: SEVERITY_STYLE.CRITICAL.hex,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-surface px-4 py-3">
      <div className="eyebrow">{label}</div>
      <div
        className="mt-1 font-mono text-[19px] leading-none font-medium tabular-nums"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
    </div>
  )
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={`px-3 py-2 text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase ${className ?? ''}`}
    >
      {children}
    </th>
  )
}
