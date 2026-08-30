import { SEVERITY_STYLE, type Severity } from '@/lib/severity'
import { cn } from '@/lib/utils'

/**
 * Tier is never signalled by hue alone: the two urgent tiers take a solid fill
 * and the two advisory tiers an outline, and the tier is always spelled out.
 * Amber, orange and red sit close enough together that colour on its own would
 * fail for a reviewer with a colour vision deficiency, or on a projector.
 */
export function SeverityChip({
  severity,
  size = 'default',
}: {
  severity: Severity
  size?: 'default' | 'sm'
}) {
  const style = SEVERITY_STYLE[severity]

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-[2px] font-medium uppercase tracking-[0.06em] whitespace-nowrap',
        size === 'sm' ? 'px-1.5 py-px text-[9.5px]' : 'px-2 py-0.5 text-[10.5px]',
      )}
      style={
        style.solid
          ? { backgroundColor: style.hex, color: '#fff' }
          : { color: style.hex, boxShadow: `inset 0 0 0 1px ${style.hex}` }
      }
    >
      {severity}
    </span>
  )
}
