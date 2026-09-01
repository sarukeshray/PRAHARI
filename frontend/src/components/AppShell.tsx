import { NavLink, useNavigate } from 'react-router-dom'

import { useHealth } from '@/api/hooks'
import { ROLE_LABEL, ROLE_NAV, useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

import { SyntheticDataBadge } from './SyntheticDataBadge'

/**
 * The frame every signed-in screen sits in.
 *
 * Navigation is built from the role the *server* reported, not from anything the
 * client decided, so the interface can never offer a section the API would
 * refuse.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, signOut } = useSession()
  const navigate = useNavigate()
  const { data: health } = useHealth()

  if (!me) return null
  const nav = ROLE_NAV[me.role] ?? []

  const jurisdiction =
    me.scope_district_name ??
    me.scope_agency_name ??
    me.scope_user_agency_name ??
    me.scope_state ??
    'National'

  return (
    <div className="min-h-screen bg-paper">
      <SyntheticDataBadge />

      <header className="flex flex-wrap items-center gap-3 border-b border-rule bg-surface px-4 py-2">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="flex items-center gap-2.5"
          aria-label="PRAHARI home"
        >
          <span className="flex size-7 items-center justify-center rounded-[2px] bg-seal">
            <span className="font-deva text-[13px] leading-none font-semibold text-white">प्र</span>
          </span>
          <span className="text-[13px] font-semibold tracking-[0.1em]">PRAHARI</span>
        </button>

        <span aria-hidden className="h-4 w-px bg-rule" />
        <span className="text-[12px] text-ink-muted">{ROLE_LABEL[me.role]}</span>

        <div className="ml-auto flex items-center gap-3">
          {health && (
            <span
              className="hidden font-mono text-[10.5px] text-ink-faint sm:inline"
              title={`Engine ${health.engine_version} · ${health.works_loaded.toLocaleString('en-IN')} works · auth: ${health.auth}`}
            >
              v{health.engine_version} · {health.auth}
            </span>
          )}
          <span className="text-[12px] font-medium">{me.display_name}</span>
          <button
            type="button"
            onClick={() => {
              signOut()
              navigate('/')
            }}
            className="rounded-[2px] border border-rule-strong px-2 py-0.5 text-[11.5px] text-ink-muted hover:border-seal hover:text-seal"
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-70px)] flex-col lg:flex-row">
        <aside className="shrink-0 border-b border-rule bg-surface lg:w-[212px] lg:border-r lg:border-b-0">
          <nav className="p-2" aria-label={`${ROLE_LABEL[me.role]} sections`}>
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    'block rounded-[2px] px-2.5 py-1.5 text-[12.5px] transition-colors',
                    isActive
                      ? 'bg-seal-tint font-medium text-seal'
                      : 'text-ink-muted hover:bg-[#f4f5f6] hover:text-ink',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden border-t border-rule px-4 py-3 lg:block">
            <div className="eyebrow">Jurisdiction</div>
            <div className="mt-1 text-[12px] text-ink-muted">{jurisdiction}</div>
            <div className="mt-2 eyebrow">Can see</div>
            <div className="mt-1 text-[12px] text-ink-muted">{me.scope}</div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  )
}
