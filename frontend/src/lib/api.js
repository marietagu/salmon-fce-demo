// Prefer build-time env, then optional runtime override, then localhost fallback
const runtimeBase = (typeof window !== 'undefined' && window.__API_BASE__) || undefined
const envBase = import.meta.env.VITE_API_BASE_URL
const rawBase = runtimeBase || envBase || 'http://localhost:8000'
export const API_BASE = String(rawBase).replace(/\/$/, '')

if (!runtimeBase && !envBase) {
  // eslint-disable-next-line no-console
  console.warn('[api] Using fallback API_BASE:', API_BASE)
}

export async function fetchJSON(path) {
  const urlPath = path.startsWith('/') ? path : `/${path}`
  const res = await fetch(`${API_BASE}${urlPath}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

