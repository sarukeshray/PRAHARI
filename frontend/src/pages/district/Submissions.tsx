import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '@/api/client'
import { EmptyState, ErrorState, Loading, PageHeader, Section } from '@/components/ui-kit'
import { shortDate } from '@/lib/format'

/**
 * What the public has written in about.
 *
 * Kept visibly apart from the review queue. A finding is something the engine
 * computed against a threshold; a submission is a person's account. Mixing them
 * in one list would blur the difference between a measurement and an opinion,
 * and the whole product rests on that difference being legible.
 */

interface Submission {
  submission_id: number
  submission_type: 'WORK_SUGGESTION' | 'WORK_CONCERN'
  district_id: string
  district_name: string | null
  block: string | null
  related_work_id: string | null
  suggested_work_type: string | null
  description: string
  submitter_name: string
  submitted_at: string
  status: string
  official_response: string | null
  responded_by: string | null
}

const TYPE_LABEL = {
  WORK_SUGGESTION: 'Suggestion',
  WORK_CONCERN: 'Concern',
} as const

export function Submissions() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<'ALL' | 'WORK_SUGGESTION' | 'WORK_CONCERN'>('ALL')
  const [replyTo, setReplyTo] = useState<number | null>(null)
  const [text, setText] = useState('')

  const list = useQuery({
    queryKey: ['submissions', filter],
    queryFn: () =>
      api.get<Submission[]>(
        `/submissions${filter === 'ALL' ? '' : `?submission_type=${filter}`}`,
      ),
  })

  const respond = useMutation({
    mutationFn: (vars: { id: number; response: string; close: boolean }) =>
      api.post<Submission>(`/submissions/${vars.id}/respond`, {
        response: vars.response,
        close: vars.close,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['submissions'] })
      setReplyTo(null)
      setText('')
    },
  })

  const rows = list.data ?? []
  const open = rows.filter((r) => r.status === 'RECEIVED').length

  return (
    <div>
      <PageHeader
        eyebrow="From the public"
        title="Citizen submissions"
        meta={
          list.data
            ? `${rows.length} received · ${open} awaiting a reply`
            : 'Loading submissions…'
        }
      />

      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-5 py-2.5">
        {(['ALL', 'WORK_SUGGESTION', 'WORK_CONCERN'] as const).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => setFilter(k)}
            aria-pressed={filter === k}
            className={
              filter === k
                ? 'rounded-[2px] bg-seal px-3 py-1 text-[12px] text-white'
                : 'rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] text-ink-muted hover:text-ink'
            }
          >
            {k === 'ALL' ? 'All' : TYPE_LABEL[k]}
          </button>
        ))}
      </div>

      <Section
        title="Received"
        note="A submission is correspondence, not a finding. Nothing here has been screened or scored, and replying to one does not change the status of any work."
      >
        {list.isPending && <Loading rows={4} label="Loading submissions" />}
        {list.isError && (
          <ErrorState message={(list.error as Error).message} onRetry={() => list.refetch()} />
        )}

        {list.data && rows.length === 0 && (
          <EmptyState
            title="Nothing received yet"
            body="Suggestions and concerns submitted through the public view will appear here for a reply."
            action={
              <Link
                to="/public"
                className="inline-block rounded-[2px] border border-rule-strong px-3 py-1.5 text-[12.5px] hover:border-seal hover:text-seal"
              >
                Open the public form
              </Link>
            }
          />
        )}

        {rows.length > 0 && (
          <ul className="divide-y divide-rule rounded-[3px] border border-rule">
            {rows.map((r) => (
              <li key={r.submission_id} className="px-4 py-3.5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[12px] font-medium">
                      CS-{String(r.submission_id).padStart(6, '0')}
                    </span>
                    <span className="rounded-[2px] bg-seal-tint px-1.5 py-px text-[10px] font-medium tracking-wide text-seal uppercase">
                      {TYPE_LABEL[r.submission_type]}
                    </span>
                    {r.status !== 'RECEIVED' && (
                      <span className="rounded-[2px] bg-[#eef0f1] px-1.5 py-px text-[10px] font-medium tracking-wide text-ink-muted uppercase">
                        {r.status.toLowerCase()}
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-[11px] text-ink-faint">
                    {r.submitter_name} · {shortDate(r.submitted_at.slice(0, 10))}
                  </span>
                </div>

                <div className="mt-1 font-mono text-[11px] text-ink-faint">
                  {r.district_name}
                  {r.block ? ` · ${r.block}` : ''}
                  {r.suggested_work_type ? ` · ${r.suggested_work_type}` : ''}
                  {r.related_work_id ? ` · about ${r.related_work_id}` : ''}
                </div>

                <p className="mt-1.5 text-[12.5px] leading-relaxed">{r.description}</p>

                {r.official_response && (
                  <p className="mt-2 border-l-2 border-rule-strong pl-3 text-[12px] leading-snug text-ink-muted">
                    <span className="font-medium">{r.responded_by}:</span> {r.official_response}
                  </p>
                )}

                {r.status === 'RECEIVED' && (
                  <div className="mt-3">
                    {replyTo === r.submission_id ? (
                      <div className="rounded-[3px] border border-rule bg-[#fafbfb] p-3">
                        <label
                          htmlFor={`reply-${r.submission_id}`}
                          className="block text-[11.5px] font-medium"
                        >
                          Reply
                        </label>
                        <p className="mt-0.5 text-[11px] text-ink-muted">
                          Acknowledging is not agreeing. The reply is recorded against the
                          submission.
                        </p>
                        <textarea
                          id={`reply-${r.submission_id}`}
                          value={text}
                          onChange={(e) => setText(e.target.value)}
                          rows={2}
                          className="mt-2 w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[12.5px] focus:border-seal"
                        />
                        <div className="mt-2 flex flex-wrap justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setReplyTo(null)}
                            className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px]"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            disabled={text.trim().length < 10 || respond.isPending}
                            onClick={() =>
                              respond.mutate({
                                id: r.submission_id,
                                response: text,
                                close: false,
                              })
                            }
                            className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal disabled:opacity-40"
                          >
                            Acknowledge
                          </button>
                          <button
                            type="button"
                            disabled={text.trim().length < 10 || respond.isPending}
                            onClick={() =>
                              respond.mutate({ id: r.submission_id, response: text, close: true })
                            }
                            className="rounded-[2px] bg-seal px-3 py-1 text-[12px] font-medium text-white disabled:opacity-40"
                          >
                            Reply and close
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setReplyTo(r.submission_id)
                          setText('')
                        }}
                        className="rounded-[2px] border border-rule-strong px-3 py-1 text-[12px] hover:border-seal hover:text-seal"
                      >
                        Reply
                      </button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}
