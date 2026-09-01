/**
 * Shared primitives every screen is built from.
 *
 * Kept in one file so a District Authority screen and a User Agency screen are
 * unmistakably the same product — the spacing, the rules and the empty states
 * come from here rather than being re-invented per role.
 */

import { Link } from 'react-router-dom'

import type { Severity } from '@/api/types'
import { cn } from '@/lib/utils'

/* -------------------------------------------------------------------------- */
/* Severity                                                                    */
/* -------------------------------------------------------------------------- */

export const SEVERITY_HEX: Record<Severity, string> = {
  LOW: '#64748b',
  MEDIUM: '#a9670c',
  HIGH: '#c4460b',
  CRITICAL: '#ae1414',
}

export const SEVERITY_ORDER: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

const SOLID: Record<Severity, boolean> = {
  LOW: false,
  MEDIUM: false,
  HIGH: true,
  CRITICAL: true,
}

/**
 * Tier is never carried by colour alone. Amber, orange and red sit close enough
 * together that a reader with deuteranopia cannot separate them, so the chip
 * spells the tier out and the two urgent tiers take a solid fill.
 */
export function SeverityChip({
  severity,
  size = 'default',
}: {
  severity: Severity | null | undefined
  size?: 'default' | 'sm'
}) {
  if (!severity) {
    return (
      <span className="inline-flex rounded-[2px] px-1.5 py-px text-[10px] tracking-wide text-ink-faint uppercase">
        Not screened
      </span>
    )
  }
  const hex = SEVERITY_HEX[severity]
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-[2px] font-medium tracking-[0.06em] whitespace-nowrap uppercase',
        size === 'sm' ? 'px-1.5 py-px text-[9.5px]' : 'px-2 py-0.5 text-[10.5px]',
      )}
      style={
        SOLID[severity]
          ? { backgroundColor: hex, color: '#fff' }
          : { color: hex, boxShadow: `inset 0 0 0 1px ${hex}` }
      }
    >
      {severity}
    </span>
  )
}

/* -------------------------------------------------------------------------- */
/* The evidence row                                                            */
/* -------------------------------------------------------------------------- */

/**
 * The one device the whole interface is built around: the observed value drawn
 * against the threshold it crossed, to scale.
 *
 * This is design rule four expressed as a component — every finding shows the
 * number that triggered it and the line it crossed — and it is why the composite
 * score never has to be the headline anywhere a person reads.
 */
