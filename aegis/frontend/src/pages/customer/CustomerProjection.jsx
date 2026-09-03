import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend
} from 'recharts'
import { getMLProjection } from '../../api/client.js'
import { PageSpinner } from '../../components/Spinner.jsx'
import Card, { CardHeader } from '../../components/Card.jsx'
import StatCard from '../../components/StatCard.jsx'
import { ChartIcon, WarnIcon, CheckIcon } from '../../components/Icons.jsx'

const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const val = payload[0]?.value ?? 0
  const color = val < 0 ? '#ef4444' : '#6366f1'
  return (
    <div className="glass rounded-xl px-4 py-3 text-sm border border-border shadow-lg">
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="font-bold" style={{ color }}>{fmt(val)}</p>
    </div>
  )
}

export default function CustomerProjection() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const uid = localStorage.getItem('aegis_uid')

  useEffect(() => {
    getMLProjection(uid).then(setData).finally(() => setLoading(false))
  }, [uid])

  if (loading) return <PageSpinner />
  if (!data)   return <div className="text-danger text-center py-20">Failed to load projection.</div>

  // Build chart data from daily_trajectory or fall back to 3 points
  const trajectory = data.daily_trajectory || []
  const chartData = trajectory.length > 0
    ? trajectory.map((bal, i) => ({ day: `Day ${i + 1}`, balance: bal }))
    : [
        { day: 'Today',  balance: data.current_balance        || data.projections?.day_30 || 0 },
        { day: 'Day 30', balance: data.projections?.day_30    || data.day_30 || 0 },
        { day: 'Day 60', balance: data.projections?.day_60    || data.day_60 || 0 },
        { day: 'Day 90', balance: data.projections?.day_90    || data.day_90 || 0 },
      ]

  const proj     = data.projections || {}
  const day30    = proj.day_30 ?? data.day_30 ?? 0
  const day60    = proj.day_60 ?? data.day_60 ?? 0
  const day90    = proj.day_90 ?? data.day_90 ?? 0
  const current  = data.current_balance ?? 0
  const trend    = data.risk_trend || (day90 > current ? 'improving' : day90 < current ? 'deteriorating' : 'stable')
  const trendColor = trend === 'improving' ? 'success' : trend === 'deteriorating' ? 'danger' : 'blue'
  const hasDefault = data.estimated_default_day != null

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold">Cashflow Projection</h1>
        <p className="text-slate-400 text-sm mt-0.5">30 · 60 · 90 day balance forecast for <span className="font-mono text-aegis-300">{uid}</span></p>
      </motion.div>

      {/* Stat row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Current Balance"    value={fmt(current)} color="aegis"   icon={<ChartIcon className="w-4 h-4"/>} />
        <StatCard label="Day 30 Projection"  value={fmt(day30)}   color={day30 < 0 ? 'danger' : 'success'} />
        <StatCard label="Day 60 Projection"  value={fmt(day60)}   color={day60 < 0 ? 'danger' : 'blue'} />
        <StatCard label="Day 90 Projection"  value={fmt(day90)}   color={day90 < 0 ? 'danger' : 'success'} />
      </div>

      {/* Default warning */}
      {hasDefault && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="glass border border-danger/40 rounded-2xl p-4 flex items-start gap-3 bg-danger/5"
        >
          <WarnIcon className="w-5 h-5 text-danger flex-shrink-0" />
          <div>
            <p className="font-semibold text-danger">Default Risk Detected</p>
            <p className="text-sm text-slate-300 mt-0.5">
              At the current burn rate, your balance is projected to reach zero in{' '}
              <span className="font-bold text-danger">{data.estimated_default_day} days</span>.
              Consider requesting an adaptive repayment plan.
            </p>
          </div>
        </motion.div>
      )}

      {/* Chart */}
      <Card className="p-6">
        <CardHeader
          title="Balance Trajectory"
          subtitle={`Trend: ${trend}`}
          icon={<ChartIcon className="w-4 h-4" />}
          action={
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium
              ${trend === 'improving' ? 'bg-success/10 text-success border border-success/30'
              : trend === 'deteriorating' ? 'bg-danger/10 text-danger border border-danger/30'
              : 'bg-blue-500/10 text-blue-400 border border-blue-500/30'}`}>
              {trend}
            </span>
          }
        />
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="balGradRed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a45" />
              <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }}
                     tickLine={false} axisLine={false}
                     interval={Math.floor(chartData.length / 5)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }}
                     tickLine={false} axisLine={false}
                     tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.6} label={{ value: 'Zero', fill: '#ef4444', fontSize: 10 }} />
              <Area type="monotone" dataKey="balance" name="Balance"
                    stroke="#6366f1" strokeWidth={2}
                    fill="url(#balGrad)" dot={false} activeDot={{ r: 4, fill: '#6366f1' }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Metrics row */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Card className="p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Daily Income</p>
          <p className="text-xl font-bold text-white">{fmt(data.avg_daily_income)}</p>
          <p className="text-xs text-slate-500 mt-1">avg per day</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Daily Burn</p>
          <p className="text-xl font-bold text-danger">{fmt(data.avg_daily_burn)}</p>
          <p className="text-xs text-slate-500 mt-1">avg per day</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Net Daily Flow</p>
          <p className={`text-xl font-bold ${(data.net_daily_flow ?? 0) >= 0 ? 'text-success' : 'text-danger'}`}>
            {fmt(data.net_daily_flow)}
          </p>
          <div className="flex items-center gap-1 mt-1">
            {(data.net_daily_flow ?? 0) >= 0
              ? <CheckIcon className="w-3 h-3 text-success" />
              : <WarnIcon className="w-3 h-3 text-danger" />}
            <span className="text-xs text-slate-500">{(data.net_daily_flow ?? 0) >= 0 ? 'positive' : 'negative'} cashflow</span>
          </div>
        </Card>
      </div>
    </div>
  )
}
