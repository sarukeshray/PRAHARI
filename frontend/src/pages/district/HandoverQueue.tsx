import { useHandoverQueue, useMaintenanceList } from '@/api/hooks'
import { EmptyState, ErrorState, Loading, PageHeader, Section, Td, Th, WorkLink } from '@/components/ui-kit'
import { shortDate } from '@/lib/format'

/**
 * Stage 3's queue: finished works nobody has taken responsibility for.
 *
 * The gap CAG documented is not that assets go missing — it is that the handover
 * is never written down, so no department owns the upkeep. A work can be built,
 * paid for and closed correctly and still land here.
 */
export function HandoverQueue() {
  const queue = useHandoverQueue()
  const maintenance = useMaintenanceList()

  return (
    <div>
      <PageHeader
        eyebrow="Stage 3 · handover and lifecycle"
        title="Handover queue"
        meta={
          queue.data
            ? `${queue.data.length} completed works without an acknowledged handover`
            : 'Loading…'
        }
      />

      <Section
        title="Completed, but not handed over on record"
        note="A work appears here 30 days after completion if no handover has been initiated, or if one was initiated and the receiving agency has not acknowledged it. Findings raised here use the same three review actions as every other stage — there is no separate workflow."
      >
        {queue.isPending && <Loading rows={5} label="Loading handover queue" />}
        {queue.isError && (
          <ErrorState message={(queue.error as Error).message} onRetry={() => queue.refetch()} />
        )}

        {queue.data && queue.data.length === 0 && (
          <EmptyState
            title="Every completed work has been handed over"
            body="No asset in this district is sitting without a recorded owner. This is the state the Stage 3 module exists to keep."
          />
        )}

        {queue.data && queue.data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-[12.5px]">
              <thead>
                <tr className="border-b border-rule bg-[#fafbfb]">
                  <Th className="w-[150px]">Work ID</Th>
                  <Th className="w-[140px]">Type</Th>
                  <Th className="w-[100px]">Block</Th>
                  <Th className="w-[110px]">Completed</Th>
                  <Th className="w-[86px] text-right">Days</Th>
                  <Th>Handover state</Th>
                  <Th className="w-[130px]">Paperwork</Th>
                </tr>
              </thead>
              <tbody>
                {queue.data.map((r) => (
                  <tr key={r.work_id} className="border-b border-rule">
                    <Td>
                      <WorkLink workId={r.work_id} to={`/district/works/${r.work_id}`} />
                    </Td>
                    <Td className="font-mono text-[11.5px]">{r.work_type}</Td>
                    <Td className="text-ink-muted">{r.block}</Td>
                    <Td className="text-ink-muted">{shortDate(r.completed_on)}</Td>
                    <Td className="text-right font-mono tabular-nums">
                      {r.days_since_completion}
                    </Td>
                    <Td>{r.handover_state}</Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        <Tag ok={r.uc_on_file} label="UC" />
                        <Tag ok={r.register_entry} label="Register" />
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section
        title="Maintenance raised by receiving agencies"
        note="MPLADS cannot fund maintenance. These records exist so the need reaches the department whose budget covers upkeep, and so an asset's condition stays visible over its life."
      >
        {maintenance.isPending && <Loading rows={3} label="Loading maintenance records" />}
        {maintenance.data && maintenance.data.length === 0 && (
          <p className="text-[12px] text-ink-muted">
            No maintenance needs have been raised against assets in this district.
          </p>
        )}
        {maintenance.data && maintenance.data.length > 0 && (
          <ul className="divide-y divide-rule rounded-[3px] border border-rule">
            {maintenance.data.slice(0, 12).map((m) => (
              <li key={m.recommendation_id} className="px-4 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <WorkLink workId={m.work_id} to={`/district/works/${m.work_id}`} />
                  <span className="font-mono text-[11px] text-ink-faint">
                    raised {shortDate(m.raised_date)} · {m.status.replace(/_/g, ' ').toLowerCase()}
                  </span>
                </div>
                <p className="mt-1 text-[12.5px] leading-snug">{m.description}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}

function Tag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className="rounded-[2px] px-1.5 py-px text-[10px] font-medium tracking-wide uppercase"
      style={
        ok
          ? { color: '#16457e', boxShadow: 'inset 0 0 0 1px #16457e' }
          : { color: '#a9670c', boxShadow: 'inset 0 0 0 1px #a9670c' }
      }
    >
      {ok ? label : `No ${label}`}
    </span>
  )
}
