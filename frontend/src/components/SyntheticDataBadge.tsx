/**
 * Mandatory data-provenance notice (§7 of the specification).
 *
 * Every screen that displays data must carry this badge, and it must not be
 * dismissible.  It deliberately has no close control.
 */
export function SyntheticDataBadge() {
  return (
    <div
      role="note"
      className="flex items-center gap-2 border-b border-amber-300 bg-amber-50 px-4 py-1.5 text-xs font-medium text-amber-900"
    >
      <span aria-hidden className="inline-block size-1.5 rounded-full bg-amber-500" />
      Synthetic demonstration data — not live MPLADS records
    </div>
  )
}
