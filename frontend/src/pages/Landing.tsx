import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useHealth } from '@/api/hooks'
import { SyntheticDataBadge } from '@/components/SyntheticDataBadge'

/**
 * The public landing page.
 *
 * The hero is the thesis of the whole product: the same irregularity, found
 * years apart. Two timeline bars, one ending at an audit long after the money
 * is spent, one ending at a screening before it is committed. It animates once
 * on load and then stops — this is a page about public money, not a showreel.
 */

const STEPS = [
  { n: 'Proposal', d: 'A Member recommends a work.' },
  { n: 'Stage 1 screening', d: 'Cost, duplication, agency record and the compliance rules — before sanction.' },
  { n: 'Sanction', d: 'A District Officer decides, with the findings in front of them.' },
  { n: 'Stage 2 monitoring', d: 'Disbursement against progress, photograph metadata, timelines.' },
  { n: 'Handover & lifecycle', d: 'Who owns the asset, and is it still standing?' },
]

const ROLES = [
  { key: 'DISTRICT_AUTHORITY', name: 'District Authority', d: 'Screens every recommendation and decides what each finding warrants.' },
  { key: 'MP', name: 'Member of Parliament', d: 'Tracks entitlement, mandated-area allocation, and findings on own works.' },
  { key: 'MINISTRY', name: 'Ministry (MoSPI)', d: 'Compares states and sets the thresholds every district screens against.' },
  { key: 'STATE_NODAL', name: 'State Nodal Authority', d: 'Compares districts and escalates findings that have gone unresolved.' },
  { key: 'IMPLEMENTING_AGENCY', name: 'Implementing Agency', d: 'Files progress, uploads evidence, and responds to findings on its works.' },
  { key: 'USER_AGENCY', name: 'User Agency', d: 'Receives the finished asset and keeps its condition on record.' },
  { key: 'PUBLIC', name: 'Public', d: 'Aggregate utilisation and completion. No individual detail.' },
]

function useCountUp(target: number, run: boolean, ms = 900) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!run) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setValue(target)
      return
    }
    const started = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - started) / ms)
      setValue(target * (1 - Math.pow(1 - t, 3)))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, run, ms])
  return value
}

function StatCard({
  value,
  suffix,
  label,
  source,
  run,
  decimals = 0,
}: {
  value: number
  suffix: string
  label: string
  source: string
  run: boolean
  decimals?: number
}) {
  const n = useCountUp(value, run)
  return (
    <div className="border border-rule bg-surface p-5">
      <div className="font-mono text-[28px] leading-none font-medium tabular-nums">
        {n.toLocaleString('en-IN', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        })}
        <span className="ml-1 text-[15px] text-ink-muted">{suffix}</span>
      </div>
      <div className="mt-2 text-[12.5px] leading-snug">{label}</div>
      <div className="mt-2 text-[11px] text-ink-faint">{source}</div>
    </div>
  )
}

