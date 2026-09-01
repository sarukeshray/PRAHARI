import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { useHealth } from '@/api/hooks'
import type { RoleKey } from '@/api/types'
import { SyntheticDataBadge } from '@/components/SyntheticDataBadge'
import { ROLE_HOME, ROLE_LABEL, useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

/**
 * One sign-in screen with the role chosen first, because the role decides which
 * dashboard you land on — there is no shared landing view to fall back to.
 *
 * With Firebase configured this collects an email and password. Without it, the
 * backend accepts a demo account instead, and the screen says so rather than
 * pretending a password was checked.
 */

const DEMO_ACCOUNTS: Record<RoleKey, { userId: string; email: string; who: string }> = {
  DISTRICT_AUTHORITY: { userId: 'u-da-udaipur', email: 'da.udaipur@prahari.demo', who: 'S. Nair, IAS — Udaipur' },
  MP: { userId: 'u-mp', email: 'mp.udaipur@prahari.demo', who: 'Member for Udaipur' },
  MINISTRY: { userId: 'u-ministry', email: 'diid@prahari.demo', who: 'DIID Monitoring Cell' },
  STATE_NODAL: { userId: 'u-state-rj', email: 'sna.rajasthan@prahari.demo', who: 'Rajasthan Nodal Authority' },
  IMPLEMENTING_AGENCY: { userId: 'u-agency', email: 'pwd.udaipur@prahari.demo', who: 'PWD Division Udaipur' },
  USER_AGENCY: { userId: 'u-useragency', email: 'useragency.udaipur@prahari.demo', who: 'Receiving body, Udaipur' },
  PUBLIC: { userId: 'u-public', email: 'public@prahari.demo', who: 'Anonymous' },
}

const ORDER: RoleKey[] = [
  'DISTRICT_AUTHORITY',
  'MP',
  'MINISTRY',
  'STATE_NODAL',
  'IMPLEMENTING_AGENCY',
  'USER_AGENCY',
  'PUBLIC',
]

export function SignIn() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { signIn } = useSession()
  const { data: health } = useHealth()

  const initial = (params.get('role') as RoleKey) || 'DISTRICT_AUTHORITY'
  const [role, setRole] = useState<RoleKey>(ORDER.includes(initial) ? initial : 'DISTRICT_AUTHORITY')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const account = DEMO_ACCOUNTS[role]
  const firebaseLive = health?.auth === 'firebase'

  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      // Route to the role the SERVER confirms, not the one this form selected.
      // Navigating on a timer and hoping the identity had caught up is what made
      // every role land on whichever dashboard you used last.
      const identity = await signIn(account.userId)
      navigate(ROLE_HOME[identity.role], { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.')
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper">
      <SyntheticDataBadge />

      <div className="mx-auto max-w-lg px-6 py-12">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-[2px] bg-seal">
            <span className="font-deva text-[15px] leading-none font-semibold text-white">प्र</span>
          </span>
          <span className="text-[14px] font-semibold tracking-[0.11em]">PRAHARI</span>
        </Link>

        <h1 className="mt-8 text-[20px] font-semibold tracking-[-0.01em]">Sign in</h1>
        <p className="mt-1.5 text-[12.5px] text-ink-muted">
          Your role decides what you can see. Signing in as a different role means signing out
          first — the same as the real access model.
        </p>

        <form onSubmit={submit} className="mt-7">
          <div className="eyebrow">Role</div>
          <div className="mt-2 grid gap-px overflow-hidden rounded-[3px] border border-rule bg-rule sm:grid-cols-2">
            {ORDER.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setRole(key)}
                aria-pressed={role === key}
                className={cn(
                  'px-3 py-2.5 text-left transition-colors',
                  role === key ? 'bg-seal-tint' : 'bg-surface hover:bg-[#fafbfb]',
                )}
              >
                <div
                  className={cn(
                    'text-[12.5px] font-medium',
                    role === key ? 'text-seal' : 'text-ink',
                  )}
                >
                  {ROLE_LABEL[key]}
                </div>
                <div className="mt-0.5 text-[11px] text-ink-faint">{DEMO_ACCOUNTS[key].who}</div>
              </button>
            ))}
          </div>

          <div className="mt-5">
            <label htmlFor="email" className="eyebrow">
              Email
            </label>
            <input
              id="email"
              value={account.email}
              readOnly
              className="mt-1.5 w-full rounded-[2px] border border-rule-strong bg-[#fafbfb] px-2.5 py-1.5 font-mono text-[12.5px] text-ink-muted"
            />
          </div>

          <div className="mt-3">
            <label htmlFor="password" className="eyebrow">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={firebaseLive ? 'Your password' : 'Not required in demo mode'}
              disabled={!firebaseLive}
              className="mt-1.5 w-full rounded-[2px] border border-rule-strong bg-surface px-2.5 py-1.5 text-[13px] disabled:bg-[#fafbfb] disabled:text-ink-faint"
            />
          </div>

          {error && (
            <p className="mt-3 text-[12px] text-[#ae1414]">{error}</p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-5 w-full rounded-[2px] bg-seal px-4 py-2 text-[13px] font-medium text-white disabled:opacity-50"
          >
            {busy ? 'Signing in…' : `Continue as ${ROLE_LABEL[role]}`}
          </button>
        </form>

        {!firebaseLive && (
          <div className="mt-5 rounded-[3px] border border-notice-rule bg-notice px-3.5 py-3 text-[11.5px] leading-relaxed text-notice-ink">
            <strong className="font-medium">Demo sign-in.</strong> Firebase is not configured, so
            the backend is accepting a named demo account without checking a password. This is not
            authentication — it is a convenience for running locally, and it refuses to start in a
            production environment. The access rules behind it are real: each role still sees only
            its own slice of the data.
          </div>
        )}

        <p className="mt-6 text-[11.5px] text-ink-faint">
          No account needed for the{' '}
          <Link to="/public" className="text-seal hover:underline">
            public view
          </Link>
          .
        </p>
      </div>
    </div>
  )
}
