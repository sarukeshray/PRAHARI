import { useState } from 'react'

import { useFlags, useNational, useUpdateWeights, useWeights } from '@/api/hooks'
import {
  EmptyState,
  ErrorState,
  Loading,
  PageHeader,
  Section,
  SeverityChip,
  Stat,
  Td,
  Th,
} from '@/components/ui-kit'
import { rupeesShort } from '@/lib/format'
import { MODULE_LABEL, flagTitle } from '@/lib/labels'

const SEAL = '#16457e'
const CRITICAL = '#ae1414'

export function MinistryOverview() {
  const { data, isPending, isError, error, refetch } = useNational()

  if (isPending) return <Loading rows={8} label="Loading national position" />
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
  if (!data) return null

  const maxUtil = 100
  const maxCritical = Math.max(...data.states.map((s) => s.open_critical), 1)

  return (
    <div>
      <PageHeader
        eyebrow="Ministry of Statistics and Programme Implementation · DIID"
        title="National overview"
        meta="Cross-state position and the findings that have gone longest without a decision."
      />

      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule lg:grid-cols-4">
        <Stat label="Works screened" value={data.totals.works.toLocaleString('en-IN')} />
        <Stat label="Open findings" value={data.totals.open_findings.toLocaleString('en-IN')} />
        <Stat
          label="Unresolved critical"
          value={data.totals.unresolved_critical.toLocaleString('en-IN')}
          accent={CRITICAL}
          hint="Awaiting a district decision"
        />
        <Stat label="Districts live" value={String(data.totals.districts)} />
      </div>

      <Section
        title="Fund utilisation by state"
        note="The share of sanctioned value accounted for by released funds. Persistent under-utilisation is the Scheme's most consistently documented problem, and is measurable without inferring anything about intent."
      >
        <div className="max-w-3xl space-y-2">
          {[...data.states]
            .sort((a, b) => b.utilisation_pct - a.utilisation_pct)
            .map((s) => (
              <div key={s.state} className="grid grid-cols-[140px_1fr_120px] items-center gap-3">
                <span className="text-[12px] text-ink-muted">{s.state}</span>
                <div className="h-4 rounded-[1px] bg-[#eceeef]">
                  <div
                    className="h-full rounded-[1px]"
                    style={{
                      width: `${(s.utilisation_pct / maxUtil) * 100}%`,
                      backgroundColor: SEAL,
                    }}
                    title={`${s.state}: ${s.utilisation_pct}% of ${rupeesShort(s.sanctioned_amount)} sanctioned`}
                  />
                </div>
                <span className="text-right font-mono text-[11.5px] tabular-nums">
                  {s.utilisation_pct.toFixed(1)}%
                  <span className="ml-1 text-ink-faint">{rupeesShort(s.disbursed_amount)}</span>
                </span>
              </div>
            ))}
        </div>
      </Section>

      <Section
        title="Open findings by state"
        note="A high count is a workload signal, not a judgement about a state — a state that screens more works will raise more findings."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb]">
                <Th>State</Th>
                <Th className="text-right">Works</Th>
                <Th className="text-right">Sanctioned</Th>
                <Th className="text-right">Utilisation</Th>
                <Th className="text-right">Critical</Th>
                <Th className="text-right">High</Th>
                <Th className="w-[140px]">Critical load</Th>
              </tr>
            </thead>
            <tbody>
              {data.states.map((s) => (
                <tr key={s.state} className="border-b border-rule">
                  <Td>{s.state}</Td>
                  <Td className="text-right font-mono tabular-nums">
                    {s.works.toLocaleString('en-IN')}
                  </Td>
                  <Td className="text-right font-mono tabular-nums">
                    {rupeesShort(s.sanctioned_amount)}
                  </Td>
                  <Td className="text-right font-mono tabular-nums">
                    {s.utilisation_pct.toFixed(1)}%
                  </Td>
                  <Td className="text-right font-mono tabular-nums">{s.open_critical}</Td>
                  <Td className="text-right font-mono tabular-nums">{s.open_high}</Td>
                  <Td>
                    <div className="h-1.5 rounded-[1px] bg-[#eceeef]">
                      <div
                        className="h-full rounded-[1px]"
                        style={{
                          width: `${(s.open_critical / maxCritical) * 100}%`,
                          backgroundColor: CRITICAL,
                        }}
                      />
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  )
}

/* -------------------------------------------------------------------------- */

export function MinistryEscalations() {
  const flags = useFlags({ status: 'OPEN', severity: 'CRITICAL' })

  return (
    <div>
      <PageHeader
        eyebrow="Escalations"
        title="Unresolved critical findings"
        meta="Critical findings still awaiting a decision anywhere in the country."
      />
      {flags.isPending && <Loading rows={6} label="Loading escalations" />}
      {flags.isError && (
        <ErrorState message={(flags.error as Error).message} onRetry={() => flags.refetch()} />
      )}
      {flags.data?.length === 0 && (
        <EmptyState
          title="Nothing critical is outstanding"
          body="Every critical finding raised has had a decision recorded against it."
        />
      )}
      {flags.data && flags.data.length > 0 && (
        <ul className="divide-y divide-rule">
          {flags.data.slice(0, 60).map((f) => (
            <li key={f.flag_id} className="bg-surface px-5 py-3.5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[12px] font-medium">{f.work_id}</span>
                  <SeverityChip severity={f.severity_tier} size="sm" />
                </div>
                <span className="font-mono text-[11px] text-ink-faint">
                  {MODULE_LABEL[f.module]}
                </span>
              </div>
              <div className="mt-1 text-[12.5px] font-medium">{flagTitle(f.flag_code)}</div>
              <p className="mt-0.5 text-[12px] leading-snug text-ink-muted">{f.explanation}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */

export function MinistryThresholds() {
  const weights = useWeights()
  const update = useUpdateWeights()
  const [edits, setEdits] = useState<Record<string, string>>({})

  if (weights.isPending) return <Loading rows={8} label="Loading configuration" />
  if (weights.isError)
    return <ErrorState message={(weights.error as Error).message} onRetry={() => weights.refetch()} />
  if (!weights.data) return null

  const w = weights.data

  function save() {
    const body: Record<string, Record<string, number>> = { thresholds: {} }
    for (const [key, value] of Object.entries(edits)) {
      const n = Number(value)
      if (!Number.isNaN(n)) body.thresholds[key] = n
    }
    if (Object.keys(body.thresholds).length) update.mutate(body, { onSuccess: () => setEdits({}) })
  }

  return (
    <div>
      <PageHeader
        eyebrow="Engine configuration"
        title="Thresholds"
        meta={`Engine v${w.engine_version} · similarity backend: ${w.similarity_backend}`}
        actions={
          <button
            type="button"
            onClick={save}
            disabled={!Object.keys(edits).length || update.isPending}
            className="rounded-[2px] bg-seal px-3 py-1.5 text-[12.5px] font-medium text-white disabled:opacity-40"
          >
            {update.isPending ? 'Saving…' : `Save ${Object.keys(edits).length || ''} change(s)`}
          </button>
        }
      />

      <div className="border-b border-notice-rule bg-notice px-5 py-3">
        <p className="max-w-4xl text-[12px] leading-relaxed text-notice-ink">
          Changes take effect on the next screening run. Existing assessments keep the scores they
          were computed with, so a decision already taken stays traceable to the configuration it
          was taken under.
        </p>
      </div>

      <Section title="Stage weights" note="Each stage's weights sum to 1.0.">
        <div className="grid gap-6 sm:grid-cols-3">
          {(['stage1', 'stage2', 'stage3'] as const).map((stage) => (
            <div key={stage}>
              <div className="eyebrow">{stage.replace('stage', 'Stage ')}</div>
              <div className="mt-2 space-y-1.5">
                {Object.entries(w[stage]).map(([k, v]) => (
                  <div key={k} className="flex items-baseline justify-between gap-3 text-[12px]">
                    <span className="text-ink-muted">{MODULE_LABEL[k as never] ?? k}</span>
                    <span className="font-mono tabular-nums">{v.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 space-y-2 border-t border-rule pt-3">
          {Object.entries(w.notes).map(([k, note]) => (
            <p key={k} className="max-w-3xl text-[11.5px] leading-relaxed text-ink-muted">
              {note}
            </p>
          ))}
        </div>
      </Section>

      <Section
        title="Flagging thresholds"
        note="The value each module compares its signal against. Raising one makes the engine quieter and costs recall; lowering it costs a reviewer's time."
      >
        <div className="grid gap-x-8 gap-y-2 lg:grid-cols-2">
          {Object.entries(w.thresholds).map(([key, value]) => (
            <div key={key} className="grid grid-cols-[minmax(0,1fr)_92px] items-center gap-3">
              <label htmlFor={`t-${key}`} className="font-mono text-[11.5px] text-ink-muted">
                {key}
              </label>
              <input
                id={`t-${key}`}
                value={edits[key] ?? String(value)}
                onChange={(e) => setEdits({ ...edits, [key]: e.target.value })}
                className="w-full rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-right font-mono text-[12px] tabular-nums focus:border-seal"
              />
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
