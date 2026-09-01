import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useMemo, useState } from 'react'

import { api } from '@/api/client'
import { getDemoUser, setDemoUser } from '@/api/client'
import type { Me, RoleKey } from '@/api/types'

/**
 * Who is signed in, according to the server.
 *
 * The client never decides its own role. `/me` is the single source of truth for
 * identity and for what the navigation offers, so the interface cannot drift
 * away from what the API will actually permit.
 *
 * The signed-in user id is **React state**, not a module variable. It was a
 * module variable, and that caused a real bug: changing it did not re-render, so
 * a route guard could still read the previous role's identity and redirect
 * there. Every role appeared to sign in as whoever you were last. Keeping it in
 * state means a change to who you are is a change React knows about.
 */

interface SessionValue {
  me: Me | undefined
  /** A credential exists and the server has not answered yet. */
  isResolving: boolean
  /** No credential at all — the caller should send the visitor to sign in. */
  isAnonymous: boolean
  isSignedIn: boolean
  signIn: (demoUserId: string) => Promise<Me>
  signOut: () => void
}

const SessionContext = createContext<SessionValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient()
  const [userId, setUserId] = useState<string | null>(() => getDemoUser())

  // The user id is part of the key, so a cached identity for one role can never
  // be served to another.
  const { data: me, isPending } = useQuery({
    queryKey: ['me', userId],
    queryFn: () => api.get<Me>('/me'),
    enabled: Boolean(userId),
    retry: false,
    staleTime: 5 * 60_000,
  })

  const signIn = useCallback(
    async (demoUserId: string): Promise<Me> => {
      setDemoUser(demoUserId)
      setUserId(demoUserId)
      qc.clear()
      // Resolve the identity here rather than navigating on a timer and hoping.
      // The caller can then route to a role it knows the server agreed to.
      const identity = await api.get<Me>('/me')
      qc.setQueryData(['me', demoUserId], identity)
      return identity
    },
    [qc],
  )

  const signOut = useCallback(() => {
    setDemoUser(null)
    setUserId(null)
    qc.clear()
  }, [qc])

  const value = useMemo<SessionValue>(
    () => ({
      me,
      isResolving: Boolean(userId) && isPending,
      isAnonymous: !userId,
      isSignedIn: Boolean(me),
      signIn,
      signOut,
    }),
    [me, userId, isPending, signIn, signOut],
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
    { to: '/district/submissions', label: 'Citizen submissions' },
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
