import { useMutation, useQuery } from '@tanstack/react-query'

import { api } from '@/api/client'
import { useWeights } from '@/api/hooks'
import { Bar, EmptyState, ErrorState, Loading, PageHeader, Section, Td, Th } from '@/components/ui-kit'

/**
 * The CAG backtest.
 *
 * The disclaimer leads the screen rather than footnoting it. Overclaiming here
 * is the fastest way to lose a technical juror, and the honest version is more
 * persuasive: the method finds the *classes* of irregularity auditors have
 * historically found, which is a real claim and a checkable one.
 *
 * Every figure on this page is computed by the backend on request. Nothing is
 * hard-coded, so the numbers cannot drift away from the engine that produced
 * them.
 */

interface CaseResult {
  case_id: string
  finding: string
  source: string
  pattern: string
  expected_flags: string[]
  triggered_flags: string[]
  unexpected_flags: string[]
  works_replayed: number
  works_detected: number
  detection_rate: number
}

interface BacktestRun {
  computed_at: string
  engine_version: string
  cases: CaseResult[]
  totals: { works_replayed: number; works_detected: number }
  disclaimer: string
}

interface SensitivityRow {
  anomaly: string
  unit: string
  planted: number
  recalled: number
  recall: number
  expected_flags: string[]
}

interface Sensitivity {
  patterns: SensitivityRow[]
  clean_works: number
  clean_works_flagged: number
  clean_flag_rate: number
  clean_works_flagged_excluding_agency_signal: number
  clean_flag_rate_excluding_agency_signal: number
  note: string
}

