/** Thin fetch wrapper around the PRAHARI API.  Requests are proxied to :8000 in dev. */

const BASE = '/api/v1'

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export interface HealthResponse {
  status: string
  engine_version: string
  db_backend: string
  data_notice: string
}
