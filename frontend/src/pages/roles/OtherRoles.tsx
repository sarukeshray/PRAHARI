/**
 * State Nodal Authority, Implementing Agency, User Agency, and the public view.
 *
 * Grouped in one file because each is a small number of screens over the same
 * primitives; keeping them together makes it obvious they are the same product.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'

import {
  useAcknowledgeHandover,
  useReassignFlag,
  useFlags,
  useLogCheckin,
  useMaintenanceList,
  useMyAssets,
  usePublicAggregates,
  useRaiseMaintenance,
  useStateDistricts,
} from '@/api/hooks'
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
import { PendingTag } from '@/components/Placeholder'
import { SyntheticDataBadge } from '@/components/SyntheticDataBadge'
import { CitizenForm } from '@/pages/CitizenForm'
import { rupeesShort, shortDate } from '@/lib/format'
import { MODULE_LABEL, flagTitle } from '@/lib/labels'
import { useSession } from '@/lib/session'

const SEAL = '#16457e'
const AMBER = '#a9670c'

/* ========================================================================== */
/* State Nodal Authority                                                       */
/* ========================================================================== */

export function StateOverview() {
  const { me } = useSession()
  const rows = useStateDistricts(me?.scope_state)

  if (rows.isPending) return <Loading rows={6} label="Loading state position" />
  if (rows.isError) return <ErrorState message={(rows.error as Error).message} onRetry={() => rows.refetch()} />

  const data = rows.data ?? []
  const totals = data.reduce(
    (acc, d) => ({
      works: acc.works + d.works,
      open: acc.open + d.open_findings,
      resolved: acc.resolved + d.resolved_findings,
    }),
    { works: 0, open: 0, resolved: 0 },
  )

  return (
    <div>
      <PageHeader
        eyebrow={me?.scope_state ?? ''}
        title="State overview"
        meta={`${data.length} districts screening under this authority`}
      />
      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule lg:grid-cols-4">
        <Stat label="Districts" value={String(data.length)} />
        <Stat label="Works" value={totals.works.toLocaleString('en-IN')} />
        <Stat label="Open findings" value={totals.open.toLocaleString('en-IN')} />
        <Stat
          label="Resolution rate"
          value={`${totals.open + totals.resolved ? ((totals.resolved / (totals.open + totals.resolved)) * 100).toFixed(0) : 0}%`}
          hint="Findings with a decision recorded"
        />
      </div>

      <Section
        title="Where the pressure is"
        note="Each bubble is a district: flag rate against how much of its caseload it has resolved, sized by the number of works. The district in the lower right is both high-risk and slow to decide — neither number identifies it on its own."
      >
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 4 }}>
              <CartesianGrid stroke="#eceeef" />
              <XAxis
                type="number"
                dataKey="flag_rate_pct"
                name="Flag rate"
                unit="%"
                tick={{ fontSize: 10, fill: '#8a939b' }}
                axisLine={{ stroke: '#dce0e2' }}
                tickLine={false}
                label={{
                  value: 'Open findings per 100 works',
                  position: 'insideBottom',
                  offset: -14,
                  style: { fontSize: 11, fill: '#5b656e' },
                }}
              />
              <YAxis
                type="number"
                dataKey="resolution_rate_pct"
                name="Resolved"
                unit="%"
                tick={{ fontSize: 10, fill: '#8a939b' }}
                axisLine={{ stroke: '#dce0e2' }}
                tickLine={false}
                label={{
                  value: 'Resolved %',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 11, fill: '#5b656e' },
                }}
              />
              <ZAxis type="number" dataKey="works" range={[60, 500]} name="Works" />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 3,
                  border: '1px solid #dce0e2',
                  boxShadow: 'none',
                }}
                content={({ payload }) => {
                  const p = payload?.[0]?.payload
                  if (!p) return null
                  return (
                    <div className="rounded-[3px] border border-rule bg-surface px-2.5 py-2 text-[11.5px]">
                      <div className="font-medium">{p.district_name}</div>
                      <div className="mt-1 text-ink-muted">
                        {p.works} works · {p.open_findings} open · {p.flag_rate_pct}% flag rate
                      </div>
                      <div className="text-ink-muted">{p.resolution_rate_pct}% resolved</div>
                    </div>
                  )
                }}
              />
              <Scatter data={data} fill={SEAL} fillOpacity={0.65} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Section>

      <Section title="District comparison">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb]">
                <Th>District</Th>
                <Th>Terrain</Th>
                <Th className="text-right">Works</Th>
                <Th className="text-right">Open</Th>
                <Th className="text-right">Resolved</Th>
                <Th className="text-right">Flag rate</Th>
              </tr>
            </thead>
            <tbody>
              {[...data]
                .sort((a, b) => b.flag_rate_pct - a.flag_rate_pct)
                .map((d) => (
                  <tr key={d.district_id} className="border-b border-rule">
                    <Td>{d.district_name}</Td>
                    <Td className="font-mono text-[11.5px] text-ink-muted">{d.terrain_category}</Td>
                    <Td className="text-right font-mono tabular-nums">{d.works}</Td>
                    <Td className="text-right font-mono tabular-nums">{d.open_findings}</Td>
                    <Td className="text-right font-mono tabular-nums">{d.resolved_findings}</Td>
                    <Td className="text-right font-mono tabular-nums">{d.flag_rate_pct}%</Td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  )
}

export function StateEscalations() {
  const flags = useFlags({ status: 'OPEN' })
  const urgent = (flags.data ?? []).filter(
    (f) => f.severity_tier === 'CRITICAL' || f.severity_tier === 'HIGH',
  )

  return (
    <div>
      <PageHeader
        eyebrow="Escalation queue"
        title="Findings awaiting a district decision"
        meta="Critical and high findings that no District Authority has yet acted on. Escalating does not change a finding's state — it moves whose queue it sits in."
      />
      {flags.isPending && <Loading rows={6} label="Loading escalations" />}
      {urgent.length === 0 && flags.data && (
        <EmptyState
          title="Nothing is waiting"
          body="Every critical and high finding in this state has had a decision recorded."
        />
      )}
      {urgent.length > 0 && (
        <ul className="divide-y divide-rule">
          {urgent.slice(0, 60).map((f) => (
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
              <ReassignControl flagId={f.flag_id} assignedTo={f.assigned_to_user_id} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/**
 * Move a finding to a named District Authority reviewer.
 *
 * Reassignment does not change the finding's state — it changes whose queue it
 * sits in. That distinction matters: a State officer can direct attention, but
 * only the reviewer holding the finding can decide it.
 */
function ReassignControl({
  flagId,
  assignedTo,
}: {
  flagId: number
  assignedTo: string | null
}) {
  const reassign = useReassignFlag()
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState('u-da-udaipur')
  const [note, setNote] = useState('')

  if (assignedTo && !open) {
    return (
      <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
        <span className="rounded-[2px] bg-seal-tint px-1.5 py-px font-mono text-[10.5px] text-seal">
          assigned to {assignedTo}
        </span>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="text-seal hover:underline"
        >
          Reassign again
        </button>
      </div>
    )
  }

  return (
    <div className="mt-2.5">
      {open ? (
        <div className="rounded-[3px] border border-rule bg-[#fafbfb] p-3">
          <div className="flex flex-wrap items-end gap-2">
            <label className="block">
              <span className="text-[11px] text-ink-muted">Reviewer</span>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="mt-1 rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12px]"
              >
                <option value="u-da-udaipur">S. Nair, IAS — Udaipur</option>
                <option value="u-da-udaipur-2">R. Deshmukh — Udaipur</option>
              </select>
            </label>
            <label className="block flex-1">
              <span className="text-[11px] text-ink-muted">Reason</span>
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional note for the audit trail"
                className="mt-1 w-full rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12px]"
              />
            </label>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px]"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={reassign.isPending}
              onClick={() =>
                reassign.mutate(
                  { flagId, assigned_to_user_id: target, note },
                  { onSuccess: () => setOpen(false) },
                )
              }
              className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-40"
            >
              {reassign.isPending ? 'Reassigning…' : 'Reassign'}
            </button>
          </div>
          {reassign.isError && (
            <p className="mt-2 text-[11.5px] text-[#ae1414]">
              {(reassign.error as Error).message}
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal"
          >
            Reassign reviewer
          </button>
          <span className="text-[11px] text-ink-faint">
            Reassigning moves whose queue this sits in. It does not change the finding.
          </span>
        </div>
      )}
    </div>
  )
}

/* ========================================================================== */
/* User Agency                                                                 */
/* ========================================================================== */

export function UserAgencyAssets() {
  const assets = useMyAssets()
  const acknowledge = useAcknowledgeHandover()
  const checkin = useLogCheckin()
  const maintain = useRaiseMaintenance()
  const [openForm, setOpenForm] = useState<{ workId: string; kind: 'checkin' | 'maintenance' } | null>(null)
  const [text, setText] = useState('')

  return (
    <div>
      <PageHeader
        eyebrow="Assets handed over to this agency"
        title="My assets"
        meta="What you have received, whether the handover is on record, and the condition history of each."
      />

      {assets.isPending && <Loading rows={5} label="Loading assets" />}
      {assets.isError && (
        <ErrorState message={(assets.error as Error).message} onRetry={() => assets.refetch()} />
      )}
      {assets.data?.length === 0 && (
        <EmptyState
          title="No assets handed over yet"
          body="When a completed work is transferred to this agency it appears here, and acknowledging it is what puts a name against its upkeep."
        />
      )}

      {assets.data && assets.data.length > 0 && (
        <ul className="divide-y divide-rule">
          {assets.data.map((a) => {
            const acknowledged = Boolean(a.handover?.handover_acknowledged_date)
            return (
              <li key={a.work_id} className="bg-surface px-5 py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <span className="font-mono text-[12.5px] font-medium">{a.work_id}</span>
                    <span className="ml-2 font-mono text-[11px] text-ink-faint">{a.work_type}</span>
                  </div>
                  <span
                    className="rounded-[2px] px-2 py-0.5 text-[10.5px] font-medium tracking-wide uppercase"
                    style={
                      acknowledged
                        ? { color: SEAL, boxShadow: `inset 0 0 0 1px ${SEAL}` }
                        : { color: AMBER, boxShadow: `inset 0 0 0 1px ${AMBER}` }
                    }
                  >
                    {acknowledged ? 'Acknowledged' : 'Awaiting acknowledgement'}
                  </span>
                </div>
                <p className="mt-1 text-[12.5px] leading-snug">{a.description}</p>

                {/* Lifecycle timeline: built, handed over, checked, maintained. */}
                <ol className="mt-3 flex flex-wrap gap-x-6 gap-y-2 border-l-2 border-rule pl-3 text-[11.5px]">
                  <TimelineItem label="Completed" value={a.completed_on ? shortDate(a.completed_on) : '—'} />
                  <TimelineItem
                    label="Handover initiated"
                    value={a.handover ? shortDate(a.handover.handover_initiated_date) : 'Not initiated'}
                  />
                  <TimelineItem
                    label="Acknowledged"
                    value={
                      a.handover?.handover_acknowledged_date
                        ? shortDate(a.handover.handover_acknowledged_date)
                        : 'Not yet'
                    }
                  />
                  <TimelineItem label="Check-ins" value={String(a.checkins.length)} />
                  <TimelineItem label="Maintenance raised" value={String(a.maintenance.length)} />
                </ol>

                <div className="mt-3 flex flex-wrap gap-2">
                  {!acknowledged && a.handover && (
                    <button
                      type="button"
                      onClick={() => acknowledge.mutate(a.work_id)}
                      disabled={acknowledge.isPending}
                      className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-50"
                    >
                      Acknowledge receipt
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setOpenForm({ workId: a.work_id, kind: 'checkin' })
                      setText('')
                    }}
                    className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal"
                  >
                    Log a check-in
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setOpenForm({ workId: a.work_id, kind: 'maintenance' })
                      setText('')
                    }}
                    className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal"
                  >
                    Raise a maintenance need
                  </button>
                </div>

                {openForm?.workId === a.work_id && (
                  <div className="mt-3 rounded-[3px] border border-rule bg-[#fafbfb] p-3">
                    <div className="text-[11.5px] font-medium">
                      {openForm.kind === 'checkin' ? 'Check-in note' : 'What needs attention?'}
                    </div>
                    {openForm.kind === 'maintenance' && (
                      <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">
                        This raises a maintenance need for the responsible department's own budget.
                        MPLADS cannot fund maintenance directly.
                      </p>
                    )}
                    <textarea
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      rows={2}
                      className="mt-2 w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] focus:border-seal"
                    />
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5 text-[11px] text-ink-faint">
                        Attach a photograph <PendingTag label="Firebase" />
                      </span>
                    </div>
                    <div className="mt-2 flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setOpenForm(null)}
                        className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px]"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={openForm.kind === 'maintenance' && text.trim().length < 15}
                        onClick={() => {
                          if (openForm.kind === 'checkin') {
                            checkin.mutate(
                              { workId: a.work_id, still_in_use: true, notes: text },
                              { onSuccess: () => setOpenForm(null) },
                            )
                          } else {
                            maintain.mutate(
                              { workId: a.work_id, description: text },
                              { onSuccess: () => setOpenForm(null) },
                            )
                          }
                        }}
                        className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-40"
                      >
                        Record
                      </button>
                    </div>
                  </div>
                )}

                {a.maintenance.length > 0 && (
                  <ul className="mt-3 space-y-1.5 border-t border-rule pt-2">
                    {a.maintenance.map((m) => (
                      <li key={m.recommendation_id} className="text-[11.5px] text-ink-muted">
                        <span className="font-mono text-[10.5px] text-ink-faint">
                          {shortDate(m.raised_date)}
                        </span>{' '}
                        {m.description}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function TimelineItem({ label, value }: { label: string; value: string }) {
  return (
    <li>
      <div className="eyebrow">{label}</div>
      <div className="mt-0.5 font-mono text-[11.5px]">{value}</div>
    </li>
  )
}

export function UserAgencyMaintenance() {
  const list = useMaintenanceList()
  return (
    <div>
      <PageHeader
        eyebrow="Raised by this agency"
        title="Maintenance"
        meta="MPLADS cannot fund maintenance. These records put the need in front of the department whose budget covers upkeep, and keep the asset's condition visible over its life."
      />
      {list.isPending && <Loading rows={4} label="Loading" />}
      {list.data?.length === 0 && (
        <EmptyState
          title="Nothing raised"
          body="Maintenance needs you record against your assets will be listed here."
        />
      )}
      {list.data && list.data.length > 0 && (
        <ul className="divide-y divide-rule">
          {list.data.map((m) => (
            <li key={m.recommendation_id} className="bg-surface px-5 py-3.5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-mono text-[12px] font-medium">{m.work_id}</span>
                <span className="font-mono text-[11px] text-ink-faint">
                  {shortDate(m.raised_date)} · {m.status.replace(/_/g, ' ').toLowerCase()}
                </span>
              </div>
              <p className="mt-1 text-[12.5px] leading-snug">{m.description}</p>
              {m.da_response && (
                <p className="mt-1 border-l-2 border-rule-strong pl-3 text-[12px] text-ink-muted">
                  District Authority: {m.da_response}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ========================================================================== */
/* Public                                                                      */
/* ========================================================================== */

export function PublicView() {
  const agg = usePublicAggregates()
  const { isSignedIn, signOut } = useSession()
  const navigate = useNavigate()

  const totals = (agg.data ?? []).reduce(
    (a, s) => ({
      works: a.works + s.works_total,
      completed: a.completed + s.works_completed,
      sanctioned: a.sanctioned + s.sanctioned_amount,
      disbursed: a.disbursed + s.disbursed_amount,
    }),
    { works: 0, completed: 0, sanctioned: 0, disbursed: 0 },
  )

  return (
    <div className="min-h-screen bg-paper">
      <SyntheticDataBadge />

      {/* The public view has no left rail, so it carries its own way out. */}
      <header className="flex flex-wrap items-center gap-3 border-b border-rule bg-surface px-4 py-2">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-[2px] bg-seal">
            <span className="font-deva text-[13px] leading-none font-semibold text-white">प्र</span>
          </span>
          <span className="text-[13px] font-semibold tracking-[0.1em]">PRAHARI</span>
        </Link>
        <span aria-hidden className="h-4 w-px bg-rule" />
        <span className="text-[12px] text-ink-muted">Public</span>

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/"
            className="rounded-[2px] border border-rule-strong px-2.5 py-1 text-[11.5px] text-ink-muted hover:border-seal hover:text-seal"
          >
            Home
          </Link>
          {isSignedIn ? (
            <button
              type="button"
              onClick={() => {
                signOut()
                navigate('/', { replace: true })
              }}
              className="rounded-[2px] border border-rule-strong px-2.5 py-1 text-[11.5px] text-ink-muted hover:border-seal hover:text-seal"
            >
              Sign out
            </button>
          ) : (
            <Link
              to="/signin"
              className="rounded-[2px] bg-seal px-3 py-1 text-[11.5px] font-medium text-white"
            >
              Sign in
            </Link>
          )}
        </div>
      </header>

      <PageHeader
        eyebrow="Public view · no sign-in required"
        title="MPLADS at a glance"
        meta="Aggregate utilisation and completion by state."
      />

      <div className="border-b border-rule bg-notice px-5 py-3">
        <p className="max-w-3xl text-[12px] leading-relaxed text-notice-ink">
          This view shows totals only. Individual works, agencies, Members and any risk finding are
          deliberately absent — not omitted for space. What a citizen may see is how much was
          committed and how much was finished.
        </p>
      </div>

      {agg.isPending && <Loading rows={5} label="Loading" />}
      {agg.isError && <ErrorState message={(agg.error as Error).message} onRetry={() => agg.refetch()} />}

      {agg.data && (
        <>
          <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule lg:grid-cols-4">
            <Stat label="Works" value={totals.works.toLocaleString('en-IN')} />
            <Stat
              label="Completed"
              value={`${totals.works ? ((totals.completed / totals.works) * 100).toFixed(0) : 0}%`}
              hint={`${totals.completed.toLocaleString('en-IN')} works`}
            />
            <Stat label="Sanctioned" value={rupeesShort(totals.sanctioned)} />
            <Stat
              label="Utilisation"
              value={`${totals.sanctioned ? ((totals.disbursed / totals.sanctioned) * 100).toFixed(0) : 0}%`}
              hint={`${rupeesShort(totals.disbursed)} released`}
            />
          </div>

          <Section title="By state">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] border-collapse text-[12.5px]">
                <thead>
                  <tr className="border-b border-rule bg-[#fafbfb]">
                    <Th>State</Th>
                    <Th className="text-right">Works</Th>
                    <Th className="text-right">Completed</Th>
                    <Th className="text-right">Sanctioned</Th>
                    <Th className="text-right">Utilisation</Th>
                  </tr>
                </thead>
                <tbody>
                  {agg.data.map((s) => (
                    <tr key={s.state} className="border-b border-rule">
                      <Td>{s.state}</Td>
                      <Td className="text-right font-mono tabular-nums">
                        {s.works_total.toLocaleString('en-IN')}
                      </Td>
                      <Td className="text-right font-mono tabular-nums">
                        {s.completion_rate_pct.toFixed(0)}%
                      </Td>
                      <Td className="text-right font-mono tabular-nums">
                        {rupeesShort(s.sanctioned_amount)}
                      </Td>
                      <Td className="text-right font-mono tabular-nums">
                        {s.utilisation_pct.toFixed(0)}%
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </>
      )}

      <CitizenForm />
    </div>
  )
}
