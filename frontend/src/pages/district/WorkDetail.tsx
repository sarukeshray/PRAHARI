import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useAssessWork, useReviewFlag, useWork } from '@/api/hooks'
import type { Assessment, Flag, ReviewAction, WorkDetail as WorkDetailType } from '@/api/types'
import {
  ErrorState,
  Loading,
  PageHeader,
  SeverityChip,
  SEVERITY_HEX,
  ThresholdBar,
} from '@/components/ui-kit'
import { PendingButton } from '@/components/Placeholder'
import { rupees, shortDate } from '@/lib/format'
import { MODULE_LABEL, STAGE_LABEL, STAGE_NOTE, flagTitle, signalLabel } from '@/lib/labels'
import { cn } from '@/lib/utils'

const MIN_JUSTIFICATION = 20

const STATUS_LABEL: Record<string, string> = {
  OPEN: 'Open',
  UNDER_INVESTIGATION: 'Under investigation',
  OVERRIDDEN: 'Overridden',
  CLEARED: 'Cleared',
}

export function WorkDetail() {
  const { workId } = useParams()
  const { data: work, isPending, isError, error, refetch } = useWork(workId)
  const assess = useAssessWork()

  if (isPending) return <Loading rows={10} label="Loading work" />
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
  if (!work) return null

  const current = [...work.assessments].sort(
    (a, b) => new Date(b.computed_at).getTime() - new Date(a.computed_at).getTime(),
  )
  const headline = work.severity_tier

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
        title={work.work_id}
        meta={work.description}
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => assess.mutate(work.work_id)}
              disabled={assess.isPending}
              className="rounded-[2px] border border-rule-strong px-2.5 py-1 text-[12px] hover:border-seal hover:text-seal disabled:opacity-50"
            >
              {assess.isPending ? 'Re-screening…' : 'Re-run screening'}
            </button>
            <SeverityChip severity={headline} />
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-px bg-rule xl:grid-cols-[272px_minmax(0,1fr)_288px]">
        <Particulars work={work} />

        <section className="bg-paper p-5">
          <h2 className="eyebrow">Findings</h2>

          {current.every((a) => a.flags.length === 0) && (
            <div className="mt-3 rounded-[3px] border border-rule bg-surface px-4 py-8 text-center">
              <p className="text-[13px] font-medium">No findings raised</p>
              <p className="mx-auto mt-1 max-w-sm text-[12px] leading-relaxed text-ink-muted">
                This work was screened against every module applicable at its stage and crossed no
                threshold.
              </p>
            </div>
          )}

          {current
            .filter((a) => a.flags.length > 0)
            .map((assessment) => (
              <StageGroup key={assessment.assessment_id} assessment={assessment} />
            ))}

          <AuditTrail assessments={work.assessments} />
        </section>

        <ScoreBreakdown work={work} />
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */

function Particulars({ work }: { work: WorkDetailType }) {
  const rows: [string, React.ReactNode][] = [
    ['Work type', <span className="font-mono text-[12px]">{work.work_type}</span>],
    ['Block', work.block],
    ['Panchayat', work.panchayat ?? '—'],
    ['Estimated cost', <span className="font-mono tabular-nums">{rupees(work.estimated_cost)}</span>],
    [
      'Final cost',
      work.final_cost ? (
        <span className="font-mono tabular-nums">{rupees(work.final_cost)}</span>
      ) : (
        <span className="text-ink-faint">Not yet recorded</span>
      ),
    ],
    ['Status', work.status.replace('_', ' ')],
    [
      'Disbursed',
      <span className="font-mono tabular-nums">
        {rupees(work.disbursed_amount)}{' '}
        <span className="text-ink-faint">({work.disbursed_pct.toFixed(0)}%)</span>
      </span>,
    ],
    [
      'Reported progress',
      <span className="font-mono tabular-nums">{work.latest_progress_pct.toFixed(0)}%</span>,
    ],
    ['Recommended', work.recommended_date ? shortDate(work.recommended_date) : '—'],
    ['Sanctioned', work.sanctioned_date ? shortDate(work.sanctioned_date) : 'Pending'],
    [
      'Completed',
      work.actual_completion_date ? shortDate(work.actual_completion_date) : '—',
    ],
    ['Recommending Member', work.mp_name ?? '—'],
    ['Constituency', work.constituency ?? '—'],
    ['Implementing agency', work.agency_name ?? 'Not assigned'],
    ['Terrain', <span className="font-mono text-[12px]">{work.terrain_category}</span>],
    ['SC/ST area', work.is_sc_st_area ? 'Yes' : 'No'],
    [
      'Evidence on file',
      `${work.photo_count} photograph${work.photo_count === 1 ? '' : 's'}, ${work.report_count} report${work.report_count === 1 ? '' : 's'}`,
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

function StageGroup({ assessment }: { assessment: Assessment }) {
  return (
    <div className="mt-3">
      <div className="rounded-t-[3px] border border-rule bg-[#fafbfb] px-4 py-2">
        <div className="text-[12px] font-semibold">{STAGE_LABEL[assessment.stage]}</div>
        <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">
          {STAGE_NOTE[assessment.stage]}
        </p>
      </div>
      <div className="divide-y divide-rule rounded-b-[3px] border border-t-0 border-rule bg-surface">
        {assessment.flags.map((flag) => (
          <FlagCard key={flag.flag_id} flag={flag} />
        ))}
      </div>
    </div>
  )
}

function FlagCard({ flag }: { flag: Flag }) {
  const review = useReviewFlag()
  const [pending, setPending] = useState<ReviewAction | null>(null)
  const [justification, setJustification] = useState('')

  const decided = flag.status !== 'OPEN'
  const needsJustification = pending === 'OVERRIDE'
  const short = justification.trim().length < MIN_JUSTIFICATION
  const blocked = needsJustification && short

  function submit() {
    if (!pending || blocked) return
    review.mutate(
      { flagId: flag.flag_id, action: pending, justification: justification.trim() },
      {
        onSuccess: () => {
          setPending(null)
          setJustification('')
        },
      },
    )
  }

  return (
    <article className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-[13.5px] font-semibold">{flagTitle(flag.flag_code)}</h3>
            <SeverityChip severity={flag.severity_tier} size="sm" />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 font-mono text-[11px] text-ink-faint">
            <span>{flag.flag_code}</span>
            <span aria-hidden>·</span>
            <span>{MODULE_LABEL[flag.module]}</span>
          </div>
        </div>
        {decided && (
          <span className="rounded-[2px] bg-[#eef0f1] px-2 py-0.5 text-[10.5px] font-medium tracking-wide text-ink-muted uppercase">
            {STATUS_LABEL[flag.status]}
          </span>
        )}
      </div>

      <div className="mt-3">
        <ThresholdBar
          observed={flag.signal_value}
          threshold={flag.threshold_value}
          severity={flag.severity_tier}
          observedLabel={signalLabel(flag.flag_code, flag.signal_value)}
          thresholdLabel={signalLabel(flag.flag_code, flag.threshold_value)}
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
                    : 'border-rule-strong bg-surface hover:border-seal hover:text-seal',
                )}
              >
                {action === 'INVESTIGATE'
                  ? 'Investigate'
                  : action === 'OVERRIDE'
                    ? 'Override'
                    : 'Clear'}
              </button>
            ))}
            <PendingButton title="Reassignment arrives with the escalation build">
              Reassign
            </PendingButton>
          </div>

          {pending && (
            <div className="mt-3 rounded-[3px] border border-rule bg-[#fafbfb] p-3">
              <label
                htmlFor={`justification-${flag.flag_id}`}
                className="block text-[11.5px] font-medium"
              >
                {needsJustification
                  ? 'Written justification (required)'
                  : 'Note for the record (optional)'}
              </label>
              <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">
                {needsJustification
                  ? `Overriding leaves this finding on the record with your reasoning attached. The API refuses an override under ${MIN_JUSTIFICATION} characters, so this is not just an interface rule.`
                  : pending === 'INVESTIGATE'
                    ? 'The finding stays open and is marked as being looked into.'
                    : 'Clearing records that the finding was examined and needs no further action.'}
              </p>
              <textarea
                id={`justification-${flag.flag_id}`}
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={3}
                placeholder={
                  needsJustification
                    ? 'Record why this finding does not warrant action…'
                    : 'Optional note…'
                }
                className="mt-2 w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] outline-none focus:border-seal"
              />
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-[11px] text-ink-muted">
                  {needsJustification && short
                    ? `${MIN_JUSTIFICATION - justification.trim().length} more characters needed`
                    : review.isError
                      ? (review.error as Error).message
                      : ' '}
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
                    disabled={blocked || review.isPending}
                    className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {review.isPending ? 'Recording…' : 'Record decision'}
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

function ScoreBreakdown({ work }: { work: WorkDetailType }) {
  const current = work.assessments.find((a) => a.severity_tier === work.severity_tier)
  if (!current) {
    return (
      <aside className="bg-surface p-5">
        <h2 className="eyebrow">How this scored</h2>
        <p className="mt-3 text-[12px] text-ink-muted">Not yet screened.</p>
      </aside>
    )
  }

  const ceiling = Math.max(...current.contributions.map((c) => c.weight), 0.01) * 100
  const hex = SEVERITY_HEX[current.severity_tier]

  // The tier can sit above what the weighted score alone produced, when a
  // compliance rule was broken or a single finding is more urgent than the
  // aggregate. Saying so is the point of this panel.
  const scoreTier =
    current.composite_score > 75
      ? 'CRITICAL'
      : current.composite_score > 50
        ? 'HIGH'
        : current.composite_score > 25
          ? 'MEDIUM'
          : 'LOW'
  const lifted = scoreTier !== current.severity_tier

  return (
    <aside className="bg-surface p-5">
      <h2 className="eyebrow">How this scored</h2>

      <div className="mt-3 rounded-[3px] border border-rule p-3">
        <div className="flex items-baseline justify-between">
          <span className="text-[11.5px] text-ink-muted">Composite</span>
          <span className="font-mono text-[22px] leading-none font-medium tabular-nums">
            {current.composite_score.toFixed(0)}
            <span className="text-[12px] text-ink-faint">/100</span>
          </span>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <SeverityChip severity={current.severity_tier} size="sm" />
          <span className="text-[11px] text-ink-muted">
            {STAGE_LABEL[current.stage].split('—')[0].trim()}
          </span>
        </div>
      </div>

      {lifted && (
        <p className="mt-2 rounded-[3px] border border-notice-rule bg-notice px-3 py-2 text-[11.5px] leading-snug text-notice-ink">
          The weighted score alone places this at {scoreTier}. It is shown as{' '}
          {current.severity_tier} because a rule violation is a determinate fact rather than a
          statistical inference, and an urgent finding is never presented inside a calmer headline.
        </p>
      )}

      <div className="mt-4 space-y-3">
        {current.contributions.map((c) => {
          const contribution = c.score * c.weight
          return (
            <div key={c.module}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[11.5px]">{MODULE_LABEL[c.module]}</span>
                <span className="font-mono text-[11.5px] text-ink-muted tabular-nums">
                  {contribution.toFixed(1)}
                </span>
              </div>
              <div className="mt-1 h-1.5 rounded-[1px] bg-[#eceeef]">
                <div
                  className="h-full rounded-[1px]"
                  style={{
                    width: `${Math.min(100, (contribution / ceiling) * 100)}%`,
                    backgroundColor: hex,
                    opacity: 0.35 + 0.65 * (c.score / 100),
                  }}
                />
              </div>
              <div className="mt-0.5 font-mono text-[10.5px] text-ink-faint tabular-nums">
                {c.score.toFixed(0)} × {c.weight.toFixed(2)} weight
              </div>
            </div>
          )
        })}
      </div>

      <p className="mt-4 border-t border-rule pt-3 text-[11px] leading-relaxed text-ink-faint">
        The score exists so the tier can be traced. It is never the headline: a reviewer acts on the
        finding and its numbers, not on this figure. Engine v{current.engine_version}.
      </p>
    </aside>
  )
}

/* -------------------------------------------------------------------------- */

function AuditTrail({ assessments }: { assessments: Assessment[] }) {
  const reviews = assessments
    .flatMap((a) => a.flags.flatMap((f) => f.reviews.map((r) => ({ ...r, code: f.flag_code }))))
    .sort((a, b) => new Date(b.decided_at).getTime() - new Date(a.decided_at).getTime())

  return (
    <div className="mt-5">
      <h2 className="eyebrow">Review history</h2>
      {reviews.length === 0 ? (
        <p className="mt-2 rounded-[3px] border border-dashed border-rule-strong bg-surface px-4 py-5 text-center text-[12px] text-ink-muted">
          No decision has been recorded against this work yet.
        </p>
      ) : (
        <ol className="mt-2 divide-y divide-rule rounded-[3px] border border-rule bg-surface">
          {reviews.map((r) => (
            <li key={r.review_id} className="px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-[12.5px] font-medium">
                  {r.action === 'INVESTIGATE'
                    ? 'Marked for investigation'
                    : r.action === 'OVERRIDE'
                      ? 'Overridden'
                      : 'Cleared'}
                  <span className="ml-2 font-mono text-[11px] font-normal text-ink-faint">
                    {r.code}
                  </span>
                </span>
                <span className="font-mono text-[11px] text-ink-faint">
                  {r.reviewer_name} · {shortDate(r.decided_at.slice(0, 10))}
                </span>
              </div>
              {r.justification && (
                <p className="mt-1 text-[12px] leading-snug text-ink-muted">{r.justification}</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