export function Landing() {
  const navigate = useNavigate()
  const { data: health } = useHealth()
  const [inView, setInView] = useState(false)
  const statsRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const node = statsRef.current
    if (!node) return
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setInView(true),
      { threshold: 0.3 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div className="min-h-screen bg-paper">
      <SyntheticDataBadge />

      <header className="flex items-center gap-3 border-b border-rule bg-surface px-6 py-3">
        <span className="flex size-8 items-center justify-center rounded-[2px] bg-seal">
          <span className="font-deva text-[15px] leading-none font-semibold text-white">प्र</span>
        </span>
        <div>
          <div className="text-[14px] leading-none font-semibold tracking-[0.11em]">PRAHARI</div>
          <div className="mt-0.5 text-[10.5px] text-ink-faint">MPLADS preventive oversight</div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/public"
            className="rounded-[2px] border border-rule-strong px-3 py-1.5 text-[12.5px] text-ink-muted hover:border-seal hover:text-seal"
          >
            Public view
          </Link>
          <button
            type="button"
            onClick={() => navigate('/signin')}
            className="rounded-[2px] bg-seal px-4 py-1.5 text-[12.5px] font-medium text-white"
          >
            Sign in
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-rule bg-surface px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <h1 className="max-w-2xl text-[30px] leading-[1.15] font-semibold tracking-[-0.02em]">
            The irregularity is the same. Only the year you find it changes.
          </h1>
          <p className="mt-4 max-w-2xl text-[14px] leading-relaxed text-ink-muted">
            MPLADS moves roughly ₹4,000 crore a year through thousands of small works. Today those
            problems surface in audit, long after the money is gone. PRAHARI screens a work
            <strong className="font-medium text-ink"> before sanction</strong>, monitors it after,
            and puts what it finds in front of a person who decides.
          </p>

          <ReactiveVsPreventive />

          <p className="mt-8 max-w-2xl text-[12.5px] leading-relaxed text-ink-muted">
            It does not approve, reject or block anything. Every output is a risk indicator routed
            to a human reviewer — never a determination about a Member, an agency or an officer.
          </p>
        </div>
      </section>

      {/* The problem */}
      <section ref={statsRef} className="border-b border-rule px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <div className="eyebrow">What the auditor already found</div>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <StatCard
              run={inView} value={4000} suffix="Cr / year"
              label="Moves through the Scheme annually, across roughly 788 Members."
              source="MPLADS Guidelines"
            />
            <StatCard
              run={inView} value={53.74} decimals={2} suffix="Cr"
              label="Spent on works inadmissible under the Scheme."
              source="CAG Report No. 31 of 2010"
            />
            <StatCard
              run={inView} value={10.18} decimals={2} suffix="Cr"
              label="Across 775 sanctioned works never taken up by the implementing agency."
              source="CAG Report No. 31 of 2010"
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-b border-rule bg-surface px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <div className="eyebrow">How it works</div>
          <ol className="mt-5 grid gap-px bg-rule md:grid-cols-5">
            {STEPS.map((s, i) => (
              <li key={s.n} className="bg-surface p-4">
                <div className="font-mono text-[11px] text-ink-faint">
                  {String(i + 1).padStart(2, '0')}
                </div>
                <div className="mt-1.5 text-[13px] font-medium">{s.n}</div>
                <p className="mt-1 text-[11.5px] leading-snug text-ink-muted">{s.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Roles */}
      <section className="border-b border-rule px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <div className="eyebrow">Seven roles, seven different views</div>
          <p className="mt-2 max-w-2xl text-[12.5px] text-ink-muted">
            Each sees only what its work requires. Selecting one here takes you to sign-in with that
            role pre-selected — it does not bypass it.
          </p>
          <div className="mt-5 grid gap-px bg-rule sm:grid-cols-2 lg:grid-cols-3">
            {ROLES.map((r) => (
              <button
                key={r.key}
                type="button"
                onClick={() => navigate(`/signin?role=${r.key}`)}
                className="group bg-surface p-4 text-left transition-colors hover:bg-[#fafbfb]"
              >
                <div className="text-[13px] font-medium group-hover:text-seal">{r.name}</div>
                <p className="mt-1 text-[11.5px] leading-snug text-ink-muted">{r.d}</p>
              </button>
            ))}
          </div>
        </div>
      </section>

      <footer className="px-6 py-10">
        <div className="mx-auto max-w-5xl space-y-3 text-[11.5px] leading-relaxed text-ink-faint">
          <p>
            <strong className="font-medium text-ink-muted">All data shown is synthetic.</strong>{' '}
            No screen reflects live MPLADS records, and no Member, agency or officer named anywhere
            in this system is real. Detection figures measure the method against anomalies generated
            for that purpose; they are not a measurement of real-world accuracy.
          </p>
          <p>
            Sources: MPLADS Guidelines 2023; CAG Report No. 31 of 2010, Performance Audit of MPLADS;
            State PWD Schedules of Rates.
          </p>
          {health && (
            <p className="font-mono">
              engine v{health.engine_version} · {health.works_loaded.toLocaleString('en-IN')} works
              loaded · auth: {health.auth}
            </p>
          )}
        </div>
      </footer>
    </div>
  )
}

/**
 * The signature visual: one problem, two timelines.
 *
 * Deliberately not a chart. It is the argument of the product drawn once, and it
 * animates a single time on load rather than looping.
 */
function ReactiveVsPreventive() {
  const [drawn, setDrawn] = useState(false)
  useEffect(() => {
    const id = window.setTimeout(() => setDrawn(true), 180)
    return () => window.clearTimeout(id)
  }, [])

  const reduce =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const width = (target: string) => (drawn || reduce ? target : '0%')

  return (
    <div className="mt-10 max-w-3xl border border-rule bg-paper p-5">
      <div className="grid gap-5">
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-[11.5px] font-medium">Today — reactive</span>
            <span className="font-mono text-[11px] text-ink-faint">audit, years later</span>
          </div>
          <div className="relative mt-2 h-6">
            <div className="absolute inset-y-0 left-0 w-full rounded-[1px] bg-[#eceeef]" />
            <div
              className="absolute inset-y-0 left-0 rounded-[1px] bg-[#b0b8bf] transition-[width] duration-[1400ms] ease-out"
              style={{ width: width('100%') }}
            />
            <div className="absolute inset-y-0 right-0 flex items-center pr-2">
              <span className="rounded-[2px] bg-[#ae1414] px-1.5 py-0.5 text-[9.5px] font-medium tracking-wide text-white uppercase">
                Found
              </span>
            </div>
          </div>
          <div className="mt-1 flex justify-between font-mono text-[10px] text-ink-faint">
            <span>recommendation</span>
            <span>money spent</span>
            <span>CAG audit</span>
          </div>
        </div>

        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-[11.5px] font-medium">PRAHARI — preventive</span>
            <span className="font-mono text-[11px] text-ink-faint">before sanction</span>
          </div>
          <div className="relative mt-2 h-6">
            <div className="absolute inset-y-0 left-0 w-full rounded-[1px] bg-[#eceeef]" />
            <div
              className="absolute inset-y-0 left-0 rounded-[1px] bg-seal transition-[width] duration-[1400ms] ease-out"
              style={{ width: width('22%'), transitionDelay: '260ms' }}
            />
            <div className="absolute inset-y-0 flex items-center" style={{ left: '22%' }}>
              <span className="ml-1.5 rounded-[2px] bg-seal px-1.5 py-0.5 text-[9.5px] font-medium tracking-wide text-white uppercase">
                Flagged
              </span>
            </div>
          </div>
          <div className="mt-1 flex justify-between font-mono text-[10px] text-ink-faint">
            <span>recommendation</span>
            <span>money spent</span>
            <span>CAG audit</span>
          </div>
        </div>
      </div>
    </div>
  )
}
