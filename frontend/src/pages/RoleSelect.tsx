import { Link } from 'react-router-dom'

import { SyntheticDataBadge } from '@/components/SyntheticDataBadge'
import { ROLES, UNBUILT_ROLES, type RoleKey } from '@/data/roles'

const ORDER: RoleKey[] = ['district', 'mp', 'ministry']

const LANDING: Record<RoleKey, string> = {
  district: '/district',
  mp: '/mp',
  ministry: '/ministry',
}

export function RoleSelect() {
  return (
    <div className="min-h-screen bg-paper">
      <SyntheticDataBadge />

      <div className="mx-auto max-w-3xl px-6 py-14">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-[3px] bg-seal">
            <span className="font-deva text-[21px] leading-none font-semibold text-white">प्र</span>
          </div>
          <div>
            <div className="text-[20px] leading-none font-semibold tracking-[0.12em]">PRAHARI</div>
            <div className="mt-1 text-[12px] text-ink-muted">
              Preventive oversight for the MPLAD Scheme
            </div>
          </div>
        </div>

        <p className="mt-6 max-w-xl text-[13px] leading-relaxed text-ink-muted">
          PRAHARI screens a recommended work before sanction and monitors it afterwards, then puts
          what it finds in front of a person. It does not approve, reject or block anything — every
          finding is routed to a reviewer, who decides.
        </p>

        <div className="mt-9">
          <div className="eyebrow">Continue as</div>
          <div className="mt-3 divide-y divide-rule overflow-hidden rounded-[3px] border border-rule bg-surface">
            {ORDER.map((key) => {
              const role = ROLES[key]
              return (
                <Link
                  key={key}
                  to={LANDING[key]}
                  className="group flex items-start gap-4 px-4 py-3.5 transition-colors hover:bg-[#fafbfb]"
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-[13.5px] font-medium group-hover:text-seal">
                      {role.label}
                    </div>
                    <div className="mt-0.5 text-[12px] text-ink-muted">{role.summary}</div>
                    <div className="mt-1.5 font-mono text-[11px] text-ink-faint">
                      {role.officer} · {role.jurisdiction}
                    </div>
                  </div>
                  <span
                    aria-hidden
                    className="mt-0.5 text-[16px] text-ink-faint transition-colors group-hover:text-seal"
                  >
                    →
                  </span>
                </Link>
              )
            })}
          </div>
        </div>

        <div className="mt-8">
          <div className="eyebrow">Defined in the product, not built in this prototype</div>
          <div className="mt-3 divide-y divide-rule overflow-hidden rounded-[3px] border border-dashed border-rule-strong bg-[#fbfcfc]">
            {UNBUILT_ROLES.map((role) => (
              <div key={role.label} className="flex items-start gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium text-ink-muted">{role.label}</div>
                  <div className="mt-0.5 text-[12px] text-ink-faint">{role.summary}</div>
                </div>
                <span className="mt-0.5 shrink-0 rounded-[2px] border border-rule-strong px-1.5 py-px text-[10px] tracking-wide text-ink-faint uppercase">
                  Not built
                </span>
              </div>
            ))}
          </div>
        </div>

        <p className="mt-8 border-t border-rule pt-4 text-[11.5px] leading-relaxed text-ink-faint">
          Prototype build. Every record shown is synthetic, and no screen reflects live MPLADS data
          or a real assessment of any Member, agency or officer.
        </p>
      </div>
    </div>
  )
}
