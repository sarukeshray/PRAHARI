import { useState } from 'react'

import { api } from '@/api/client'
import { useDistrictRefs } from '@/api/hooks'
import { Section } from '@/components/ui-kit'

/**
 * The public submission form.
 *
 * Two things a citizen can do: put a work forward for their Member to consider,
 * or raise a concern about one already under way.
 *
 * The copy is careful about what a submission is. A citizen cannot recommend an
 * MPLADS work — only a Member can — so this is correspondence routed to the
 * Member and the District Authority, not an entry into the screening pipeline.
 * Saying otherwise would set an expectation the Scheme cannot meet.
 */

type Kind = 'WORK_SUGGESTION' | 'WORK_CONCERN'

const WORK_TYPES = [
  'ROAD_CC', 'ROAD_BT', 'COMMUNITY_HALL', 'SCHOOL_BUILDING', 'WATER_TANK', 'BOREWELL',
  'STREET_LIGHTING', 'DRAINAGE', 'TOILET_BLOCK', 'LIBRARY', 'BUS_SHELTER', 'CREMATORIUM_SHED',
]

const MIN_DESCRIPTION = 25

interface Receipt {
  submission_id: number
  reference: string
  status: string
  message: string
}

export function CitizenForm() {
  const districts = useDistrictRefs()
  const [kind, setKind] = useState<Kind>('WORK_SUGGESTION')
  const [form, setForm] = useState({
    district_id: '',
    block: '',
    suggested_work_type: '',
    related_work_id: '',
    description: '',
    submitter_name: '',
    submitter_contact: '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<Receipt | null>(null)

  const isSuggestion = kind === 'WORK_SUGGESTION'
  const ready =
    form.district_id &&
    form.submitter_name.trim().length >= 2 &&
    form.description.trim().length >= MIN_DESCRIPTION

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!ready) return
    setBusy(true)
    setError(null)
    try {
      const body = {
        submission_type: kind,
        district_id: form.district_id,
        block: form.block || null,
        suggested_work_type: isSuggestion ? form.suggested_work_type || null : null,
        related_work_id: !isSuggestion && form.related_work_id ? form.related_work_id : null,
        description: form.description.trim(),
        submitter_name: form.submitter_name.trim(),
        submitter_contact: form.submitter_contact.trim() || null,
      }
      setReceipt(await api.post<Receipt>('/public/submissions', body))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit.')
    } finally {
      setBusy(false)
    }
  }

  if (receipt) {
    return (
      <Section title="Submission recorded">
        <div className="max-w-2xl rounded-[3px] border border-rule bg-surface p-5">
          <div className="eyebrow">Your reference</div>
          <div className="mt-1 font-mono text-[22px] leading-none font-medium">
            {receipt.reference}
          </div>
          <p className="mt-3 text-[12.5px] leading-relaxed text-ink-muted">{receipt.message}</p>
          <button
            type="button"
            onClick={() => {
              setReceipt(null)
              setForm({
                district_id: '', block: '', suggested_work_type: '', related_work_id: '',
                description: '', submitter_name: '', submitter_contact: '',
              })
            }}
            className="mt-4 rounded-[2px] border border-rule-strong px-3 py-1.5 text-[12.5px] hover:border-seal hover:text-seal"
          >
            Make another submission
          </button>
        </div>
      </Section>
    )
  }

  return (
    <Section
      title="Suggest a work, or raise a concern"
      note="Open to anyone. What you send reaches the Member of Parliament for the constituency and the District Authority for the district."
    >
      <form onSubmit={submit} className="max-w-2xl">
        <div className="eyebrow">What is this about?</div>
        <div className="mt-2 grid gap-px overflow-hidden rounded-[3px] border border-rule bg-rule sm:grid-cols-2">
          {(
            [
              {
                key: 'WORK_SUGGESTION' as Kind,
                title: 'Suggest a work',
                body: 'Something your area needs that is not yet built.',
              },
              {
                key: 'WORK_CONCERN' as Kind,
                title: 'Raise a concern',
                body: 'Something about a work already under way or finished.',
              },
            ]
          ).map((o) => (
            <button
              key={o.key}
              type="button"
              onClick={() => setKind(o.key)}
              aria-pressed={kind === o.key}
              className={
                kind === o.key
                  ? 'bg-seal-tint px-3.5 py-3 text-left'
                  : 'bg-surface px-3.5 py-3 text-left hover:bg-[#fafbfb]'
              }
            >
              <div
                className={
                  kind === o.key
                    ? 'text-[12.5px] font-medium text-seal'
                    : 'text-[12.5px] font-medium'
                }
              >
                {o.title}
              </div>
              <div className="mt-0.5 text-[11.5px] text-ink-muted">{o.body}</div>
            </button>
          ))}
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Field label="District" required>
            <select
              value={form.district_id}
              onChange={(e) => setForm({ ...form, district_id: e.target.value })}
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            >
              <option value="">Select your district</option>
              {(districts.data ?? []).map((d) => (
                <option key={d.district_id} value={d.district_id}>
                  {d.name} — {d.state}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Block or village">
            <input
              value={form.block}
              onChange={(e) => setForm({ ...form, block: e.target.value })}
              placeholder="Optional"
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            />
          </Field>

          {isSuggestion ? (
            <Field label="Kind of work">
              <select
                value={form.suggested_work_type}
                onChange={(e) => setForm({ ...form, suggested_work_type: e.target.value })}
                className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 font-mono text-[12.5px]"
              >
                <option value="">Not sure</option>
                {WORK_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </Field>
          ) : (
            <Field label="Work reference, if you have it">
              <input
                value={form.related_work_id}
                onChange={(e) => setForm({ ...form, related_work_id: e.target.value })}
                placeholder="e.g. RJ-UDR-00085"
                className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 font-mono text-[12.5px]"
              />
            </Field>
          )}

          <Field label="Your name" required>
            <input
              value={form.submitter_name}
              onChange={(e) => setForm({ ...form, submitter_name: e.target.value })}
              className="w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            />
          </Field>
        </div>

        <div className="mt-4">
          <Field
            label={`In your own words (${form.description.trim().length}/${MIN_DESCRIPTION} minimum)`}
            required
          >
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={4}
              placeholder={
                isSuggestion
                  ? 'What is needed, where, and who would use it?'
                  : 'What have you noticed about this work?'
              }
              className="w-full resize-y rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            />
          </Field>
        </div>

        <div className="mt-4">
          <Field label="Phone or email">
            <input
              value={form.submitter_contact}
              onChange={(e) => setForm({ ...form, submitter_contact: e.target.value })}
              placeholder="Optional — only used to reply to you"
              className="w-full max-w-sm rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px]"
            />
          </Field>
          <p className="mt-1 text-[11px] text-ink-muted">
            Leaving this blank is fine. You will still get a reference number, and the submission
            is still recorded.
          </p>
        </div>

        <div className="mt-5 rounded-[3px] border border-notice-rule bg-notice px-3.5 py-3 text-[11.5px] leading-relaxed text-notice-ink">
          <strong className="font-medium">What happens next.</strong>{' '}
          {isSuggestion
            ? 'A suggestion is not a sanctioned work. Under MPLADS only a Member of Parliament may recommend a work, and only the District Authority may sanction one. Your submission reaches both of them for consideration.'
            : 'A concern does not change the status of a work and is not treated as a finding. A person reads it and decides what it warrants.'}
        </div>

        {error && <p className="mt-3 text-[12px] text-[#ae1414]">{error}</p>}

        <button
          type="submit"
          disabled={!ready || busy}
          className="mt-4 rounded-[2px] bg-seal px-4 py-2 text-[13px] font-medium text-white disabled:opacity-40"
        >
          {busy ? 'Submitting…' : isSuggestion ? 'Send suggestion' : 'Send concern'}
        </button>
      </form>
    </Section>
  )
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="eyebrow">
        {label}
        {required && <span className="ml-1 text-[#ae1414]">*</span>}
      </span>
      <div className="mt-1.5">{children}</div>
    </label>
  )
}
