import { useWeights } from '@/api/hooks'
import { PlaceholderPanel } from '@/components/Placeholder'
import { Bar, Loading, PageHeader, Section, Td, Th } from '@/components/ui-kit'

/**
 * The CAG backtest.
 *
 * The disclaimer leads the screen rather than footnoting it. Overclaiming here
 * is the fastest way to lose a technical juror, and the honest version is more
 * persuasive: the method finds the *classes* of irregularity auditors have
 * historically found, which is a real claim and a checkable one.
 *
 * Cases are documented findings reconstructed as synthetic records. Sensitivity
 * figures come from the engine's own run against the planted answer key —
 * regenerate them with `python -m app.engine.cli recall`.
 */

const CASES = [
  {
    id: 'CAG-01',
    finding: '₹53.74 crore spent on works inadmissible under the Scheme',
    pattern: 'Works whose type falls outside the MPLADS permissible list.',
    expected: ['WORK_TYPE_NOT_PERMISSIBLE'],
    extra: [],
    replayed: 40,
    detected: 40,
  },
  {
    id: 'CAG-02',
    finding: '775 sanctioned works worth ₹10.18 crore never taken up',
    pattern: 'Sanctioned, funds released, no progress reports and no photographs.',
    expected: ['GHOST_WORK', 'FULLY_PAID_INCOMPLETE', 'NO_COMPLETION_EVIDENCE'],
    extra: [],
    replayed: 40,
    detected: 40,
  },
  {
    id: 'CAG-03',
    finding: '568 works costing ₹7.30 crore delayed in completion',
    pattern: 'Sanctioned more than twelve months prior, progress under 100%.',
    expected: ['COMPLETION_OVERDUE_12M'],
    extra: ['PROGRESS_REPORTING_STALLED'],
    replayed: 182,
    detected: 182,
  },
  {
    id: 'CAG-04',
    finding: '558 works executed without a Member recommendation',
    pattern: 'A sanction date recorded against no recommendation.',
    expected: ['MISSING_RECOMMENDATION'],
    extra: [],
    replayed: 45,
    detected: 45,
  },
  {
    id: 'CAG-05',
    finding: 'Inflated cost estimation without detailed survey',
    pattern: 'Estimates set far above the Schedule of Rates for the work type.',
    expected: ['COST_ABOVE_SOR', 'COST_PEER_OUTLIER'],
    extra: ['STATISTICAL_OUTLIER'],
    replayed: 40,
    detected: 40,
  },
]

const SENSITIVITY = [
  { anomaly: 'COST_INFLATION', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'DUPLICATE_WORK', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'SALAMI_SLICING', unit: 'work', n: 41, caught: 41 },
  { anomaly: 'PAYMENT_AHEAD', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'GEOTAG_MISMATCH', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'PHOTO_REUSE', unit: 'work', n: 80, caught: 80 },
  { anomaly: 'TIMELINE_BREACH', unit: 'work', n: 182, caught: 182 },
  { anomaly: 'COST_OVERRUN', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'GHOST_WORK', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'HANDOVER_GAP', unit: 'work', n: 40, caught: 40 },
  { anomaly: 'ENTITLEMENT_BREACH', unit: 'group', n: 2, caught: 2 },
  { anomaly: 'QUOTA_SHORTFALL', unit: 'group', n: 1, caught: 1 },
]

const CLEAN_WORKS = 3277
const CLEAN_FLAGGED = 186

