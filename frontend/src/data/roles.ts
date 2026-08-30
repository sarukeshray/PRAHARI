/**
 * The three roles this prototype builds.
 *
 * The product defines six. The other three — State Nodal Authority, Implementing
 * Agency and the public portal — are named on the role screen and marked as not
 * built, rather than shipped as empty shells.
 */

export type RoleKey = 'district' | 'mp' | 'ministry'

interface NavItem {
  to: string
  label: string
  end?: boolean
}

interface RoleConfig {
  key: RoleKey
  label: string
  officer: string
  jurisdiction: string
  summary: string
  nav: NavItem[]
}

export const ROLES: Record<RoleKey, RoleConfig> = {
  district: {
    key: 'district',
    label: 'District Authority',
    officer: 'S. Nair, IAS',
    jurisdiction: 'Udaipur district, Rajasthan',
    summary:
      'Screens every recommendation before sanction, monitors work underway, and decides what each finding warrants.',
    nav: [
      { to: '/district', label: 'Review queue', end: true },
      { to: '/district/map', label: 'District map' },
      { to: '/district/trends', label: 'Trends' },
      { to: '/district/backtest', label: 'CAG backtest' },
    ],
  },
  mp: {
    key: 'mp',
    label: 'Member of Parliament',
    officer: 'Dr. A. Vaishnav',
    jurisdiction: 'Udaipur constituency, Lok Sabha',
    summary:
      'Tracks their own recommendations, entitlement usage and mandated area allocation, with any findings explained in plain language.',
    nav: [{ to: '/mp', label: 'My recommendations', end: true }],
  },
  ministry: {
    key: 'ministry',
    label: 'Ministry (MoSPI)',
    officer: 'DIID Monitoring Cell',
    jurisdiction: 'National',
    summary:
      'Compares states, watches unresolved high-severity findings, and sets the thresholds every district screens against.',
    nav: [{ to: '/ministry', label: 'National overview', end: true }],
  },
}

/** Roles the product defines but this prototype does not build. */
export const UNBUILT_ROLES = [
  {
    label: 'State Nodal Authority',
    summary: 'Aggregated state view, cross-district comparison, escalation queue.',
  },
  {
    label: 'Implementing Agency',
    summary: 'Assigned works, payment status, progress uploads, responses to findings.',
  },
  {
    label: 'Public portal',
    summary: 'Anonymised aggregates only — utilisation and completion rates, no finding details.',
  },
]
