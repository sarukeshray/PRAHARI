import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { PageHeader } from '@/components/AppShell'
import { SeverityChip } from '@/components/SeverityChip'
import { ThresholdBar } from '@/components/ThresholdBar'
import { MODULE_LABEL, type ReviewAction, type RiskFlag, type Work } from '@/data/types'
import { complianceOverrideApplied } from '@/data/works'
import { rupees, shortDate } from '@/lib/format'
import { MIN_JUSTIFICATION, useReviews, useWork } from '@/lib/reviewStore'
import { SEVERITY_STYLE, tierForScore } from '@/lib/severity'
import { cn } from '@/lib/utils'

const REVIEWER = { name: 'S. Nair', role: 'District Authority' }

const FLAG_STATUS_LABEL: Record<string, string> = {
  OPEN: 'Open',
  UNDER_INVESTIGATION: 'Under investigation',
  OVERRIDDEN: 'Overridden',
  CLEARED: 'Cleared',
}

export function WorkDetail() {
  const { workId } = useParams()
  const work = useWork(workId)

  if (!work) {
    return (
      <div className="px-5 py-16 text-center">
        <p className="text-[13px] font-medium">Work not found</p>
        <Link to="/district" className="mt-2 inline-block text-[12px] text-seal hover:underline">
          Back to the review queue
        </Link>
      </div>
    )
  }

  const stage1 = work.flags.filter((f) => f.stage === 'STAGE_1')
  const stage2 = work.flags.filter((f) => f.stage === 'STAGE_2')

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/district" className="text-seal hover:underline">
              Review queue
            </Link>{' '}
            / {work.block} block
          </span>
        }
        title={work.workId}
        meta={work.description}
        actions={<SeverityChip severity={work.severity} />}
      />

      <div className="grid grid-cols-1 gap-px bg-rule xl:grid-cols-[280px_minmax(0,1fr)_300px]">
        <Particulars work={work} />

        <section className="bg-paper p-5">
          <h2 className="eyebrow">Findings</h2>

          {work.flags.length === 0 && (
            <div className="mt-3 rounded-[3px] border border-rule bg-surface px-4 py-8 text-center">
              <p className="text-[13px] font-medium">No findings raised</p>
              <p className="mt-1 text-[12px] text-ink-muted">
                This work was screened against all five pre-sanction modules and crossed no
                threshold.
              </p>
            </div>
          )}

          {stage1.length > 0 && (
            <FlagGroup
              title="Stage 1 — pre-sanction screening"
              note="Uses only what is known before sanction: cost, description, location, agency record and the compliance rules."
              flags={stage1}
              work={work}
            />
          )}

          {stage2.length > 0 && (
            <FlagGroup
              title="Stage 2 — post-sanction monitoring"
              note="Uses disbursement, progress reporting, photograph metadata and final cost."
              flags={stage2}
              work={work}
            />
          )}

          <AuditTrail work={work} />
        </section>

        <ScoreBreakdown work={work} />
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */

function Particulars({ work }: { work: Work }) {
  const rows: [string, React.ReactNode][] = [
    ['Work type', <span className="font-mono text-[12px]">{work.workType}</span>],
    ['Block', work.block],
    ['Panchayat', work.panchayat],
    ['Estimated cost', <span className="font-mono tabular-nums">{rupees(work.estimatedCost)}</span>],
    [
      'Final cost',
      work.finalCost ? (
        <span className="font-mono tabular-nums">{rupees(work.finalCost)}</span>
      ) : (
        <span className="text-ink-faint">Not yet recorded</span>
      ),
    ],
    ['Status', work.status.replace('_', ' ')],
    ['Recommended', shortDate(work.recommendedOn)],
    [
      'Sanctioned',
      work.sanctionedOn ? shortDate(work.sanctionedOn) : <span className="text-ink-faint">Pending</span>,
    ],
    ['Expected completion', shortDate(work.expectedCompletionOn)],
    ['Recommending Member', work.mpName],
    ['Constituency', `${work.constituency} · ${work.house.replace('_', ' ')}`],
    ['Implementing agency', work.agencyName],
    ['Agency type', <span className="font-mono text-[12px]">{work.agencyType}</span>],
    ['Terrain', <span className="font-mono text-[12px]">{work.terrain}</span>],
    ['SC/ST area', work.isScStArea ? 'Yes' : 'No'],
    [
      'Location',
      <span className="font-mono text-[11.5px] tabular-nums">
        {work.lat.toFixed(4)}, {work.lon.toFixed(4)}
      </span>,
    ],
  ]

  return (
    <aside className="bg-surface p-5">
      <h2 className="eyebrow">Particulars</h2>
      <dl className="mt-3 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[1fr_auto] items-baseline gap-3">
            <dt className="text-[11.5px] text-ink-muted">{label}</dt>
            <dd className="text-right text-[12.5px]">{value}</dd>
          </div>
        ))}
      </dl>
    </aside>
  )
}

