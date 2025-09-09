import React, { useEffect, useMemo, useState, Suspense, lazy } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchJSON } from './lib/api'

// Lazy load charts to reduce initial bundle size
const LazyCharts = lazy(() => import('./components/Charts'))

// Loading skeleton for charts
const ChartSkeleton = () => (
  <div className="animate-pulse">
    <div className="h-[300px] bg-gray-200 rounded"></div>
  </div>
)

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
  // No auth: all API endpoints are public

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
      const startDate = new Date(start)
      const endDate = new Date(end)
      const spanDays = Math.max(1, Math.round((endDate - startDate) / 86400000) + 1)
      try {
        if (spanDays > 60) {
          // Request ~200 points for smoothness
          return await fetchJSON(`/api/metrics/aggregated?start=${start}&end=${end}&site=${encodeURIComponent(site)}&points=200`)
        }
      } catch (e) {
        // If aggregated not available, fall back to daily
      }
      return fetchJSON(`/api/metrics?start=${start}&end=${end}&site=${encodeURIComponent(site)}`)
    }
  })

  // Table data: always last 14 days based on current end date
  const { data: tableData } = useQuery({
    queryKey: ['tableData', end, site],
    queryFn: async () => {
      const endDate = new Date(end)
      const start14 = new Date(endDate)
      start14.setDate(start14.getDate() - 13)
      const s = start14.toISOString().slice(0,10)
      const e = endDate.toISOString().slice(0,10)
      return fetchJSON(`/api/metrics?start=${s}&end=${e}&site=${encodeURIComponent(site)}`)
    },
    enabled: !!end
  })

  // Auto-align: fetch latest and set end/start to [min(latest, CLAMP_END) - 90d, min(latest, CLAMP_END)]
  const { data: latestData } = useQuery({
    queryKey: ['latest', site],
    queryFn: () => fetchJSON(`/api/metrics/latest?site=${encodeURIComponent(site)}`),
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  })

  useEffect(() => {
    if (latestData?.date) {
      const endDateRaw = new Date(latestData.date)
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
  }, [latestData, end, start, CLAMP_END])

  return (
    <div className="max-w-7xl mx-auto px-3 sm:px-5 py-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Salmon FCE Demo</h1>
        <div className="space-x-2" />
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

      {/* Always show chart containers for better UX */}
      <div className="grid gap-6">
        <div className="bg-white shadow rounded p-4">
          <h2 className="font-medium mb-2">Feed Conversion Efficiency (FCE)</h2>
          {isLoadingChart ? (
            <ChartSkeleton />
          ) : chartError ? (
            <div className="h-[300px] flex items-center justify-center text-red-600">
              Error loading chart: {String(chartError)}
            </div>
          ) : chartData && chartData.length > 0 ? (
            <Suspense fallback={<ChartSkeleton />}>
              <LazyCharts type="fce" data={thin(chartData)} />
            </Suspense>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No data available
            </div>
          )}
        </div>
        
        <div className="bg-white shadow rounded p-4">
          <h2 className="font-medium mb-2">Average Temperature (°C)</h2>
          {isLoadingChart ? (
            <ChartSkeleton />
          ) : chartError ? (
            <div className="h-[300px] flex items-center justify-center text-red-600">
              Error loading chart: {String(chartError)}
            </div>
          ) : chartData && chartData.length > 0 ? (
            <Suspense fallback={<ChartSkeleton />}>
              <LazyCharts type="temp" data={thin(chartData)} />
            </Suspense>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No data available
            </div>
          )}
        </div>
      </div>

      <div className="bg-white shadow rounded p-4 mt-6 overflow-x-auto">
        <h3 className="font-medium mb-2">Last 14 days</h3>
        {!tableData ? (
          <div className="animate-pulse space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded"></div>
            ))}
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr><th className="py-2">Date</th><th>FCE</th><th>FCR</th><th>Feed (kg)</th><th>Gain (kg)</th></tr>
            </thead>
            <tbody>
              {tableData.slice(-14).map((r)=> (
                <tr key={r.date} className="border-t">
                  <td className="py-1.5">{r.date}</td><td>{r.fce}</td><td>{r.fcr}</td><td>{r.feed_given_kg}</td><td>{r.biomass_gain_kg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default function App(){
  return (
    <Dashboard />
  )
}

