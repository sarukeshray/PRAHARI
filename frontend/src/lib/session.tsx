import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useMemo } from 'react'

import { getDemoUser, setDemoUser } from '@/api/client'
import { useMe } from '@/api/hooks'
import type { Me, RoleKey } from '@/api/types'

/**
 * Who is signed in, according to the server.
 *
 * The client never decides its own role. `/me` is the single source of truth for
 * both identity and what the navigation should offer, so the interface cannot
 * drift away from what the API will actually permit.
 */

interface SessionValue {
  me: Me | undefined
  isLoading: boolean
  isSignedIn: boolean
  signIn: (demoUserId: string) => void
  signOut: () => void
}

const SessionContext = createContext<SessionValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient()
  const hasCredential = Boolean(getDemoUser())
  const { data: me, isLoading } = useMe(hasCredential)

  const signIn = useCallback(
    (demoUserId: string) => {
      setDemoUser(demoUserId)
      qc.clear()
    },
    [qc],
  )

  const signOut = useCallback(() => {
    setDemoUser(null)
    qc.clear()
  }, [qc])

  const value = useMemo<SessionValue>(
    () => ({
      me,
      isLoading: hasCredential && isLoading,
      isSignedIn: Boolean(me),
      signIn,
      signOut,
    }),
    [me, hasCredential, isLoading, signIn, signOut],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used inside SessionProvider')
  return ctx
}

/** Navigation per role. Labels name what the person does, not what the system stores. */
export const ROLE_NAV: Record<RoleKey, { to: string; label: string; end?: boolean }[]> = {
  DISTRICT_AUTHORITY: [
    { to: '/district', label: 'Review queue', end: true },
    { to: '/district/handovers', label: 'Handover queue' },
    { to: '/district/map', label: 'District map' },
    { to: '/district/trends', label: 'Trends' },
    { to: '/district/backtest', label: 'CAG backtest' },
  ],
  MP: [
    { to: '/mp', label: 'My entitlement', end: true },
    { to: '/mp/works', label: 'My works' },
    { to: '/mp/recommend', label: 'Recommend a work' },
  ],
  MINISTRY: [
    { to: '/ministry', label: 'National overview', end: true },
    { to: '/ministry/escalations', label: 'Escalations' },
    { to: '/ministry/thresholds', label: 'Threshold configuration' },
  ],
  STATE_NODAL: [
    { to: '/state', label: 'State overview', end: true },
    { to: '/state/districts', label: 'District comparison' },
    { to: '/state/escalations', label: 'Escalation queue' },
  ],
  IMPLEMENTING_AGENCY: [
    { to: '/agency', label: 'My works', end: true },
    { to: '/agency/findings', label: 'Findings on my works' },
    { to: '/agency/performance', label: 'My performance' },
  ],
  USER_AGENCY: [
    { to: '/user-agency', label: 'My assets', end: true },
    { to: '/user-agency/maintenance', label: 'Maintenance raised' },
  ],
  PUBLIC: [{ to: '/public', label: 'Scheme overview', end: true }],
}

export const ROLE_LABEL: Record<RoleKey, string> = {
  DISTRICT_AUTHORITY: 'District Authority',
  MP: 'Member of Parliament',
  MINISTRY: 'Ministry (MoSPI)',
  STATE_NODAL: 'State Nodal Authority',
  IMPLEMENTING_AGENCY: 'Implementing Agency',
  USER_AGENCY: 'User Agency',
  PUBLIC: 'Public',
}

export const ROLE_HOME: Record<RoleKey, string> = {
  DISTRICT_AUTHORITY: '/district',
  MP: '/mp',
  MINISTRY: '/ministry',
  STATE_NODAL: '/state',
  IMPLEMENTING_AGENCY: '/agency',
  USER_AGENCY: '/user-agency',
  PUBLIC: '/public',
}
