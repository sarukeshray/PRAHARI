/**
 * API client.
 *
 * Two sign-in modes, matching the backend. When Firebase is configured the
 * client sends a Bearer ID token; otherwise it sends the demo user header. The
 * backend decides which it will accept — the client just supplies both if it
 * has them, so switching one on does not require changing calling code.
 */

const BASE = '/api/v1'

let demoUserId: string | null = localStorage.getItem('prahari.demoUser')
let idTokenProvider: (() => Promise<string | null>) | null = null

export function setDemoUser(userId: string | null) {
  demoUserId = userId
  if (userId) localStorage.setItem('prahari.demoUser', userId)
  else localStorage.removeItem('prahari.demoUser')
}

export function getDemoUser() {
  return demoUserId
}

export function setIdTokenProvider(fn: (() => Promise<string | null>) | null) {
  idTokenProvider = fn
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function headers(): Promise<HeadersInit> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (demoUserId) h['X-Demo-User'] = demoUserId
  if (idTokenProvider) {
    const token = await idTokenProvider()
    if (token) h.Authorization = `Bearer ${token}`
  }
  return h
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { ...init, headers: await headers() })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      /* the body was not JSON; the status text will have to do */
    }
    throw new ApiError(res.status, detail)
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
}

/** Build a querystring, dropping anything unset so the URL stays readable. */
export function qs(params: Record<string, string | number | boolean | null | undefined>) {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined && v !== '' && v !== 'ALL')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  return parts.length ? `?${parts.join('&')}` : ''
}
