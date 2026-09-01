import { useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts'
import { Link } from 'react-router-dom'

import { useAgencyRefs, useDistrictRefs, useMPSummary, useRecommendWork, useWorks } from '@/api/hooks'
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
import { rupees, rupeesShort, shortDate } from '@/lib/format'
import { useSession } from '@/lib/session'

const SEAL = '#16457e'
const AMBER = '#a9670c'

/* -------------------------------------------------------------------------- */
/* Entitlement                                                                 */
/* -------------------------------------------------------------------------- */

export function MPEntitlement() {
  const { data, isPending, isError, error, refetch } = useMPSummary()

  if (isPending) return <Loading rows={6} label="Loading entitlement" />
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
  if (!data) return null

  const used = Math.min(100, data.utilisation_pct)

  return (
    <div>
      <PageHeader
        eyebrow={`${data.constituency} · ${data.house.replace('_', ' ')} · FY ${data.financial_year}`}
        title="My entitlement"
        meta="Where your annual entitlement stands and how the mandated area allocation is tracking."
      />

      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule lg:grid-cols-4">
        <Stat label="Entitlement" value={rupeesShort(data.entitlement)} hint="Annual, per Member" />
        <Stat label="Recommended" value={rupeesShort(data.recommended)} hint={`${data.works_recommended} works this year`} />
        <Stat label="Sanctioned" value={rupeesShort(data.sanctioned)} />
        <Stat label="Disbursed" value={rupeesShort(data.disbursed)} />
      </div>

      <Section
        title="Utilisation against the annual cap"
        note="Under-utilisation is the Scheme's most consistently documented problem, and unlike anything else on this page it can be measured without inferring anything about intent."
      >
        <div className="grid gap-8 lg:grid-cols-[minmax(0,240px)_minmax(0,1fr)]">
          <div className="relative h-44">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={[
                    { name: 'Recommended', value: used },
                    { name: 'Unused', value: 100 - used },
                  ]}
                  dataKey="value"
                  startAngle={210}
                  endAngle={-30}
                  innerRadius="66%"
                  outerRadius="92%"
                  stroke="none"
                >
                  <Cell fill={SEAL} />
                  <Cell fill="#eceeef" />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pt-3">
              <span className="font-mono text-[26px] leading-none font-medium tabular-nums">
                {data.utilisation_pct.toFixed(0)}%
              </span>
              <span className="mt-1 text-[11px] text-ink-muted">of entitlement</span>
            </div>
          </div>

          <div className="self-center space-y-3">
            <div className="flex items-baseline justify-between border-b border-rule pb-2">
              <span className="text-[12.5px] text-ink-muted">Recommended so far</span>
              <span className="font-mono text-[13px] tabular-nums">{rupees(data.recommended)}</span>
            </div>
            <div className="flex items-baseline justify-between border-b border-rule pb-2">
              <span className="text-[12.5px] text-ink-muted">Still available</span>
              <span className="font-mono text-[13px] tabular-nums">
                {rupees(Math.max(0, data.entitlement - data.recommended))}
              </span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-[12.5px] text-ink-muted">Works completed</span>
              <span className="font-mono text-[13px] tabular-nums">
                {data.works_completed} of {data.works_total_all_years} all years
              </span>
            </div>
          </div>
        </div>
      </Section>

      <Section
        title="Mandated area allocation"
        note="MPLADS requires 15% of allocation in SC areas and 7.5% in ST areas. The position is tracked at district-year level; a shortfall at year end is raised there, not against any single work."
      >
        <QuotaRing
          label="SC and ST areas combined"
          actual={data.sc_st_allocation_pct}
          required={data.sc_st_required_pct}
        />
      </Section>
    </div>
  )
}

function QuotaRing({
  label,
  actual,
  required,
}: {
  label: string
  actual: number
  required: number
}) {
  const met = actual >= required
  const colour = met ? SEAL : AMBER
  return (
    <div className="flex flex-wrap items-center gap-8">
      <div className="relative h-36 w-36">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={[
                { value: Math.min(actual, 100) },
                { value: Math.max(0, 100 - actual) },
              ]}
              dataKey="value"
              innerRadius="70%"
              outerRadius="94%"
              startAngle={90}
              endAngle={-270}
              stroke="none"
            >
              <Cell fill={colour} />
              <Cell fill="#eceeef" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-[20px] leading-none font-medium tabular-nums">
            {actual.toFixed(1)}%
          </span>
        </div>
      </div>
      <div>
        <div className="text-[13px] font-medium">{label}</div>
        <div className="mt-1 text-[12px] text-ink-muted">
          Mandated minimum {required.toFixed(1)}%
        </div>
        <div
          className="mt-2 inline-flex rounded-[2px] px-2 py-0.5 text-[11px] font-medium"
          style={
            met
              ? { color: SEAL, boxShadow: `inset 0 0 0 1px ${SEAL}` }
              : { color: AMBER, boxShadow: `inset 0 0 0 1px ${AMBER}` }
          }
        >
          {met ? 'Above the requirement' : 'Below the requirement'}
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* My works                                                                    */
/* -------------------------------------------------------------------------- */

export function MPWorks() {
  const works = useWorks({ limit: 200 })

  return (
    <div>
      <PageHeader
        eyebrow="My recommendations"
        title="My works"
        meta="Every work you have recommended, with anything raised against it. A finding is a request for the District Authority to look more closely — it is not a determination about you, and nothing is blocked while it is open."
      />

      {works.isPending && <Loading rows={8} label="Loading works" />}
      {works.isError && (
        <ErrorState message={(works.error as Error).message} onRetry={() => works.refetch()} />
      )}
      {works.data?.length === 0 && (
        <EmptyState
          title="No works recommended yet"
          body="Recommendations you submit will appear here with their screening result."
          action={
            <Link
              to="/mp/recommend"
              className="inline-block rounded-[2px] bg-seal px-3 py-1.5 text-[12.5px] font-medium text-white"
            >
              Recommend a work
            </Link>
          }
        />
      )}

      {works.data && works.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb]">
                <Th className="w-[150px]">Work ID</Th>
                <Th className="w-[140px]">Type</Th>
                <Th className="w-[100px]">Block</Th>
                <Th className="w-[110px] text-right">Estimate</Th>
                <Th className="w-[110px]">Status</Th>
                <Th className="w-[96px]">Severity</Th>
                <Th>Finding</Th>
              </tr>
            </thead>
            <tbody>
              {works.data.map((w) => (
                <tr key={w.work_id} className="border-b border-rule">
                  <Td>
                    <span className="font-mono text-[12px]">{w.work_id}</span>
                    <div className="mt-0.5 text-[11px] text-ink-faint">
                      {w.recommended_date ? shortDate(w.recommended_date) : '—'}
                    </div>
                  </Td>
                  <Td className="font-mono text-[11.5px]">{w.work_type}</Td>
                  <Td className="text-ink-muted">{w.block}</Td>
                  <Td className="text-right font-mono tabular-nums">
                    {rupeesShort(w.estimated_cost)}
                  </Td>
                  <Td className="text-ink-muted">{w.status.replace('_', ' ').toLowerCase()}</Td>
                  <Td>
                    <SeverityChip severity={w.severity_tier} size="sm" />
                  </Td>
                  <Td>
                    {w.primary_finding ? (
                      <span className="line-clamp-2 text-[11.5px] leading-snug">
                        {w.primary_finding}
                      </span>
                    ) : (
                      <span className="text-[11.5px] text-ink-faint">Nothing raised</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Recommend                                                                   */
/* -------------------------------------------------------------------------- */

const WORK_TYPES = [
  'ROAD_CC', 'ROAD_BT', 'COMMUNITY_HALL', 'SCHOOL_BUILDING', 'WATER_TANK', 'BOREWELL',
  'STREET_LIGHTING', 'DRAINAGE', 'TOILET_BLOCK', 'LIBRARY', 'BUS_SHELTER', 'CREMATORIUM_SHED',
]

export function MPRecommend() {
  const { me } = useSession()
  const districts = useDistrictRefs()
  const create = useRecommendWork()

  const mine = districts.data?.filter((d) => d.state === me?.scope_state) ?? []
  const [districtId, setDistrictId] = useState('')
  const agencies = useAgencyRefs(districtId || undefined)

  const [form, setForm] = useState({
    block: '',
    work_type: 'ROAD_CC',
    description: '',
    estimated_cost: '',
    agency_id: '',
    is_sc_st_area: false,
  })

  const district = mine.find((d) => d.district_id === districtId)
  const ready =
    districtId && form.block && form.description.length >= 20 && Number(form.estimated_cost) > 0

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!ready || !district) return
    create.mutate({
      district_id: districtId,
      block: form.block,
      panchayat: form.block,
      work_type: form.work_type,
      description: form.description,
      estimated_cost: Number(form.estimated_cost),
      latitude: district.centroid_lat,
      longitude: district.centroid_lon,
      is_sc_st_area: form.is_sc_st_area,
      agency_id: form.agency_id || null,
    })
  }

  return (
    <div>
      <PageHeader
        eyebrow="New recommendation"
        title="Recommend a work"
        meta="Screening runs the moment you submit. Anything it finds goes to the District Authority — it never blocks your recommendation, because the system has no authority to refuse one."
      />

      {create.isSuccess && create.data && (
        <div className="border-b border-rule bg-notice px-5 py-4">
          <p className="text-[12.5px] text-notice-ink">
            <strong className="font-medium">{create.data.work_id} recorded.</strong>{' '}
            {create.data.open_flag_count > 0 ? (
              <>
                Screening raised {create.data.open_flag_count}{' '}
                {create.data.open_flag_count === 1 ? 'finding' : 'findings'} for the District
                Authority to review: {create.data.primary_finding}
              </>
            ) : (
              'Screening raised no findings.'
            )}
          </p>
        </div>
      )}

      <form onSubmit={submit} className="max-w-2xl px-5 py-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="District">
            <select
              value={districtId}
              onChange={(e) => setDistrictId(e.target.value)}
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            >
              <option value="">Select a district</option>
              {mine.map((d) => (
                <option key={d.district_id} value={d.district_id}>
                  {d.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Block">
            <input
              value={form.block}
              onChange={(e) => setForm({ ...form, block: e.target.value })}
              placeholder="e.g. Girwa"
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            />
          </Field>

          <Field label="Work type">
            <select
              value={form.work_type}
              onChange={(e) => setForm({ ...form, work_type: e.target.value })}
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 font-mono text-[12.5px]"
            >
              {WORK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Estimated cost (₹)">
            <input
              type="number"
              value={form.estimated_cost}
              onChange={(e) => setForm({ ...form, estimated_cost: e.target.value })}
              placeholder="600000"
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 font-mono text-[13px] tabular-nums"
            />
          </Field>

          <Field label="Proposed implementing agency">
            <select
              value={form.agency_id}
              onChange={(e) => setForm({ ...form, agency_id: e.target.value })}
              disabled={!districtId}
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px] disabled:bg-[#fafbfb]"
            >
              <option value="">Not yet decided</option>
              {(agencies.data ?? []).map((a) => (
                <option key={a.agency_id} value={a.agency_id}>
                  {a.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Area">
            <label className="flex items-center gap-2 py-1.5 text-[12.5px]">
              <input
                type="checkbox"
                checked={form.is_sc_st_area}
                onChange={(e) => setForm({ ...form, is_sc_st_area: e.target.checked })}
                className="size-3.5 accent-[#16457e]"
              />
              This work is in an SC or ST area
            </label>
          </Field>
        </div>

        <div className="mt-4">
          <Field label={`Description (${form.description.length}/20 minimum)`}>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
              placeholder="Construction of cement concrete road with side drains at…"
              className="w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            />
          </Field>
          <p className="mt-1 text-[11px] text-ink-muted">
            The description is compared against nearby recent works to catch duplication, so write
            it as you would in the sanction file.
          </p>
        </div>

        {create.isError && (
          <p className="mt-3 text-[12px] text-[#ae1414]">{(create.error as Error).message}</p>
        )}

        <button
          type="submit"
          disabled={!ready || create.isPending}
          className="mt-5 rounded-[2px] bg-seal px-4 py-2 text-[13px] font-medium text-white disabled:opacity-40"
        >
          {create.isPending ? 'Submitting and screening…' : 'Submit recommendation'}
        </button>
      </form>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="eyebrow">{label}</span>
      <div className="mt-1.5">{children}</div>
    </label>
  )
}
