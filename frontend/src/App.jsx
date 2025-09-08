import React, { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AuthProvider, useToken } from './lib/auth'
import { fetchJSON } from './lib/api'
import { FceChart, TempChart } from './components/Charts'
import { useAuth0 } from '@auth0/auth0-react'

function Dashboard() {
  const CLAMP_END_ISO = '2025-09-07'
  const CLAMP_END = useMemo(()=> new Date(CLAMP_END_ISO), [])
  const today = useMemo(()=> {
    const t = new Date()
    return t > CLAMP_END ? new Date(CLAMP_END) : t
  }, [CLAMP_END])
  const startDefault = new Date(today); startDefault.setMonth(today.getMonth()-3)
  const [start, setStart] = useState(startDefault.toISOString().slice(0,10))
  const [end, setEnd] = useState(today.toISOString().slice(0,10))
  const [site, setSite] = useState('Marlborough Sounds')
  const getToken = useToken()

  // Helper to thin data for charts when needed
  const thin = (arr, maxPoints = 300) => {
    if (!arr || arr.length <= maxPoints) return arr || []
    const step = Math.ceil(arr.length / maxPoints)
    const out = []
    for (let i = 0; i < arr.length; i += step) out.push(arr[i])
    return out
  }

  // Chart data: use aggregated endpoint for large ranges; fallback to daily on 404
  const { data: chartData, isLoading: isLoadingChart, error: chartError, refetch: refetchChart } = useQuery({
    queryKey: ['chartData', start, end, site],
    queryFn: async () => {
      const token = await getToken()
      const startDate = new Date(start)
      const endDate = new Date(end)
      const spanDays = Math.max(1, Math.round((endDate - startDate) / 86400000) + 1)
      try {
        if (spanDays > 60) {
          // Request ~200 points for smoothness
          return await fetchJSON(`/api/metrics/aggregated?start=${start}&end=${end}&site=${encodeURIComponent(site)}&points=200`, token)
        }
      } catch (e) {
        // If aggregated not available, fall back to daily
      }
      return fetchJSON(`/api/metrics?start=${start}&end=${end}&site=${encodeURIComponent(site)}`, token)
    }
  })

  // Table data: always last 14 days based on current end date
  const { data: tableData } = useQuery({
    queryKey: ['tableData', end, site],
    queryFn: async () => {
      const token = await getToken()
      const endDate = new Date(end)
      const start14 = new Date(endDate)
      start14.setDate(start14.getDate() - 13)
      const s = start14.toISOString().slice(0,10)
      const e = endDate.toISOString().slice(0,10)
      return fetchJSON(`/api/metrics?start=${s}&end=${e}&site=${encodeURIComponent(site)}`, token)
    },
    enabled: !!end
  })

  // Auto-align: fetch latest and set end/start to [min(latest, CLAMP_END) - 90d, min(latest, CLAMP_END)]
  useEffect(() => {
    (async () => {
      try {
        const token = await getToken()
        const latest = await fetchJSON(`/api/metrics/latest?site=${encodeURIComponent(site)}`, token)
        if (latest?.date) {
          const endDateRaw = new Date(latest.date)
          const endDate = endDateRaw > CLAMP_END ? new Date(CLAMP_END) : endDateRaw
          const startDate = new Date(endDate)
          startDate.setDate(startDate.getDate() - 90)
          const newEnd = endDate.toISOString().slice(0,10)
          const newStart = startDate.toISOString().slice(0,10)
          if (newEnd !== end || newStart !== start) {
            setEnd(newEnd)
            setStart(newStart)
          }
        }
      } catch {}
    })()
  // only on mount or when site changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site])

  const { loginWithRedirect, logout, isAuthenticated } = useAuth0()

  return (
    <div className="max-w-7xl mx-auto px-3 sm:px-5 py-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Salmon FCE Demo</h1>
        <div className="space-x-2">
          {isAuthenticated ? (
            <button className="px-3 py-1.5 rounded bg-gray-200 hover:bg-gray-300" onClick={()=>logout({ logoutParams: { returnTo: window.location.origin }})}>Logout</button>
          ) : (
            <button className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700" onClick={()=>loginWithRedirect()}>Login</button>
          )}
        </div>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <label className="flex flex-col text-sm">Start
          <input className="mt-1 border rounded p-2" type="date" value={start} max={CLAMP_END_ISO} onChange={e=>setStart(e.target.value)} />
        </label>
        <label className="flex flex-col text-sm">End
          <input className="mt-1 border rounded p-2" type="date" value={end} max={CLAMP_END_ISO} onChange={e=>setEnd(e.target.value)} />
        </label>
        <label className="flex flex-col text-sm md:col-span-2">Site
          <input className="mt-1 border rounded p-2" value={site} onChange={e=>setSite(e.target.value)} />
        </label>
      </section>

      <div className="flex gap-2 mb-6">
        <button className="px-3 py-1.5 rounded bg-gray-2 00 hover:bg-gray-300" onClick={()=>{ refetchChart() }}>Refresh</button>
        <button className="px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200" onClick={()=>{ const d=new Date(end); const s=new Date(d); s.setDate(s.getDate()-30); setStart(s.toISOString().slice(0,10)); }}>Last 30d</button>
        <button className="px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200" onClick={()=>{ const d=new Date(end); const s=new Date(d); s.setDate(s.getDate()-90); setStart(s.toISOString().slice(0,10)); }}>Last 90d</button>
        <button className="px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200" onClick={()=>{ const d=new Date(end); const s=new Date(d); s.setDate(s.getDate()-180); setStart(s.toISOString().slice(0,10)); }}>Last 180d</button>
      </div>

      {isLoadingChart && <p className="text-sm text-gray-600">Loading…</p>}
      {chartError && <p className="text-sm text-red-600">Error: {String(chartError)}</p>}

      {chartData && chartData.length>0 && (
        <>
          <div className="grid gap-6">
            <div className="bg-white shadow rounded p-4">
              <h2 className="font-medium mb-2">Feed Conversion Efficiency (FCE)</h2>
              <FceChart data={thin(chartData)} />
            </div>
            <div className="bg-white shadow rounded p-4">
              <h2 className="font-medium mb-2">Average Temperature (°C)</h2>
              <TempChart data={thin(chartData)} />
            </div>
          </div>

          <div className="bg-white shadow rounded p-4 mt-6 overflow-x-auto">
            <h3 className="font-medium mb-2">Last 14 days</h3>
            <table className="min-w-full text-sm">
              <thead className="text-left text-gray-500">
                <tr><th className="py-2">Date</th><th>FCE</th><th>FCR</th><th>Feed (kg)</th><th>Gain (kg)</th></tr>
              </thead>
              <tbody>
                {(tableData || []).slice(-14).map((r)=> (
                  <tr key={r.date} className="border-t">
                    <td className="py-1.5">{r.date}</td><td>{r.fce}</td><td>{r.fcr}</td><td>{r.feed_given_kg}</td><td>{r.biomass_gain_kg}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

export default function App(){
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  )
}

