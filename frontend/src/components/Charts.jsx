import React, { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, Brush } from 'recharts'

function useDateFormatters(data) {
  return useMemo(() => {
    if (!data || data.length === 0) {
      return {
        tickFormatter: (d) => d,
        tooltipLabelFormatter: (d) => d
      }
    }
    const first = new Date(data[0].date)
    const last = new Date(data[data.length - 1].date)
    const days = Math.max(1, Math.round((last - first) / 86400000) + 1)
    // Choose label granularity by span
    if (days <= 31) {
      return {
        tickFormatter: (d) => d.slice(5), // MM-DD
        tooltipLabelFormatter: (d) => d
      }
    }
    if (days <= 180) {
      return {
        tickFormatter: (d) => d.slice(5), // MM-DD
        tooltipLabelFormatter: (d) => d
      }
    }
    // Long ranges: show YYYY-MM
    return {
      tickFormatter: (d) => d.slice(0, 7),
      tooltipLabelFormatter: (d) => d
    }
  }, [data])
}

function FceChart({ data }) {
  const { tickFormatter, tooltipLabelFormatter } = useDateFormatters(data)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 10, right: 80, bottom: 40, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={tickFormatter} tick={{ fontSize: 12 }} tickMargin={12} padding={{ left: 24, right: 48 }} interval="preserveStartEnd" />
        <YAxis yAxisId="left" tick={{ fontSize: 12 }} width={56} />
        <Tooltip labelFormatter={tooltipLabelFormatter} />
        <Legend />
        <Line stroke="#2563eb" strokeWidth={2} yAxisId="left" type="monotone" dataKey="fce" name="FCE" dot={false} isAnimationActive={false} connectNulls />
        <Brush dataKey="date" height={24} stroke="#9ca3af" travellerWidth={12} tickFormatter={tickFormatter} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function TempChart({ data }) {
  const { tickFormatter, tooltipLabelFormatter } = useDateFormatters(data)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 10, right: 80, bottom: 40, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={tickFormatter} tick={{ fontSize: 12 }} tickMargin={12} padding={{ left: 24, right: 48 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 12 }} width={56} />
        <Tooltip labelFormatter={tooltipLabelFormatter} />
        <Legend />
        <Line stroke="#16a34a" strokeWidth={2} type="monotone" dataKey="avg_temperature_C" name="Avg Temp (°C)" dot={false} isAnimationActive={false} connectNulls />
        <Brush dataKey="date" height={24} stroke="#9ca3af" travellerWidth={12} tickFormatter={tickFormatter} />
      </LineChart>
    </ResponsiveContainer>
  )
}

// Main component for lazy loading
export default function Charts({ type, data }) {
  if (type === 'fce') {
    return <FceChart data={data} />
  }
  return <TempChart data={data} />
}

// Also export individual components for backward compatibility
export { FceChart, TempChart }

