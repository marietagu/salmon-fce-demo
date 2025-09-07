import React from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'

export function FceChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d)=>d.slice(5)} />
        <YAxis yAxisId="left" />
        <Tooltip />
        <Legend />
        <Line yAxisId="left" type="monotone" dataKey="fce" name="FCE" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function TempChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d)=>d.slice(5)} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="avg_temperature_C" name="Avg Temp (°C)" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

