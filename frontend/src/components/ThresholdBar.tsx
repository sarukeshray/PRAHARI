import { SEVERITY_STYLE, type Severity } from '@/lib/severity'
import { cn } from '@/lib/utils'

interface ThresholdBarProps {
  observed: number
  observedLabel: string
  observedCaption: string
  threshold: number
  thresholdLabel: string
  thresholdCaption: string
  axisMax: number
  severity: Severity
}

/**
 * The evidence row — the one visual device the whole interface is built around.
 *
 * It draws the observed value against the threshold it crossed, to scale, so a
 * reviewer can see the size of the deviation rather than being handed a score.
 * This is the fourth design rule ("every flag must carry a checkable number")
 * expressed as a component, and it is why the composite score never has to be
 * the headline anywhere in the product.
 */
export function ThresholdBar({
  observed,
  observedLabel,
  observedCaption,
  threshold,
  thresholdLabel,
  thresholdCaption,
  axisMax,
  severity,
}: ThresholdBarProps) {
  const style = SEVERITY_STYLE[severity]

  const clamp = (n: number) => Math.max(0, Math.min(100, n))
  const observedPct = clamp((Math.abs(observed) / axisMax) * 100)
  const thresholdPct = clamp((Math.abs(threshold) / axisMax) * 100)

  // Keep the threshold caption inside the track when the tick sits near an edge.
  const captionAlignsRight = thresholdPct > 62

  return (
    <div
      role="img"
      aria-label={`${observedLabel} ${observedCaption}. Threshold ${thresholdLabel}, ${thresholdCaption}.`}
      className="select-none"
    >
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-[11px] text-ink-muted">{observedCaption}</span>
        <span className={cn('font-mono text-[15px] font-medium tabular-nums', style.fg)}>
          {observedLabel}
        </span>
      </div>

      <div className="relative mt-1.5 h-2 rounded-[1px] bg-[#eceeef]">
        <div
          className="absolute inset-y-0 left-0 rounded-[1px]"
          style={{ width: `${observedPct}%`, backgroundColor: style.hex }}
        />
        {/* The threshold tick. Drawn over the fill so the overshoot is legible. */}
        <div
          className="absolute -top-1 -bottom-1 w-px bg-ink"
          style={{ left: `${thresholdPct}%` }}
          aria-hidden
        />
      </div>

      <div
        className={cn(
          'relative mt-1 flex items-baseline gap-1.5 text-[11px] text-ink-muted',
          captionAlignsRight && 'justify-end',
        )}
      >
        <span className="font-mono tabular-nums text-ink">{thresholdLabel}</span>
        <span>{thresholdCaption}</span>
      </div>
    </div>
  )
}
