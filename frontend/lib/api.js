/**
 * API helper — all backend calls route through here.
 * In production: NEXT_PUBLIC_BACKEND_URL points to Railway/Render
 * In dev: falls back to localhost:8000
 */

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function apiGet(path, params = {}) {
  const url = new URL(`${BACKEND}${path}`)
  Object.entries(params).forEach(([k, v]) => v !== undefined && url.searchParams.set(k, v))
  const res = await fetch(url.toString(), { cache: 'no-store' })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

export async function apiPost(path, body = {}) {
  const res = await fetch(`${BACKEND}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || `POST ${path} failed: ${res.status}`)
  }
  return res.json()
}

export async function apiDelete(path) {
  const res = await fetch(`${BACKEND}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
  return res.json()
}

export function backendUrl(path) {
  return `${BACKEND}${path}`
}
