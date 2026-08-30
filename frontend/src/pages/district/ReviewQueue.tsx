import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { PageHeader } from '@/components/AppShell'
import { SeverityChip } from '@/components/SeverityChip'
import { MODULE_LABEL, type ModuleCode } from '@/data/types'
import { BLOCKS, DISTRICT } from '@/data/works'
import { rupeesShort, shortDate } from '@/lib/format'
import { useReviews } from '@/lib/reviewStore'
import { SEVERITIES, SEVERITY_RANK, SEVERITY_STYLE, type Severity } from '@/lib/severity'
import { cn } from '@/lib/utils'

type ModuleFilter = ModuleCode | 'ALL'

export function ReviewQueue() {
  const { works } = useReviews()
  const [severity, setSeverity] = useState<Severity | 'ALL'>('ALL')
  const [module, setModule] = useState<ModuleFilter>('ALL')
  const [block, setBlock] = useState<string>('ALL')
  const [onlyFindings, setOnlyFindings] = useState(true)

  const counts = useMemo(() => {
    const base: Record<Severity, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
    for (const w of works) base[w.severity] += 1
    return base
  }, [works])

  const rows = useMemo(() => {
    return works
      .filter((w) => (severity === 'ALL' ? true : w.severity === severity))
      .filter((w) => (block === 'ALL' ? true : w.block === block))
      .filter((w) => (module === 'ALL' ? true : w.flags.some((f) => f.module === module)))
      .filter((w) => (onlyFindings ? w.flags.length > 0 : true))
      .sort(
        (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || b.daysOpen - a.daysOpen,
      )
  }, [works, severity, block, module, onlyFindings])

  const openFindings = works.reduce((n, w) => n + w.flags.filter((f) => f.status === 'OPEN').length, 0)

  return (
    <div>
      <PageHeader
        eyebrow={`${DISTRICT.name} district · ${DISTRICT.state}`}
        title="Review queue"
        meta={`${openFindings} findings awaiting a decision · ${DISTRICT.worksScreenedThisYear} works screened this financial year`}
      />

      {/* Counters. Clicking one filters the table rather than opening a new view. */}
      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule sm:grid-cols-4">
        {SEVERITIES.map((tier) => {
          const active = severity === tier
          return (
            <button
              key={tier}
              type="button"
              aria-pressed={active}
              onClick={() => setSeverity(active ? 'ALL' : tier)}
              className={cn(
                'group px-5 py-3 text-left transition-colors',
                active ? 'bg-seal-tint' : 'bg-surface hover:bg-[#fafbfb]',
              )}
            >
              <div className="flex items-center gap-2">
                <SeverityChip severity={tier} size="sm" />
              </div>
              <div className="mt-1.5 font-mono text-[26px] leading-none font-medium tabular-nums">
                {counts[tier]}
              </div>
              <div className="mt-1 text-[11px] text-ink-muted">
                {counts[tier] === 1 ? 'work' : 'works'}
              </div>
            </button>
          )
        })}
      </div>

      {/* Filters sit in one row above the table. */}
      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-5 py-2.5">
        <Select
          label="Module"
          value={module}
          onChange={(v) => setModule(v as ModuleFilter)}
          options={[
            { value: 'ALL', label: 'All modules' },
            ...(Object.keys(MODULE_LABEL) as ModuleCode[]).map((m) => ({
              value: m,
              label: MODULE_LABEL[m],
            })),
          ]}
        />
        <Select
          label="Block"
          value={block}
          onChange={setBlock}
          options={[
            { value: 'ALL', label: 'All blocks' },
            ...BLOCKS.map((b) => ({ value: b, label: b })),
          ]}
        />
        <label className="ml-auto flex items-center gap-2 text-[12px] text-ink-muted">
          <input
            type="checkbox"
            checked={onlyFindings}
            onChange={(e) => setOnlyFindings(e.target.checked)}
            className="size-3.5 accent-[#16457e]"
          />
          Only works with findings
        </label>
        {(severity !== 'ALL' || module !== 'ALL' || block !== 'ALL') && (
          <button
            type="button"
            onClick={() => {
              setSeverity('ALL')
              setModule('ALL')
              setBlock('ALL')
            }}
            className="text-[12px] text-seal underline-offset-2 hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] border-collapse text-[12.5px]">
          <thead>
            <tr className="border-b border-rule bg-[#fafbfb] text-left">
              <Th className="w-[168px]">Work ID</Th>
              <Th className="w-[150px]">Type</Th>
              <Th className="w-[110px]">Block</Th>
              <Th className="w-[110px] text-right">Estimate</Th>
              <Th className="w-[104px]">Severity</Th>
              <Th>Primary finding</Th>
              <Th className="w-[86px] text-right">Days open</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w) => {
              const primary = w.flags[0]
              return (
                <tr
                  key={w.workId}
                  className="ledger-row border-b border-rule align-top"
                  style={{ '--row-accent': SEVERITY_STYLE[w.severity].hex } as React.CSSProperties}
                >
                  <Td>
                    <Link
                      to={`/district/works/${w.workId}`}
                      className="font-mono text-[12px] text-seal hover:underline"
                    >
                      {w.workId}
                    </Link>
                    <div className="mt-0.5 text-[11px] text-ink-faint">
                      {shortDate(w.recommendedOn)}
                    </div>
                  </Td>
                  <Td>
                    <span className="font-mono text-[11.5px]">{w.workType}</span>
                    <div className="mt-0.5 text-[11px] text-ink-faint">
                      {w.stage === 'STAGE_1' ? 'Pre-sanction' : 'Post-sanction'}
                    </div>
                  </Td>
                  <Td className="text-ink-muted">{w.block}</Td>
                  <Td className="text-right font-mono tabular-nums">
                    {rupeesShort(w.estimatedCost)}
                  </Td>
                  <Td>
                    <SeverityChip severity={w.severity} size="sm" />
                  </Td>
                  <Td>
                    {primary ? (
                      <>
                        <div className="font-medium">{primary.title}</div>
                        <div className="mt-0.5 line-clamp-2 text-[11.5px] leading-snug text-ink-muted">
                          {primary.explanation}
                        </div>
                        {w.flags.length > 1 && (
                          <div className="mt-1 text-[11px] text-ink-faint">
                            +{w.flags.length - 1} further{' '}
                            {w.flags.length === 2 ? 'finding' : 'findings'}
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="text-[11.5px] text-ink-faint">
                        Screened, no finding raised
                      </span>
                    )}
                  </Td>
                  <Td className="text-right font-mono tabular-nums text-ink-muted">{w.daysOpen}</Td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {rows.length === 0 && (
          <div className="px-5 py-14 text-center">
            <p className="text-[13px] font-medium">No works match these filters</p>
            <p className="mt-1 text-[12px] text-ink-muted">
              Widen the module or block filter, or clear the severity selection above.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={cn(
        'px-3 py-2 text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase',
        className,
      )}
    >
      {children}
    </th>
  )
}

function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2.5', className)}>{children}</td>
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <label className="flex items-center gap-1.5 text-[12px] text-ink-muted">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12px] text-ink"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}
