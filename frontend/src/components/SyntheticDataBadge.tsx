/**
 * Mandatory data-provenance notice.
 *
 * Every screen that shows data carries this, and it has no dismiss control by
 * design — a reader arriving mid-demo must never be able to mistake these
 * records for live MPLADS data.
 */
export function SyntheticDataBadge() {
  return (
    <div
      role="note"
      className="flex items-center gap-2 border-b border-notice-rule bg-notice px-4 py-1 text-[11px] font-medium text-notice-ink"
    >
      <span aria-hidden className="inline-block size-1.5 rounded-full bg-[#c79a1e]" />
      Synthetic demonstration data — not live MPLADS records
    </div>
  )
}
