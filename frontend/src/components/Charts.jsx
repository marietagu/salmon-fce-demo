import React from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, Brush } from 'recharts'

export function FceChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 10, right: 80, bottom: 40, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d)=>d.slice(5)} tick={{ fontSize: 12 }} tickMargin={12} padding={{ left: 24, right: 48 }} interval="preserveStartEnd" />
        <YAxis yAxisId="left" tick={{ fontSize: 12 }} width={56} />
        <Tooltip />
        <Legend />
        <Line stroke="#2563eb" strokeWidth={2} yAxisId="left" type="monotone" dataKey="fce" name="FCE" dot={false} />
        <Brush dataKey="date" height={24} stroke="#9ca3af" travellerWidth={12} tickFormatter={(d)=>d.slice(5)} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function TempChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 10, right: 80, bottom: 40, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d)=>d.slice(5)} tick={{ fontSize: 12 }} tickMargin={12} padding={{ left: 24, right: 48 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 12 }} width={56} />
        <Tooltip />
        <Legend />
        <Line stroke="#16a34a" strokeWidth={2} type="monotone" dataKey="avg_temperature_C" name="Avg Temp (°C)" dot={false} />
        <Brush dataKey="date" height={24} stroke="#9ca3af" travellerWidth={12} tickFormatter={(d)=>d.slice(5)} />
      </LineChart>
    </ResponsiveContainer>
  )
}

