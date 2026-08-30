import { PageHeader } from '@/components/AppShell'
import { SeverityChip } from '@/components/SeverityChip'
import { MP_SUMMARY } from '@/data/analytics'
import { pct, rupeesShort, shortDate } from '@/lib/format'
import { useReviews } from '@/lib/reviewStore'

const SEAL = '#16457e'

export function MPOverview() {
  const { works } = useReviews()
  const mine = works.filter((w) => w.mpName === MP_SUMMARY.name)
  const withFindings = mine.filter((w) => w.flags.length > 0)

  const usedPct = (MP_SUMMARY.recommended / MP_SUMMARY.entitlement) * 100

  return (
    <div>
      <PageHeader
        eyebrow={`${MP_SUMMARY.constituency} · ${MP_SUMMARY.house} · FY ${MP_SUMMARY.financialYear}`}
        title="My recommendations"
        meta="Where your entitlement stands, how the mandated area allocation is tracking, and anything raised against a work you recommended."
      />

      <div className="grid gap-px bg-rule lg:grid-cols-3">
        <section className="bg-surface px-5 py-4 lg:col-span-2">
          <h2 className="eyebrow">Entitlement, FY {MP_SUMMARY.financialYear}</h2>

          <div className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-[26px] leading-none font-medium tabular-nums">
                {rupeesShort(MP_SUMMARY.recommended)}
              </span>
              <span className="font-mono text-[12px] text-ink-muted tabular-nums">
                of {rupeesShort(MP_SUMMARY.entitlement)}
              </span>
            </div>
            <div className="mt-2 h-2.5 rounded-[1px] bg-[#eceeef]">
              <div
                className="h-full rounded-[1px]"
                style={{ width: `${usedPct}%`, backgroundColor: SEAL }}
              />
            </div>
            <div className="mt-1 text-[11.5px] text-ink-muted">
              {pct(usedPct, 1)} recommended · {rupeesShort(MP_SUMMARY.entitlement - MP_SUMMARY.recommended)}{' '}
              still available
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
            <Stat label="Works recommended" value={String(MP_SUMMARY.worksRecommended)} />
            <Stat label="Completed" value={String(MP_SUMMARY.worksCompleted)} />
            <Stat label="Sanctioned value" value={rupeesShort(MP_SUMMARY.sanctioned)} />
            <Stat label="Disbursed" value={rupeesShort(MP_SUMMARY.disbursed)} />
          </div>
        </section>

        <section className="bg-surface px-5 py-4">
          <h2 className="eyebrow">Mandated area allocation</h2>
          <div className="mt-3 space-y-4">
            <Quota
              label="SC-area allocation"
              actual={MP_SUMMARY.scAllocationPct}
              required={MP_SUMMARY.scRequiredPct}
            />
            <Quota
              label="ST-area allocation"
              actual={MP_SUMMARY.stAllocationPct}
              required={MP_SUMMARY.stRequiredPct}
            />
          </div>
        </section>
      </div>

      <section className="border-t border-rule bg-surface px-5 py-5">
        <h2 className="text-[13.5px] font-semibold">Works with an open finding</h2>
        <p className="mt-1 max-w-3xl text-[11.5px] leading-relaxed text-ink-muted">
          A finding is a request for a District Authority to look more closely. It is not a
          determination about you, the agency, or the work, and nothing is blocked while it is open.
        </p>

        {withFindings.length === 0 ? (
          <p className="mt-4 rounded-[3px] border border-dashed border-rule-strong px-4 py-6 text-center text-[12px] text-ink-muted">
            Nothing has been raised against your recommendations.
          </p>
        ) : (
          <div className="mt-4 divide-y divide-rule rounded-[3px] border border-rule">
            {withFindings.map((w) => (
              <div key={w.workId} className="px-4 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-mono text-[12px] font-medium">{w.workId}</span>
                  <SeverityChip severity={w.severity} size="sm" />
                </div>
                <div className="mt-0.5 font-mono text-[11px] text-ink-faint">
                  {w.workType} · {w.block} · recommended {shortDate(w.recommendedOn)}
                </div>
                <p className="mt-1.5 text-[12.5px] leading-snug">{w.flags[0].explanation}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className="mt-1 font-mono text-[17px] leading-none font-medium tabular-nums">{value}</div>
    </div>
  )
}

function Quota({ label, actual, required }: { label: string; actual: number; required: number }) {
  const met = actual >= required
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[12px]">{label}</span>
        <span className="font-mono text-[12.5px] tabular-nums">{pct(actual, 1)}</span>
      </div>
      <div className="relative mt-1.5 h-2.5 rounded-[1px] bg-[#eceeef]">
        <div
          className="absolute inset-y-0 left-0 rounded-[1px]"
          style={{ width: `${Math.min(actual * 4, 100)}%`, backgroundColor: met ? SEAL : '#a9670c' }}
        />
        <div
          aria-hidden
          className="absolute -top-1 -bottom-1 w-px bg-ink"
          style={{ left: `${Math.min(required * 4, 100)}%` }}
        />
      </div>
      <div className="mt-1 text-[11px] text-ink-muted">
        {met ? 'Above' : 'Below'} the mandated {pct(required, 1)}
        {!met && ' — this is tracked at district level and will be raised if the year closes short'}
      </div>
    </div>
  )
}
