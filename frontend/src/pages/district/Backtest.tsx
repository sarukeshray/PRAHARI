import { PageHeader } from '@/components/AppShell'
import {
  BACKTEST_CASES,
  CLEAN_WORKS_TESTED,
  FALSE_POSITIVE_RATE,
  SENSITIVITY,
} from '@/data/analytics'
import { pct } from '@/lib/format'

const SEAL = '#16457e'

export function Backtest() {
  const totalReplayed = BACKTEST_CASES.reduce((n, c) => n + c.worksReplayed, 0)
  const totalDetected = BACKTEST_CASES.reduce((n, c) => n + c.detected, 0)

  return (
    <div>
      <PageHeader
        eyebrow="Method validation"
        title="CAG backtest"
        meta="Irregularity patterns documented by the Comptroller and Auditor General, reconstructed as synthetic records and replayed through the engine."
      />

      {/* The disclaimer leads the screen rather than footnoting it. Overclaiming
          here is the fastest way to lose a technical juror. */}
      <div className="border-b border-notice-rule bg-notice px-5 py-4">
        <p className="max-w-4xl text-[12.5px] leading-relaxed text-notice-ink">
          These cases reproduce irregularity <em>patterns</em> documented in CAG performance audits,
          using synthetic records. This demonstrates that the detection method identifies the classes
          of irregularity auditors have historically found. It is not a measurement of real-world
          detection accuracy, which would require validation against live MPLADS data.
        </p>
      </div>

      <section className="border-b border-rule bg-surface px-5 py-5">
        <h2 className="text-[13.5px] font-semibold">Documented cases replayed</h2>
        <p className="mt-1 max-w-3xl text-[11.5px] text-ink-muted">
          Source: CAG Report No. 31 of 2010, Performance Audit of MPLADS, and later compliance
          reports. Each row reconstructs the documented pattern as synthetic works and runs them
          through the same engine that screens live proposals.
        </p>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[840px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb] text-left">
                <th className="w-[76px] px-3 py-2 text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase">
                  Case
                </th>
                <th className="px-3 py-2 text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase">
                  Documented finding
                </th>
                <th className="w-[240px] px-3 py-2 text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase">
                  Flags triggered
                </th>
                <th className="w-[128px] px-3 py-2 text-right text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase">
                  Detected
                </th>
              </tr>
            </thead>
            <tbody>
              {BACKTEST_CASES.map((c) => {
                const rate = (c.detected / c.worksReplayed) * 100
                const extra = c.triggered.filter((t) => !c.expected.includes(t))
                return (
                  <tr key={c.caseId} className="border-b border-rule align-top">
                    <td className="px-3 py-3 font-mono text-[11.5px] font-medium">{c.caseId}</td>
                    <td className="px-3 py-3">
                      <div>{c.finding}</div>
                      <div className="mt-0.5 text-[11.5px] text-ink-muted">{c.pattern}</div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        {c.triggered.map((t) => (
                          <span
                            key={t}
                            className={
                              extra.includes(t)
                                ? 'rounded-[2px] border border-dashed border-rule-strong px-1.5 py-px font-mono text-[10px] text-ink-faint'
                                : 'rounded-[2px] bg-seal-tint px-1.5 py-px font-mono text-[10px] text-seal'
                            }
                            title={extra.includes(t) ? 'Additional to the expected flags' : 'Expected'}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="font-mono text-[13px] tabular-nums">
                        {c.detected}
                        <span className="text-ink-faint">/{c.worksReplayed}</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded-[1px] bg-[#eceeef]">
                        <div
                          className="h-full rounded-[1px]"
                          style={{ width: `${rate}%`, backgroundColor: SEAL }}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className="bg-[#fafbfb]">
                <td colSpan={3} className="px-3 py-2.5 text-[12px] font-medium">
                  Across all five reconstructed cases
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[13px] tabular-nums">
                  {totalDetected}
                  <span className="text-ink-faint">/{totalReplayed}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-ink-faint">
          Dashed flags fired in addition to those the case was built to trigger. They are reported
          rather than hidden, because an unexpected flag is as much a property of the method as an
          expected one.
        </p>
      </section>

      <section className="bg-surface px-5 py-5">
        <h2 className="text-[13.5px] font-semibold">Method sensitivity on synthetic data</h2>
        <p className="mt-1 max-w-3xl text-[11.5px] leading-relaxed text-ink-muted">
          Recall against anomalies deliberately planted in the synthetic dataset, by pattern. This
          measures whether the method finds what was put there to be found. It is not accuracy, and
          it says nothing about how the engine would perform on live records.
        </p>

        <div className="mt-4 grid gap-x-8 gap-y-2 lg:grid-cols-2">
          {SENSITIVITY.map((s) => {
            const recall = (s.recalled / s.planted) * 100
            return (
              <div key={s.anomaly} className="grid grid-cols-[190px_1fr_92px] items-center gap-3">
                <span className="font-mono text-[11px] text-ink-muted">{s.anomaly}</span>
                <div className="h-3.5 rounded-[1px] bg-[#eceeef]">
                  <div
                    className="h-full rounded-[1px]"
                    style={{ width: `${recall}%`, backgroundColor: SEAL }}
                    title={`${s.anomaly}: ${s.recalled} of ${s.planted} planted instances recalled`}
                  />
                </div>
                <span className="text-right font-mono text-[11.5px] tabular-nums">
                  {pct(recall)}
                  <span className="ml-1 text-ink-faint">({s.planted})</span>
                </span>
              </div>
            )
          })}
        </div>

        <div className="mt-5 grid max-w-2xl gap-px bg-rule sm:grid-cols-2">
          <div className="bg-[#fafbfb] px-4 py-3">
            <div className="eyebrow">Flag rate on clean works</div>
            <div className="mt-1 font-mono text-[22px] leading-none font-medium tabular-nums">
              {FALSE_POSITIVE_RATE}%
            </div>
            <p className="mt-1.5 text-[11px] leading-snug text-ink-muted">
              Of {CLEAN_WORKS_TESTED.toLocaleString('en-IN')} works with no planted anomaly, this
              share still raised at least one finding.
            </p>
          </div>
          <div className="bg-[#fafbfb] px-4 py-3">
            <div className="eyebrow">What that means for a reviewer</div>
            <p className="mt-1.5 text-[11.5px] leading-relaxed text-ink-muted">
              Every finding is reviewed by a person before anything follows from it. A flag on a
              sound work costs a reviewer's time; it does not stop the work.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
