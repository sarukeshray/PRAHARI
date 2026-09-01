import { Navigate, Route, Routes } from 'react-router-dom'

import type { RoleKey } from '@/api/types'
import { AppShell } from '@/components/AppShell'
import { Loading } from '@/components/ui-kit'
import { ROLE_HOME, useSession } from '@/lib/session'
import { Backtest } from '@/pages/district/Backtest'
import { DistrictMap } from '@/pages/district/DistrictMap'
import { HandoverQueue } from '@/pages/district/HandoverQueue'
import { ReviewQueue } from '@/pages/district/ReviewQueue'
import { Submissions } from '@/pages/district/Submissions'
import { Trends } from '@/pages/district/Trends'
import { WorkDetail } from '@/pages/district/WorkDetail'
import { Landing } from '@/pages/Landing'
import {
  MinistryEscalations,
  MinistryOverview,
  MinistryThresholds,
} from '@/pages/ministry/MinistryDashboard'
import { MPEntitlement, MPRecommend, MPWorks } from '@/pages/mp/MPDashboard'
import {
  AgencyFindings,
  AgencyPerformanceScreen,
  AgencyWorks,
  PublicView,
  StateEscalations,
  StateOverview,
  UserAgencyAssets,
  UserAgencyMaintenance,
} from '@/pages/roles/OtherRoles'
import { SignIn } from '@/pages/SignIn'

/**
 * A screen is only reachable by the role it belongs to.
 *
 * This mirrors the API rather than replacing it: the server refuses regardless.
 * Guarding here keeps a signed-in user from landing on a page that would only
 * show them an error.
 */
function RoleRoute({ allow, children }: { allow: RoleKey[]; children: React.ReactNode }) {
  const { me, isResolving, isAnonymous } = useSession()

  // Order matters. Redirecting while the identity is still in flight is what
  // sent every role to whichever dashboard was cached from the last sign-in.
  if (isAnonymous) return <Navigate to="/signin" replace />
  if (isResolving || !me) return <Loading rows={6} label="Checking your sign-in" />
  if (!allow.includes(me.role)) return <Navigate to={ROLE_HOME[me.role]} replace />

  return <AppShell>{children}</AppShell>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/public" element={<PublicView />} />

      {/* District Authority */}
      <Route
        path="/district"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <ReviewQueue />
          </RoleRoute>
        }
      />
      <Route
        path="/district/works/:workId"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <WorkDetail />
          </RoleRoute>
        }
      />
      <Route
        path="/district/handovers"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <HandoverQueue />
          </RoleRoute>
        }
      />
      <Route
        path="/district/submissions"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <Submissions />
          </RoleRoute>
        }
      />
      <Route
        path="/district/map"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <DistrictMap />
          </RoleRoute>
        }
      />
      <Route
        path="/district/trends"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <Trends />
          </RoleRoute>
        }
      />
      <Route
        path="/district/backtest"
        element={
          <RoleRoute allow={['DISTRICT_AUTHORITY']}>
            <Backtest />
          </RoleRoute>
        }
      />

      {/* Member of Parliament */}
      <Route
        path="/mp"
        element={
          <RoleRoute allow={['MP']}>
            <MPEntitlement />
          </RoleRoute>
        }
      />
      <Route
        path="/mp/works"
        element={
          <RoleRoute allow={['MP']}>
            <MPWorks />
          </RoleRoute>
        }
      />
      <Route
        path="/mp/recommend"
        element={
          <RoleRoute allow={['MP']}>
            <MPRecommend />
          </RoleRoute>
        }
      />

      {/* Ministry */}
      <Route
        path="/ministry"
        element={
          <RoleRoute allow={['MINISTRY']}>
            <MinistryOverview />
          </RoleRoute>
        }
      />
      <Route
        path="/ministry/escalations"
        element={
          <RoleRoute allow={['MINISTRY']}>
            <MinistryEscalations />
          </RoleRoute>
        }
      />
      <Route
        path="/ministry/thresholds"
        element={
          <RoleRoute allow={['MINISTRY']}>
            <MinistryThresholds />
          </RoleRoute>
        }
      />

      {/* State Nodal Authority */}
      <Route
        path="/state"
        element={
          <RoleRoute allow={['STATE_NODAL']}>
            <StateOverview />
          </RoleRoute>
        }
      />
      <Route
        path="/state/escalations"
        element={
          <RoleRoute allow={['STATE_NODAL']}>
            <StateEscalations />
          </RoleRoute>
        }
      />

      {/* Implementing Agency */}
      <Route
        path="/agency"
        element={
          <RoleRoute allow={['IMPLEMENTING_AGENCY']}>
            <AgencyWorks />
          </RoleRoute>
        }
      />
      <Route
        path="/agency/findings"
        element={
          <RoleRoute allow={['IMPLEMENTING_AGENCY']}>
            <AgencyFindings />
          </RoleRoute>
        }
      />
      <Route
        path="/agency/performance"
        element={
          <RoleRoute allow={['IMPLEMENTING_AGENCY']}>
            <AgencyPerformanceScreen />
          </RoleRoute>
        }
      />

      {/* User Agency */}
      <Route
        path="/user-agency"
        element={
          <RoleRoute allow={['USER_AGENCY']}>
            <UserAgencyAssets />
          </RoleRoute>
        }
      />
      <Route
        path="/user-agency/maintenance"
        element={
          <RoleRoute allow={['USER_AGENCY']}>
            <UserAgencyMaintenance />
          </RoleRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
