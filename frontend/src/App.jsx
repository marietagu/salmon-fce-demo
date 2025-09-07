import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AuthProvider, useToken } from './lib/auth'
import { fetchJSON } from './lib/api'
import { FceChart, TempChart } from './components/Charts'
import { useAuth0 } from '@auth0/auth0-react'

function Dashboard() {
  const today = useMemo(()=> new Date(), [])
  const startDefault = new Date(today); startDefault.setMonth(today.getMonth()-3)
  const [start, setStart] = useState(startDefault.toISOString().slice(0,10))
  const [end, setEnd] = useState(today.toISOString().slice(0,10))
  const [site, setSite] = useState('Marlborough Sounds')
  const getToken = useToken()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['metrics', start, end, site],
    queryFn: async () => {
      const token = await getToken()
      return fetchJSON(`/api/metrics?start=${start}&end=${end}&site=${encodeURIComponent(site)}`, token)
    }
  })

  const { loginWithRedirect, logout, isAuthenticated } = useAuth0()

  return (
    <div style={{ maxWidth: 1000, margin: '20px auto', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <h1>Salmon FCE Demo</h1>
        <div>
          {isAuthenticated ? (
            <button onClick={()=>logout({ logoutParams: { returnTo: window.location.origin }})}>Logout</button>
          ) : (
            <button onClick={()=>loginWithRedirect()}>Login</button>
          )}
        </div>
      </header>

      <section style={{ display:'grid', gap:12, gridTemplateColumns:'1fr 1fr 1fr' }}>
        <label>Start <input type="date" value={start} onChange={e=>setStart(e.target.value)} /></label>
        <label>End <input type="date" value={end} onChange={e=>setEnd(e.target.value)} /></label>
        <label>Site <input value={site} onChange={e=>setSite(e.target.value)} /></label>
      </section>

      <button onClick={()=>refetch()} style={{ marginTop: 10 }}>Refresh</button>

      {isLoading && <p>Loading…</p>}
      {error && <p>Error: {String(error)}</p>}

      {data && data.length>0 && (
        <>
          <FceChart data={data} />
          <TempChart data={data} />
          <table style={{ width: '100%', marginTop: 16 }}>
            <thead><tr><th>Date</th><th>FCE</th><th>FCR</th><th>Feed (kg)</th><th>Gain (kg)</th></tr></thead>
            <tbody>
              {data.slice(-14).map((r)=> (
                <tr key={r.date}><td>{r.date}</td><td>{r.fce}</td><td>{r.fcr}</td><td>{r.feed_given_kg}</td><td>{r.biomass_gain_kg}</td></tr>
              ))}
            </tbody>
          </table>
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

