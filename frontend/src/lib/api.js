// Prefer build-time var, then optional runtime override, then ACA URL, then localhost
export const API_BASE =
  (typeof window !== 'undefined' && window.__API_BASE__) ||
  import.meta.env.VITE_API_BASE_URL ||
  'https://fce-api.gentlesky-fa6c425e.westeurope.azurecontainerapps.io' ||
  'http://localhost:8000'

export async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

