import { NavLink, useNavigate } from 'react-router-dom'

import { ROLES, type RoleKey } from '@/data/roles'
import { cn } from '@/lib/utils'

import { SyntheticDataBadge } from './SyntheticDataBadge'

/**
 * The frame every screen sits in: provenance notice, masthead, role rail.
 *
 * The wordmark is set bilingually because PRAHARI is a Hindi-named system for a
 * Government of India scheme, and that is how such systems present themselves on
 * their own letterhead. IBM Plex covers Devanagari and Latin at matching
 * proportions, which is why the family was chosen.
 */
export function AppShell({ role, children }: { role: RoleKey; children: React.ReactNode }) {
  const navigate = useNavigate()
  const config = ROLES[role]

  return (
    <div className="min-h-screen bg-paper">
      <SyntheticDataBadge />

      <div className="flex min-h-[calc(100vh-26px)] flex-col lg:flex-row">
        <aside className="shrink-0 border-b border-rule bg-surface lg:w-[228px] lg:border-r lg:border-b-0">
          <div className="flex items-center gap-2.5 border-b border-rule px-4 py-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-[2px] bg-seal">
              <span className="font-deva text-[15px] leading-none font-semibold text-white">
                प्र
              </span>
            </div>
            <div className="min-w-0">
              <div className="text-[13px] leading-tight font-semibold tracking-[0.1em]">
                PRAHARI
              </div>
              <div className="truncate text-[10px] leading-tight text-ink-faint">
                MPLADS oversight
              </div>
            </div>
          </div>

          <div className="border-b border-rule px-4 py-2.5">
            <div className="eyebrow">Signed in as</div>
            <div className="mt-1 text-[12.5px] font-medium">{config.officer}</div>
            <div className="text-[11px] text-ink-muted">{config.label}</div>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="mt-2 text-[11px] text-seal underline-offset-2 hover:underline"
            >
              Switch role
            </button>
          </div>

          <nav className="p-2" aria-label={`${config.label} sections`}>
            {config.nav.map((item) => (
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

          <div className="hidden px-4 py-3 lg:block">
            <div className="eyebrow">Jurisdiction</div>
            <div className="mt-1 text-[12px] text-ink-muted">{config.jurisdiction}</div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  )
}

/** Page title strip. Kept separate so each screen controls its own actions. */
export function PageHeader({
  eyebrow,
  title,
  meta,
  actions,
}: {
  eyebrow: React.ReactNode
  title: string
  meta?: string
  actions?: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-rule bg-surface px-5 py-3.5">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="mt-0.5 text-[19px] leading-tight font-semibold tracking-[-0.01em]">
          {title}
        </h1>
        {meta && <p className="mt-1 text-[12px] text-ink-muted">{meta}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
