/**
 * Consistent treatment for UI that is designed but not yet wired.
 *
 * The point is to look deliberate rather than unfinished, while never letting a
 * reader mistake scaffolding for a working control. Two rules hold everywhere
 * this is used:
 *
 *   1. A placeholder never displays invented data. It shows the shape of a
 *      screen, not made-up findings, scores or amounts — fabricating those would
 *      undermine the one thing this product is asking to be trusted on.
 *   2. It always says what it is waiting for, so the gap is a roadmap item
 *      rather than a mystery.
 */

import { cn } from '@/lib/utils'

export function PendingTag({ label = 'Next build' }: { label?: string }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded-[2px] border border-dashed border-rule-strong px-1.5 py-px text-[10px] font-medium tracking-[0.06em] text-ink-faint uppercase">
      {label}
    </span>
  )
}

export function PlaceholderPanel({
  title,
  body,
  waitingOn,
  children,
  className,
}: {
  title: string
  body: string
  waitingOn?: string
  children?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'rounded-[3px] border border-dashed border-rule-strong bg-[#fbfcfc] p-5',
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-[13px] font-medium">{title}</h3>
        <PendingTag />
      </div>
      <p className="mt-1.5 max-w-xl text-[12px] leading-relaxed text-ink-muted">{body}</p>
      {waitingOn && (
        <p className="mt-2 font-mono text-[11px] text-ink-faint">Waiting on: {waitingOn}</p>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  )
}

/** A control that is present and styled but does nothing yet. */
export function PendingButton({
  children,
  title,
}: {
  children: React.ReactNode
  title: string
}) {
  return (
    <button
      type="button"
      disabled
      title={title}
      className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-[2px] border border-dashed border-rule-strong px-3 py-1 text-[12px] text-ink-faint"
    >
      {children}
      <PendingTag />
    </button>
  )
}
