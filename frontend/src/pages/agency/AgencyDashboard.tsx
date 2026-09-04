import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { api, getDemoUser } from '@/api/client'
import { useAgencyPerformance, useFlags, useWorks } from '@/api/hooks'
import type { Flag, WorkSummary } from '@/api/types'
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
import { downloadCsv } from '@/lib/csv'
import { rupeesShort } from '@/lib/format'
import { MODULE_LABEL, flagTitle } from '@/lib/labels'
import { useSession } from '@/lib/session'

const SEAL = '#16457e'
const AMBER = '#a9670c'

/* ========================================================================== */
/* My works — progress and photographs                                         */
/* ========================================================================== */

export function AgencyWorks() {
  const works = useWorks({ limit: 200 })
  const [openFor, setOpenFor] = useState<string | null>(null)

  return (
    <div>
      <PageHeader
        eyebrow="Assigned to this agency"
        title="My works"
        meta="File progress and upload site photographs against the works you are executing."
        actions={
          <button
            type="button"
            disabled={!works.data?.length}
            onClick={() =>
              downloadCsv(
                `my-works-${new Date().toISOString().slice(0, 10)}.csv`,
                (works.data ?? []) as unknown as Record<string, unknown>[],
                ['work_id', 'work_type', 'block', 'estimated_cost', 'status', 'severity_tier', 'primary_finding'],
              )
            }
            className="rounded-[2px] border border-rule-strong px-2.5 py-1 text-[12px] hover:border-seal hover:text-seal disabled:opacity-40"
          >
            Export CSV
          </button>
        }
      />

      {works.isPending && <Loading rows={8} label="Loading works" />}
      {works.isError && (
        <ErrorState message={(works.error as Error).message} onRetry={() => works.refetch()} />
      )}
      {works.data?.length === 0 && (
        <EmptyState title="No works assigned" body="Works assigned to this agency will appear here." />
      )}

      {works.data && works.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[880px] border-collapse text-[12.5px]">
            <thead>
              <tr className="border-b border-rule bg-[#fafbfb]">
                <Th className="w-[150px]">Work ID</Th>
                <Th className="w-[140px]">Type</Th>
                <Th className="w-[110px] text-right">Estimate</Th>
                <Th className="w-[110px]">Status</Th>
                <Th className="w-[96px]">Severity</Th>
                <Th>Finding</Th>
                <Th className="w-[92px]" />
              </tr>
            </thead>
            <tbody>
              {works.data.map((w) => (
                <>
                  <tr key={w.work_id} className="border-b border-rule">
                    <Td className="font-mono text-[12px]">{w.work_id}</Td>
                    <Td className="font-mono text-[11.5px]">{w.work_type}</Td>
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
                    <Td>
                      <button
                        type="button"
                        onClick={() => setOpenFor(openFor === w.work_id ? null : w.work_id)}
                        className="rounded-[2px] border border-rule-strong px-2 py-0.5 text-[11.5px] hover:border-seal hover:text-seal"
                      >
                        {openFor === w.work_id ? 'Close' : 'Update'}
                      </button>
                    </Td>
                  </tr>
                  {openFor === w.work_id && (
                    <tr key={`${w.work_id}-panel`} className="border-b border-rule bg-[#fafbfb]">
                      <Td colSpan={7}>
                        <UpdatePanel work={w} onDone={() => setOpenFor(null)} />
                      </Td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function UpdatePanel({ work, onDone }: { work: WorkSummary; onDone: () => void }) {
  const qc = useQueryClient()
  const [progress, setProgress] = useState('')
  const [remarks, setRemarks] = useState('')
  const [stage, setStage] = useState('COMPLETE')
  const [file, setFile] = useState<File | null>(null)
  const [photoResult, setPhotoResult] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['works'] })
    qc.invalidateQueries({ queryKey: ['flags'] })
  }

  const submitProgress = useMutation({
    mutationFn: () =>
      api.post(`/agency/works/${work.work_id}/progress`, {
        physical_progress_pct: Number(progress),
        remarks,
      }),
    onSuccess: () => {
      invalidate()
      setProgress('')
      setRemarks('')
      onDone()
    },
  })

  /**
   * Uploaded with fetch rather than the JSON client, because it is multipart.
   * The browser must set its own Content-Type boundary.
   */
  const uploadPhoto = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Choose a photograph first.')
      const body = new FormData()
      body.append('stage', stage)
      body.append('file', file)
      const demo = getDemoUser()
      const base = import.meta.env.VITE_API_BASE_URL ?? ''
      const res = await fetch(`${base}/api/v1/agency/works/${work.work_id}/photos`, {
        method: 'POST',
        headers: demo ? { 'X-Demo-User': demo } : {},
        body,
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail.detail ?? `Upload failed (${res.status})`)
      }
      return res.json() as Promise<{ metadata_note: string; photo_lat: number | null }>
    },
    onSuccess: (d) => {
      setPhotoResult(d.metadata_note)
      setFile(null)
      if (fileInput.current) fileInput.current.value = ''
      invalidate()
    },
  })

  return (
    <div className="grid gap-6 py-2 lg:grid-cols-2">
      <div>
        <div className="eyebrow">File physical progress</div>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="block">
            <span className="text-[11px] text-ink-muted">Progress %</span>
            <input
              type="number"
              min={0}
              max={100}
              value={progress}
              onChange={(e) => setProgress(e.target.value)}
              className="mt-1 w-24 rounded-[2px] border border-rule-strong bg-surface px-2 py-1 font-mono text-[12.5px] tabular-nums"
            />
          </label>
          <label className="block flex-1">
            <span className="text-[11px] text-ink-muted">Remarks</span>
            <input
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="Optional"
              className="mt-1 w-full rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12.5px]"
            />
          </label>
          <button
            type="button"
            disabled={!progress || submitProgress.isPending}
            onClick={() => submitProgress.mutate()}
            className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-40"
          >
            {submitProgress.isPending ? 'Filing…' : 'File'}
          </button>
        </div>
        {submitProgress.isError && (
          <p className="mt-2 text-[11.5px] text-[#ae1414]">
            {(submitProgress.error as Error).message}
          </p>
        )}
        <p className="mt-2 text-[11px] leading-snug text-ink-muted">
          This figure is compared against the funds actually released. A gap between them is what
          the disbursement finding is about.
        </p>
      </div>

      <div>
        <div className="eyebrow">Upload a site photograph</div>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="block">
            <span className="text-[11px] text-ink-muted">Stage</span>
            <select
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              className="mt-1 rounded-[2px] border border-rule-strong bg-surface px-2 py-1 text-[12.5px]"
            >
              <option value="START">Start</option>
              <option value="MID">Mid</option>
              <option value="COMPLETE">Complete</option>
            </select>
          </label>
          <label className="block flex-1">
            <span className="text-[11px] text-ink-muted">Photograph</span>
            <input
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-1 w-full text-[11.5px] file:mr-2 file:rounded-[2px] file:border file:border-rule-strong file:bg-surface file:px-2 file:py-1 file:text-[11.5px]"
            />
          </label>
          <button
            type="button"
            disabled={!file || uploadPhoto.isPending}
            onClick={() => uploadPhoto.mutate()}
            className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-40"
          >
            {uploadPhoto.isPending ? 'Uploading…' : 'Upload'}
          </button>
        </div>
        {uploadPhoto.isError && (
          <p className="mt-2 text-[11.5px] text-[#ae1414]">{(uploadPhoto.error as Error).message}</p>
        )}
        {photoResult && (
          <p className="mt-2 rounded-[2px] border border-rule bg-surface px-2.5 py-2 text-[11.5px] leading-snug text-ink-muted">
            {photoResult}
          </p>
        )}
        <p className="mt-2 text-[11px] leading-snug text-ink-muted">
          Location and capture time are read from the file on the server, never taken from this
          browser — the geotag check exists to verify the party uploading.
        </p>
      </div>
    </div>
  )
}

/* ========================================================================== */
/* Findings on my works, with a response                                       */
/* ========================================================================== */

export function AgencyFindings() {
  const flags = useFlags({ status: 'OPEN' })

  return (
    <div>
      <PageHeader
        eyebrow="On my works"
        title="Findings"
        meta="What has been raised against works this agency is executing, and the numbers behind each one."
      />

      <div className="border-b border-notice-rule bg-notice px-5 py-3">
        <p className="max-w-3xl text-[12px] leading-relaxed text-notice-ink">
          Responding attaches your account of a finding for the District Authority to weigh. It
          does <strong className="font-medium">not</strong> clear the finding — letting the party a
          finding is about resolve it would empty the review of meaning.
        </p>
      </div>

      {flags.isPending && <Loading rows={5} label="Loading findings" />}
      {flags.isError && (
        <ErrorState message={(flags.error as Error).message} onRetry={() => flags.refetch()} />
      )}
      {flags.data?.length === 0 && (
        <EmptyState
          title="Nothing has been raised"
          body="No open findings sit against works assigned to this agency."
        />
      )}

      {flags.data && flags.data.length > 0 && (
        <ul className="divide-y divide-rule">
          {flags.data.map((f) => (
            <FindingRow key={f.flag_id} flag={f} />
          ))}
        </ul>
      )}
    </div>
  )
}

function FindingRow({ flag }: { flag: Flag }) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')

  const responses = useQuery({
    queryKey: ['agencyResponses', flag.flag_id],
    queryFn: () =>
      api.get<{ response_id: number; submitted_date: string; note: string }[]>(
        `/agency/flags/${flag.flag_id}/responses`,
      ),
  })

  const respond = useMutation({
    mutationFn: () => api.post(`/agency/flags/${flag.flag_id}/respond`, { note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agencyResponses', flag.flag_id] })
      setNote('')
      setOpen(false)
    },
  })

  return (
    <li className="bg-surface px-5 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[12px] font-medium">{flag.work_id}</span>
          <SeverityChip severity={flag.severity_tier} size="sm" />
        </div>
        <span className="font-mono text-[11px] text-ink-faint">{MODULE_LABEL[flag.module]}</span>
      </div>
      <div className="mt-1 text-[13px] font-medium">{flagTitle(flag.flag_code)}</div>
      <p className="mt-1 border-l-2 border-rule-strong pl-3 text-[12.5px] leading-relaxed">
        {flag.explanation}
      </p>

      {(responses.data ?? []).length > 0 && (
        <ul className="mt-2 space-y-1">
          {responses.data!.map((r) => (
            <li key={r.response_id} className="text-[11.5px] text-ink-muted">
              <span className="font-mono text-[10.5px] text-ink-faint">{r.submitted_date}</span>{' '}
              {r.note}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3">
        {open ? (
          <div className="rounded-[3px] border border-rule bg-[#fafbfb] p-3">
            <label
              htmlFor={`resp-${flag.flag_id}`}
              className="block text-[11.5px] font-medium"
            >
              Your account of this finding
            </label>
            <textarea
              id={`resp-${flag.flag_id}`}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              className="mt-2 w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] focus:border-seal"
            />
            <div className="mt-2 flex items-center justify-between gap-3">
              <span className="text-[11px] text-ink-muted">
                {note.trim().length < 15
                  ? `${15 - note.trim().length} more characters needed`
                  : respond.isError
                    ? (respond.error as Error).message
                    : ' '}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={note.trim().length < 15 || respond.isPending}
                  onClick={() => respond.mutate()}
                  className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-40"
                >
                  {respond.isPending ? 'Sending…' : 'Send response'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal"
          >
            Respond with evidence
          </button>
        )}
      </div>
    </li>
  )
}

/* ========================================================================== */
/* Performance                                                                 */
/* ========================================================================== */

export function AgencyPerformanceScreen() {
  const { me } = useSession()
  const perf = useAgencyPerformance(me?.scope_agency_id)

  if (perf.isPending) return <Loading rows={6} label="Loading performance" />
  if (perf.isError)
    return <ErrorState message={(perf.error as Error).message} onRetry={() => perf.refetch()} />
  if (!perf.data) return null

  const p = perf.data
  const sorted = [...p.peer_percentiles].sort((a, b) => a - b)
  const q = (f: number) => sorted[Math.min(sorted.length - 1, Math.floor(f * sorted.length))] ?? 0

  return (
    <div>
      <PageHeader
        eyebrow={p.name}
        title="My performance"
        meta="How this agency is being measured, shown in full. A percentile without its comparison group is not interpretable, so the peer set is named."
      />

      <div className="grid grid-cols-2 gap-px border-b border-rule bg-rule lg:grid-cols-4">
        <Stat
          label="Percentile in peer group"
          value={p.percentile.toFixed(0)}
          hint={`Among ${p.peer_count} agencies in ${p.peer_group_label}`}
          accent={p.flagged ? AMBER : undefined}
        />
        <Stat
          label="Completed works"
          value={String(p.completed_works)}
          hint={`of ${p.total_works} assigned`}
        />
        <Stat label="Completion rate" value={`${p.completion_rate.toFixed(0)}%`} />
        <Stat
          label="Mean cost variance"
          value={`${p.mean_overrun_pct >= 0 ? '+' : ''}${p.mean_overrun_pct.toFixed(1)}%`}
        />
      </div>

      <Section title="Against the peer group" note={p.note}>
        <div className="max-w-2xl">
          <div className="relative h-16">
            <div className="absolute top-1/2 right-0 left-0 h-px -translate-y-1/2 bg-rule" />
            <div
              className="absolute top-1/2 h-8 -translate-y-1/2 rounded-[2px] border border-rule-strong bg-[#f4f5f6]"
              style={{ left: `${q(0.25)}%`, width: `${Math.max(2, q(0.75) - q(0.25))}%` }}
              title={`Middle half of the peer group: ${q(0.25).toFixed(0)}th to ${q(0.75).toFixed(0)}th percentile`}
            />
            <div
              className="absolute top-1/2 h-8 w-px -translate-y-1/2 bg-ink"
              style={{ left: `${q(0.5)}%` }}
              title="Median"
            />
            <div
              className="absolute top-1/2 h-10 w-[3px] -translate-y-1/2 rounded-[1px]"
              style={{ left: `${p.percentile}%`, backgroundColor: p.flagged ? AMBER : SEAL }}
              title={`This agency: ${p.percentile.toFixed(0)}th percentile`}
            />
          </div>
          <div className="flex justify-between font-mono text-[10px] text-ink-faint">
            <span>weakest</span>
            <span>median</span>
            <span>strongest</span>
          </div>
          <p className="mt-4 text-[12px] leading-relaxed text-ink-muted">
            The bar marks this agency; the box is the middle half of the peer group. Ranking is
            within {p.peer_group_label.toLowerCase()} only — an agency working in harder terrain is
            never measured against one working on the plains, because the terrain would become a
            permanent penalty it could not escape by performing well.
          </p>
        </div>
      </Section>
    </div>
  )
}