/* -------------------------------------------------------------------------- */

function FlagGroup({
  title,
  note,
  flags,
  work,
}: {
  title: string
  note: string
  flags: RiskFlag[]
  work: Work
}) {
  return (
    <div className="mt-3">
      <div className="rounded-t-[3px] border border-rule bg-[#fafbfb] px-4 py-2">
        <div className="text-[12px] font-semibold">{title}</div>
        <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">{note}</p>
      </div>
      <div className="divide-y divide-rule rounded-b-[3px] border border-t-0 border-rule bg-surface">
        {flags.map((flag) => (
          <FlagCard key={flag.flagId} flag={flag} work={work} />
        ))}
      </div>
    </div>
  )
}

function FlagCard({ flag, work }: { flag: RiskFlag; work: Work }) {
  const { recordReview } = useReviews()
  const [pending, setPending] = useState<ReviewAction | null>(null)
  const [justification, setJustification] = useState('')

  const decided = flag.status !== 'OPEN'
  const needsJustification = pending === 'OVERRIDE'
  const tooShort = justification.trim().length < MIN_JUSTIFICATION
  const blocked = needsJustification && tooShort

  function submit() {
    if (!pending || blocked) return
    recordReview({
      workId: work.workId,
      flagId: flag.flagId,
      action: pending,
      reviewerName: REVIEWER.name,
      reviewerRole: REVIEWER.role,
      justification: justification.trim() || `Marked ${pending.toLowerCase()} without further note.`,
    })
    setPending(null)
    setJustification('')
  }

  return (
    <article className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">{flag.title}</h3>
            <SeverityChip severity={flag.severity} size="sm" />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] text-ink-faint">
            <span>{flag.code}</span>
            <span aria-hidden>·</span>
            <span>{MODULE_LABEL[flag.module]}</span>
            <span aria-hidden>·</span>
            <span>raised {shortDate(flag.raisedOn)}</span>
          </div>
        </div>
        {decided && (
          <span className="rounded-[2px] bg-[#eef0f1] px-2 py-0.5 text-[10.5px] font-medium tracking-wide text-ink-muted uppercase">
            {FLAG_STATUS_LABEL[flag.status]}
          </span>
        )}
      </div>

      <div className="mt-3 max-w-md">
        <ThresholdBar
          observed={flag.observed}
          observedLabel={flag.observedLabel}
          observedCaption={flag.observedCaption}
          threshold={flag.threshold}
          thresholdLabel={flag.thresholdLabel}
          thresholdCaption={flag.thresholdCaption}
          axisMax={flag.axisMax}
          severity={flag.severity}
        />
      </div>

      <p className="mt-3 border-l-2 border-rule-strong pl-3 text-[12.5px] leading-relaxed">
        {flag.explanation}
      </p>

      {!decided && (
        <div className="mt-3.5">
          <div className="flex flex-wrap gap-2">
            {(['INVESTIGATE', 'OVERRIDE', 'CLEAR'] as ReviewAction[]).map((action) => (
              <button
                key={action}
                type="button"
                onClick={() => {
                  setPending(pending === action ? null : action)
                  setJustification('')
                }}
                className={cn(
                  'rounded-[2px] border px-3 py-1 text-[12px] font-medium transition-colors',
                  pending === action
                    ? 'border-seal bg-seal text-white'
                    : 'border-rule-strong bg-surface text-ink hover:border-seal hover:text-seal',
                )}
              >
                {action === 'INVESTIGATE' ? 'Investigate' : action === 'OVERRIDE' ? 'Override' : 'Clear'}
              </button>
            ))}
          </div>

          {pending && (
            <div className="mt-3 rounded-[3px] border border-rule bg-[#fafbfb] p-3">
              <label
                htmlFor={`justification-${flag.flagId}`}
                className="block text-[11.5px] font-medium"
              >
                {needsJustification
                  ? 'Written justification (required)'
                  : 'Note for the record (optional)'}
              </label>
              <p className="mt-0.5 text-[11px] text-ink-muted">
                {needsJustification
                  ? `Overriding leaves this finding on the record with your reasoning attached. At least ${MIN_JUSTIFICATION} characters.`
                  : pending === 'INVESTIGATE'
                    ? 'The finding stays open and is marked as being looked into.'
                    : 'Clearing records that the finding was examined and needs no further action.'}
              </p>
              <textarea
                id={`justification-${flag.flagId}`}
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={3}
                className="mt-2 w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] outline-none focus:border-seal"
                placeholder={
                  needsJustification
                    ? 'Record why this finding does not warrant action…'
                    : 'Optional note…'
                }
              />
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-[11px] text-ink-muted">
                  {needsJustification && tooShort
                    ? `${MIN_JUSTIFICATION - justification.trim().length} more characters needed`
                    : ' '}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setPending(null)}
                    className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px]"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={submit}
                    disabled={blocked}
                    className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Record decision
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  )
}

/* -------------------------------------------------------------------------- */

function ScoreBreakdown({ work }: { work: Work }) {
  const overridden = complianceOverrideApplied(work)
  const scored = tierForScore(work.compositeScore)

  return (
    <aside className="bg-surface p-5">
      <h2 className="eyebrow">How this scored</h2>

      <div className="mt-3 rounded-[3px] border border-rule p-3">
        <div className="flex items-baseline justify-between">
          <span className="text-[11.5px] text-ink-muted">Composite</span>
          <span className="font-mono text-[22px] leading-none font-medium tabular-nums">
            {work.compositeScore}
            <span className="text-[12px] text-ink-faint">/100</span>
          </span>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <SeverityChip severity={work.severity} size="sm" />
          <span className="text-[11px] text-ink-muted">
            {work.stage === 'STAGE_1' ? 'Pre-sanction' : 'Post-sanction'} assessment
          </span>
        </div>
      </div>

      {overridden && (
        <p className="mt-2 rounded-[3px] border border-notice-rule bg-notice px-3 py-2 text-[11.5px] leading-snug text-notice-ink">
          The weighted score alone places this at {scored}. A compliance rule was broken, and a rule
          violation is a determinate fact rather than a statistical inference, so the tier is lifted
          to {work.severity}.
        </p>
      )}

      <div className="mt-4 space-y-3">
        {work.contributions.map((c) => {
          const contribution = c.score * c.weight
          // Bars are scaled against the largest contribution any single module
          // could make at this stage, so their lengths compare like for like.
          const ceiling = Math.max(...work.contributions.map((x) => x.weight)) * 100
          return (
            <div key={c.module}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[11.5px]">{MODULE_LABEL[c.module]}</span>
                <span className="font-mono text-[11.5px] tabular-nums text-ink-muted">
                  {contribution.toFixed(1)}
                </span>
              </div>
              <div className="mt-1 h-1.5 rounded-[1px] bg-[#eceeef]">
                <div
                  className="h-full rounded-[1px]"
                  style={{
                    width: `${(contribution / ceiling) * 100}%`,
                    backgroundColor:
                      c.score > 0 ? SEVERITY_STYLE[work.severity].hex : 'transparent',
                    opacity: 0.3 + 0.7 * (c.score / 100),
                  }}
                />
              </div>
              <div className="mt-0.5 font-mono text-[10.5px] text-ink-faint tabular-nums">
                {c.score} × {c.weight.toFixed(2)} weight
              </div>
            </div>
          )
        })}
      </div>

      <p className="mt-4 border-t border-rule pt-3 text-[11px] leading-relaxed text-ink-faint">
        The score exists so the tier can be traced. It is never the headline: a reviewer acts on the
        finding and its numbers, not on this figure.
      </p>
    </aside>
  )
}

/* -------------------------------------------------------------------------- */

function AuditTrail({ work }: { work: Work }) {
  return (
    <div className="mt-5">
      <h2 className="eyebrow">Review history</h2>
      {work.reviews.length === 0 ? (
        <p className="mt-2 rounded-[3px] border border-dashed border-rule-strong bg-surface px-4 py-5 text-center text-[12px] text-ink-muted">
          No decision has been recorded against this work yet.
        </p>
      ) : (
        <ol className="mt-2 divide-y divide-rule rounded-[3px] border border-rule bg-surface">
          {work.reviews.map((r) => (
            <li key={r.reviewId} className="px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-[12.5px] font-medium">
                  {r.action === 'INVESTIGATE'
                    ? 'Marked for investigation'
                    : r.action === 'OVERRIDE'
                      ? 'Overridden'
                      : 'Cleared'}
                </span>
                <span className="font-mono text-[11px] text-ink-faint">
                  {r.reviewerName} · {r.reviewerRole} · {shortDate(r.decidedAt)}
                </span>
              </div>
              <p className="mt-1 text-[12px] leading-snug text-ink-muted">{r.justification}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
