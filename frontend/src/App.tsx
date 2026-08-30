import { useQuery } from '@tanstack/react-query'

import { apiGet, type HealthResponse } from '@/api/client'
import { SyntheticDataBadge } from '@/components/SyntheticDataBadge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function App() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet<HealthResponse>('/health'),
  })

  return (
    <div className="min-h-screen bg-background">
      <SyntheticDataBadge />

      <header className="border-b px-6 py-3">
        <h1 className="text-base font-semibold tracking-tight">PRAHARI</h1>
        <p className="text-xs text-muted-foreground">
          Preventive oversight screening — MPLAD Scheme
        </p>
      </header>

      <main className="p-6">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-sm">Scaffold status</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {health.isPending && <p className="text-muted-foreground">Contacting API…</p>}
            {health.isError && (
              <p className="text-severity-high">API unreachable — is uvicorn running on :8000?</p>
            )}
            {health.data && (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                <dt className="text-muted-foreground">API</dt>
                <dd>{health.data.status}</dd>
                <dt className="text-muted-foreground">Engine</dt>
                <dd>v{health.data.engine_version}</dd>
                <dt className="text-muted-foreground">Database</dt>
                <dd>{health.data.db_backend}</dd>
              </dl>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