export function ThresholdBar({
  observed,
  threshold,
  severity,
  observedLabel,
  thresholdLabel,
}: {
  observed: number
  threshold: number
  severity: Severity
  observedLabel: string
  thresholdLabel: string
}) {
  const hex = SEVERITY_HEX[severity]
  const axisMax = Math.max(Math.abs(observed), Math.abs(threshold)) * 1.25 || 1
  const clamp = (n: number) => Math.max(0, Math.min(100, n))
  const observedPct = clamp((Math.abs(observed) / axisMax) * 100)
  const thresholdPct = clamp((Math.abs(threshold) / axisMax) * 100)

  return (
    <div className="max-w-md select-none" role="img" aria-label={`${observedLabel} against ${thresholdLabel}`}>
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-[11px] text-ink-muted">observed</span>
        <span className="font-mono text-[15px] font-medium tabular-nums" style={{ color: hex }}>
          {observedLabel}
        </span>
      </div>
      <div className="relative mt-1.5 h-2 rounded-[1px] bg-[#eceeef]">
        <div
          className="absolute inset-y-0 left-0 rounded-[1px]"
          style={{ width: `${observedPct}%`, backgroundColor: hex }}
        />
        <div
          aria-hidden
          className="absolute -top-1 -bottom-1 w-px bg-ink"
          style={{ left: `${thresholdPct}%` }}
        />
      </div>
      <div
        className={cn(
          'mt-1 flex items-baseline gap-1.5 text-[11px] text-ink-muted',
          thresholdPct > 62 && 'justify-end',
        )}
      >
        <span className="font-mono text-ink tabular-nums">{thresholdLabel}</span>
        <span>threshold</span>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Layout                                                                      */
/* -------------------------------------------------------------------------- */

export function PageHeader({
  eyebrow,
  title,
  meta,
  actions,
}: {
  eyebrow?: React.ReactNode
  title: string
  meta?: React.ReactNode
  actions?: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-rule bg-surface px-5 py-3.5">
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="mt-0.5 text-[19px] leading-tight font-semibold tracking-[-0.01em]">
          {title}
        </h1>
        {meta && <div className="mt-1 text-[12px] text-ink-muted">{meta}</div>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Section({
  title,
  note,
  actions,
  children,
}: {
  title: string
  note?: string
  actions?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section className="border-b border-rule bg-surface px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[13.5px] font-semibold">{title}</h2>
          {note && <p className="mt-1 max-w-3xl text-[11.5px] leading-relaxed text-ink-muted">{note}</p>}
        </div>
        {actions}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  )
}

export function Stat({
  label,
  value,
  hint,
  accent,
}: {
  label: string
  value: string
  hint?: string
  accent?: string
}) {
  return (
    <div className="bg-surface px-4 py-3">
      <div className="eyebrow">{label}</div>
      <div
        className="mt-1 font-mono text-[20px] leading-none font-medium tabular-nums"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-[11px] leading-snug text-ink-muted">{hint}</div>}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* States                                                                      */
/* -------------------------------------------------------------------------- */

/** Skeleton rows, so an async screen never flashes blank. */
export function Loading({ rows = 5, label = 'Loading' }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-2 p-5" role="status" aria-label={label}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-9 animate-pulse rounded-[2px] bg-[#eef0f1]"
          style={{ animationDelay: `${i * 60}ms`, opacity: 1 - i * 0.12 }}
        />
      ))}
    </div>
  )
}

/** An empty screen is an instruction, not a blank. */
export function EmptyState({
  title,
  body,
  action,
}: {
  title: string
  body: string
  action?: React.ReactNode
}) {
  return (
    <div className="px-5 py-14 text-center">
      <div
        aria-hidden
        className="mx-auto mb-3 h-px w-10 bg-rule-strong"
        style={{ boxShadow: '0 4px 0 0 var(--rule), 0 8px 0 0 var(--rule)' }}
      />
      <p className="text-[13px] font-medium">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-[12px] leading-relaxed text-ink-muted">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="px-5 py-12 text-center">
      <p className="text-[13px] font-medium">Could not load this</p>
      <p className="mx-auto mt-1 max-w-md text-[12px] text-ink-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal"
        >
          Try again
        </button>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Table                                                                       */
/* -------------------------------------------------------------------------- */

export function Th({
  children,
  className,
}: {
  children?: React.ReactNode
  className?: string
}) {
  return (
    <th
      className={cn(
        'px-3 py-2 text-left text-[10.5px] font-semibold tracking-[0.08em] text-ink-faint uppercase',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function Td({
  children,
  className,
  colSpan,
}: {
  children: React.ReactNode
  className?: string
  colSpan?: number
}) {
  return (
    <td colSpan={colSpan} className={cn('px-3 py-2.5 align-top', className)}>
      {children}
    </td>
  )
}

export function WorkLink({ workId, to }: { workId: string; to: string }) {
  return (
    <Link to={to} className="font-mono text-[12px] text-seal hover:underline">
      {workId}
    </Link>
  )
}

/* -------------------------------------------------------------------------- */
/* Bars                                                                        */
/* -------------------------------------------------------------------------- */

const SEAL = '#16457e'

/** A single-hue horizontal bar. Used wherever one series is being compared. */
export function Bar({
  value,
  max,
  color = SEAL,
  title,
}: {
  value: number
  max: number
  color?: string
  title?: string
}) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0
  return (
    <div className="h-3.5 rounded-[1px] bg-[#eceeef]" title={title}>
      <div className="h-full rounded-[1px]" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  )
}
