import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/AppShell'
import { ReviewProvider } from '@/lib/reviewStore'
import { Backtest } from '@/pages/district/Backtest'
import { DistrictMap } from '@/pages/district/DistrictMap'
import { ReviewQueue } from '@/pages/district/ReviewQueue'
import { Trends } from '@/pages/district/Trends'
import { WorkDetail } from '@/pages/district/WorkDetail'
import { MinistryOverview } from '@/pages/ministry/MinistryOverview'
import { MPOverview } from '@/pages/mp/MPOverview'
import { RoleSelect } from '@/pages/RoleSelect'

export default function App() {
  return (
    <ReviewProvider>
      <Routes>
        <Route path="/" element={<RoleSelect />} />

        <Route
          path="/district"
          element={
            <AppShell role="district">
              <ReviewQueue />
            </AppShell>
          }
        />
        <Route
          path="/district/works/:workId"
          element={
            <AppShell role="district">
              <WorkDetail />
            </AppShell>
          }
        />
        <Route
          path="/district/map"
          element={
            <AppShell role="district">
              <DistrictMap />
            </AppShell>
          }
        />
        <Route
          path="/district/trends"
          element={
            <AppShell role="district">
              <Trends />
            </AppShell>
          }
        />
        <Route
          path="/district/backtest"
          element={
            <AppShell role="district">
              <Backtest />
            </AppShell>
          }
        />

        <Route
          path="/mp"
          element={
            <AppShell role="mp">
              <MPOverview />
            </AppShell>
          }
        />
        <Route
          path="/ministry"
          element={
            <AppShell role="ministry">
              <MinistryOverview />
            </AppShell>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ReviewProvider>
  )
}