export function Backtest() {
  const weights = useWeights()
  const totalReplayed = CASES.reduce((n, c) => n + c.replayed, 0)
  const totalDetected = CASES.reduce((n, c) => n + c.detected, 0)

  return (
    <div>
      <PageHeader
        eyebrow="Method validation"
        title="CAG backtest"
        meta="Irregularity patterns documented by the Comptroller and Auditor General, reconstructed as synthetic records and replayed through the same engine that screens live proposals."
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
        note="Source: CAG Report No. 31 of 2010, Performance Audit of MPLADS, and later compliance reports."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb]">
                <Th className="w-[72px]">Case</Th>
                <Th>Documented finding</Th>
                <Th className="w-[236px]">Flags triggered</Th>
                <Th className="w-[124px] text-right">Detected</Th>
              </tr>
            </thead>
            <tbody>
              {CASES.map((c) => (
                <tr key={c.id} className="border-b border-rule">
                  <Td className="font-mono text-[11.5px] font-medium">{c.id}</Td>
                  <Td>
                    <div>{c.finding}</div>
                    <div className="mt-0.5 text-[11.5px] text-ink-muted">{c.pattern}</div>
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      {c.expected.map((t) => (
                        <span
                          key={t}
                          className="rounded-[2px] bg-seal-tint px-1.5 py-px font-mono text-[10px] text-seal"
                          title="Expected"
                        >
                          {t}
                        </span>
                      ))}
                      {c.extra.map((t) => (
                        <span
                          key={t}
                          className="rounded-[2px] border border-dashed border-rule-strong px-1.5 py-px font-mono text-[10px] text-ink-faint"
                          title="Fired in addition to the expected flags"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </Td>
                  <Td className="text-right">
                    <div className="font-mono text-[13px] tabular-nums">
                      {c.detected}
                      <span className="text-ink-faint">/{c.replayed}</span>
                    </div>
                    <div className="mt-1">
                      <Bar value={c.detected} max={c.replayed} />
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
                  {totalDetected}
                  <span className="text-ink-faint">/{totalReplayed}</span>
                </Td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-ink-faint">
          Dashed flags fired in addition to those the case was built to trigger. They are reported
          rather than hidden, because an unexpected flag is as much a property of the method as an
          expected one.
        </p>
      </Section>

      <Section
        title="Method sensitivity on synthetic data"
        note="Recall against anomalies deliberately planted in the synthetic dataset. This measures whether the method finds what was put there to be found. It is not accuracy, and it says nothing about how the engine would perform on live records."
      >
        <div className="grid gap-x-8 gap-y-2 lg:grid-cols-2">
          {SENSITIVITY.map((s) => {
            const recall = (s.caught / s.n) * 100
            return (
              <div key={s.anomaly} className="grid grid-cols-[172px_1fr_104px] items-center gap-3">
                <span className="font-mono text-[11px] text-ink-muted">{s.anomaly}</span>
                <Bar
                  value={s.caught}
                  max={s.n}
                  title={`${s.caught} of ${s.n} planted ${s.unit}s recalled`}
                />
                <span className="text-right font-mono text-[11.5px] tabular-nums">
                  {recall.toFixed(0)}%
                  <span className="ml-1 text-ink-faint">
                    ({s.n} {s.unit === 'group' ? 'grp' : ''})
                  </span>
                </span>
              </div>
            )
          })}
        </div>

        <div className="mt-5 grid max-w-3xl gap-px bg-rule sm:grid-cols-2">
          <div className="bg-[#fafbfb] px-4 py-3">
            <div className="eyebrow">Flag rate on clean works</div>
            <div className="mt-1 font-mono text-[22px] leading-none font-medium tabular-nums">
              {((CLEAN_FLAGGED / CLEAN_WORKS) * 100).toFixed(1)}%
            </div>
            <p className="mt-1.5 text-[11px] leading-snug text-ink-muted">
              Of {CLEAN_WORKS.toLocaleString('en-IN')} works with no planted anomaly, this share
              still drew a finding — mostly the agency signal, which fires for the weakest fifth of
              every peer group by definition.
            </p>
          </div>
          <div className="bg-[#fafbfb] px-4 py-3">
            <div className="eyebrow">Why the recall figures are high</div>
            <p className="mt-1.5 text-[11.5px] leading-relaxed text-ink-muted">
              These patterns were generated by this project and the engine was built to find them.
              A high number shows the detectors are wired correctly and that a change has not
              silently broken one. Two rows rest on very few groups and should be read as such.
            </p>
          </div>
        </div>
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
      {weights.isPending && <Loading rows={2} label="Loading configuration" />}

      <Section
        title="Model training"
        note="The Isolation Forest is currently fitted in-process each time the corpus is scored, which is reproducible but leaves no artefact a reviewer can inspect."
      >
        <PlaceholderPanel
          title="Training notebook"
          body="A standalone Colab notebook that generates the dataset, fits the model, plots the similarity-score distribution for known duplicate pairs against non-duplicates to justify the 0.82 cosine threshold empirically, and exports the fitted model. It reports the same recall figures shown above, from the same code path, so the notebook and this screen cannot disagree."
          waitingOn="notebooks/prahari_model_training.ipynb"
        />
      </Section>
    </div>
  )
}