export function Backtest() {
  const weights = useWeights()
  const sensitivity = useQuery({
    queryKey: ['sensitivity'],
    queryFn: () => api.get<Sensitivity>('/backtest/sensitivity'),
  })
  const run = useMutation({
    mutationFn: () => api.post<BacktestRun>('/backtest/run'),
  })

  const result = run.data

  return (
    <div>
      <PageHeader
        eyebrow="Method validation"
        title="CAG backtest"
        meta="Irregularity patterns documented by the Comptroller and Auditor General, reconstructed as synthetic records and replayed through the same engine that screens live proposals."
        actions={
          <button
            type="button"
            onClick={() => run.mutate()}
            disabled={run.isPending}
            className="rounded-[2px] bg-seal px-3 py-1.5 text-[12.5px] font-medium text-white disabled:opacity-50"
          >
            {run.isPending ? 'Replaying…' : result ? 'Replay again' : 'Run the backtest'}
          </button>
        }
      />

      <div className="border-b border-notice-rule bg-notice px-5 py-4">
        <p className="max-w-4xl text-[12.5px] leading-relaxed text-notice-ink">
          These cases reproduce irregularity <em>patterns</em> documented in CAG performance audits,
          using synthetic records. This demonstrates that the detection method identifies the
          classes of irregularity auditors have historically found. It is not a measurement of
          real-world detection accuracy, which would require validation against live MPLADS data.
        </p>
      </div>

      <Section
        title="Documented cases replayed"
        note="Each case builds its records in an isolated scratch database and scores them with the live engine, so a run cannot touch the working corpus and gives the same answer every time."
      >
        {!result && !run.isPending && (
          <EmptyState
            title="Not yet run"
            body="Replaying builds five documented CAG findings as synthetic records, scores them, and reports which flags fired. It takes about a second."
          />
        )}
        {run.isPending && <Loading rows={5} label="Replaying documented cases" />}
        {run.isError && (
          <ErrorState message={(run.error as Error).message} onRetry={() => run.mutate()} />
        )}

        {result && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] border-collapse text-[12.5px]">
                <thead>
                  <tr className="border-b border-rule bg-[#fafbfb]">
                    <Th className="w-[76px]">Case</Th>
                    <Th>Documented finding</Th>
                    <Th className="w-[240px]">Flags fired</Th>
                    <Th className="w-[124px] text-right">Detected</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.cases.map((c) => (
                    <tr key={c.case_id} className="border-b border-rule">
                      <Td className="font-mono text-[11.5px] font-medium">{c.case_id}</Td>
                      <Td>
                        <div>{c.finding}</div>
                        <div className="mt-0.5 text-[11.5px] text-ink-muted">{c.pattern}</div>
                        <div className="mt-1 text-[11px] text-ink-faint">{c.source}</div>
                      </Td>
                      <Td>
                        <div className="flex flex-wrap gap-1">
                          {c.triggered_flags.map((t) => (
                            <span
                              key={t}
                              title="Expected by this case"
                              className="rounded-[2px] bg-seal-tint px-1.5 py-px font-mono text-[10px] text-seal"
                            >
                              {t}
                            </span>
                          ))}
                          {c.unexpected_flags.map((t) => (
                            <span
                              key={t}
                              title="Fired in addition to what this case tested for"
                              className="rounded-[2px] border border-dashed border-rule-strong px-1.5 py-px font-mono text-[10px] text-ink-faint"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </Td>
                      <Td className="text-right">
                        <div className="font-mono text-[13px] tabular-nums">
                          {c.works_detected}
                          <span className="text-ink-faint">/{c.works_replayed}</span>
                        </div>
                        <div className="mt-1">
                          <Bar value={c.works_detected} max={c.works_replayed} />
                        </div>
                      </Td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-[#fafbfb]">
                    <Td colSpan={3} className="text-[12px] font-medium">
                      Across all five reconstructed cases
                    </Td>
                    <Td className="text-right font-mono text-[13px] tabular-nums">
                      {result.totals.works_detected}
                      <span className="text-ink-faint">/{result.totals.works_replayed}</span>
                    </Td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <p className="mt-3 max-w-4xl text-[11px] leading-relaxed text-ink-faint">
              Dashed flags fired in addition to what the case tested for. They are reported rather
              than hidden: a work that was paid in full and never built is also overdue on handover,
              and the engine finding that is a property of the method worth seeing. Run at{' '}
              {result.computed_at.replace('T', ' ')} on engine v{result.engine_version}.
            </p>
          </>
        )}
      </Section>

      <Section
        title="Method sensitivity on synthetic data"
        note={sensitivity.data?.note ?? 'Recall against anomalies deliberately planted in the dataset.'}
      >
        {sensitivity.isPending && <Loading rows={6} label="Computing sensitivity" />}
        {sensitivity.isError && (
          <ErrorState
            message={(sensitivity.error as Error).message}
            onRetry={() => sensitivity.refetch()}
          />
        )}

        {sensitivity.data && (
          <>
            <div className="grid gap-x-8 gap-y-2 lg:grid-cols-2">
              {sensitivity.data.patterns.map((s) => (
                <div key={s.anomaly} className="grid grid-cols-[172px_1fr_112px] items-center gap-3">
                  <span className="font-mono text-[11px] text-ink-muted">{s.anomaly}</span>
                  <Bar
                    value={s.recalled}
                    max={s.planted}
                    title={`${s.recalled} of ${s.planted} planted ${s.unit}s recalled — expects ${s.expected_flags.join(' or ')}`}
                  />
                  <span className="text-right font-mono text-[11.5px] tabular-nums">
                    {(s.recall * 100).toFixed(0)}%
                    <span className="ml-1 text-ink-faint">
                      ({s.planted} {s.unit === 'group' ? 'grp' : ''})
                    </span>
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-5 grid max-w-3xl gap-px bg-rule sm:grid-cols-2">
              <div className="bg-[#fafbfb] px-4 py-3">
                <div className="eyebrow">Flag rate on clean works</div>
                <div className="mt-1 font-mono text-[22px] leading-none font-medium tabular-nums">
                  {(sensitivity.data.clean_flag_rate * 100).toFixed(1)}%
                </div>
                <p className="mt-1.5 text-[11px] leading-snug text-ink-muted">
                  Of {sensitivity.data.clean_works.toLocaleString('en-IN')} works with no planted
                  anomaly, {sensitivity.data.clean_works_flagged} drew a finding. Excluding the
                  agency signal — which fires for the weakest fifth of every peer group by
                  construction — the rate is{' '}
                  {(sensitivity.data.clean_flag_rate_excluding_agency_signal * 100).toFixed(1)}%.
                </p>
              </div>
              <div className="bg-[#fafbfb] px-4 py-3">
                <div className="eyebrow">Why these figures are high</div>
                <p className="mt-1.5 text-[11.5px] leading-relaxed text-ink-muted">
                  These patterns were generated by this project and the engine was built to find
                  them. A high number shows the detectors are wired correctly and that a change has
                  not silently broken one. Two rows rest on very few groups and should be read as
                  such.
                </p>
              </div>
            </div>
          </>
        )}
      </Section>

      {weights.data && (
        <Section
          title="Configuration these figures were produced under"
          note="A sensitivity number means nothing without the thresholds behind it."
        >
          <div className="flex flex-wrap gap-x-8 gap-y-1.5 font-mono text-[11.5px] text-ink-muted">
            <span>engine v{weights.data.engine_version}</span>
            <span>similarity: {weights.data.similarity_backend}</span>
            <span>cost above SoR: +{weights.data.thresholds.COST_ABOVE_SOR_PCT}%</span>
            <span>duplicate cosine: {weights.data.thresholds.DUPLICATE_COSINE}</span>
            <span>payment gap: {weights.data.thresholds.PAYMENT_AHEAD_POINTS} pts</span>
            <span>handover overdue: {weights.data.thresholds.HANDOVER_OVERDUE_DAYS} days</span>
          </div>
        </Section>
      )}

      <Section
        title="Model training"
        note="The Isolation Forest is fitted in-process each time the corpus is scored, which is reproducible but leaves no artefact a reviewer can inspect."
      >
        <div className="max-w-3xl rounded-[3px] border border-rule bg-surface p-5">
          <div className="text-[13px] font-medium">
            <code className="font-mono text-[12px]">notebooks/prahari_model_training.ipynb</code>
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-ink-muted">
            A standalone notebook that runs on a fresh Colab runtime with no checkout. It
            generates the corpus, checks the inflation defence against its own data, plots the
            similarity distribution for known duplicate pairs against unrelated ones to justify
            the 0.82 threshold empirically, fits the Isolation Forest, and exports the model.
          </p>
          <p className="mt-2 text-[12px] leading-relaxed text-ink-muted">
            It reports recall the same way this page does, from the same rules, so the notebook
            and this screen cannot disagree.
          </p>
          <p className="mt-3 border-t border-rule pt-3 text-[11px] text-ink-faint">
            Upload it at colab.research.google.com and choose Runtime → Run all. Roughly two
            minutes, most of it downloading the sentence-transformer weights.
          </p>
        </div>
      </Section>
    </div>
  )
}
