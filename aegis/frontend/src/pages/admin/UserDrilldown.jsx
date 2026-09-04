import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts'
import {
  getMLAssessment, getMLProjection,
  getAnomalies, getSurvivalBuffer
} from '../../api/client.js'
import Navbar    from '../../components/Navbar.jsx'
import OxygenGauge from '../../components/OxygenGauge.jsx'
import RiskBadge from '../../components/RiskBadge.jsx'
import Card, { CardHeader } from '../../components/Card.jsx'
import DemoBanner from '../../components/DemoBanner.jsx'
import { PageSpinner } from '../../components/Spinner.jsx'
import { ArrowRightIcon, AlertIcon, ChartIcon, ShieldIcon, UserIcon, WarnIcon } from '../../components/Icons.jsx'

const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

export default function UserDrilldown() {
  const { userId } = useParams()
  const nav = useNavigate()

  const [assess,   setAssess]   = useState(null)
  const [proj,     setProj]     = useState(null)
  const [anom,     setAnom]     = useState(null)
  const [buf,      setBuf]      = useState(null)
  const [isDemo,   setIsDemo]   = useState(false)
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    Promise.allSettled([
      getMLAssessment(userId),
      getMLProjection(userId),
      getAnomalies(userId),
      getSurvivalBuffer(userId),
    ]).then(([a, p, an, b]) => {
      if (a.status === 'fulfilled') setAssess(a.value.data)
      if (p.status === 'fulfilled') setProj(p.value.data)
      if (an.status === 'fulfilled') setAnom(an.value.data)
      if (b.status === 'fulfilled') setBuf(b.value.data)
      const anyDemo = [a, p, an, b].some(r => r.status === 'fulfilled' && r.value.isDemo)
      setIsDemo(anyDemo)
    }).finally(() => setLoading(false))
  }, [userId])

  if (loading) return (
    <div className="min-h-screen bg-[#f8f8fc] bg-grid">
      <Navbar role="admin" />
      <PageSpinner />
    </div>
  )

  // Build trajectory chart data
  const trajectory = proj?.daily_trajectory || []
  const chartData = trajectory.length > 0
    ? trajectory.slice(0, 90).map((bal, i) => ({ day: `D${i+1}`, balance: bal }))
    : [
        { day: 'Now',    balance: proj?.current_balance || 0 },
        { day: 'Day 30', balance: proj?.projections?.day_30 || proj?.day_30 || 0 },
        { day: 'Day 60', balance: proj?.projections?.day_60 || proj?.day_60 || 0 },
        { day: 'Day 90', balance: proj?.projections?.day_90 || proj?.day_90 || 0 },
      ]

  // Radar chart from component scores
  const compScores = assess?.component_scores || {}
  const radarData = Object.entries(compScores).map(([key, val]) => ({
    subject: key.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase()),
    score: Math.round(val.weighted || 0),
    fullMark: 40,
  }))

  const profile    = assess?.profile      || {}
  const riskScore  = assess?.risk_score   || assess?.financial_oxygen_score
  const oxyScore   = assess?.risk_score != null ? Math.max(0, 100 - assess.risk_score) : (assess?.financial_oxygen_score ?? 50)
  const riskTier   = assess?.risk_tier    || assess?.risk_status
  const anomalies  = anom?.anomalies || []

  return (
    <div className="min-h-screen bg-[#f8f8fc] bg-grid">
      <Navbar role="admin" />

      <main className="max-w-7xl mx-auto px-4 py-8 relative z-10 space-y-6">
        {isDemo && <DemoBanner label={`user ${userId}`} />}
        {/* Back + header */}
        <div className="flex items-center gap-4">
          <button onClick={() => nav('/admin')} className="btn-ghost text-sm py-1.5 flex items-center gap-2">
            ← Portfolio
          </button>
          <div className="h-4 w-px bg-border" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {profile.name || assess?.name || userId}
            </h1>
            <p className="text-xs font-mono text-slate-400">{userId}</p>
          </div>
          {riskTier && <RiskBadge status={riskTier} size="lg" pulse={riskTier === 'Critical' || riskTier === 'critical'} />}
        </div>

        {/* Profile + gauge row */}
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Gauge */}
          <Card className="p-6 flex flex-col items-center justify-center gap-4">
            <OxygenGauge score={Math.round(oxyScore)} size={160} />
            {riskScore != null && (
              <div className="text-center">
                <p className="text-xs text-slate-400">Risk Score</p>
                <p className="text-2xl font-bold text-slate-900">{Math.round(riskScore)}<span className="text-slate-500 text-sm">/100</span></p>
              </div>
            )}
          </Card>

          {/* Profile stats */}
          <div className="lg:col-span-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { label: 'Monthly Income',    value: fmt(profile.monthly_income || assess?.monthly_income)   },
              { label: 'Age',               value: profile.age ? `${profile.age} yrs` : '—'               },
              { label: 'City',              value: profile.city || '—'                                     },
              { label: 'Occupation',        value: profile.occupation || '—'                               },
              { label: 'Current Balance',   value: fmt(assess?.projection?.current_balance || proj?.current_balance) },
              { label: 'Monthly Expenses',  value: fmt(assess?.monthly_expenses || buf?.total_monthly_essential) },
            ].map(s => (
              <Card key={s.label} className="p-4">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{s.label}</p>
                <p className="font-semibold text-slate-900">{s.value}</p>
              </Card>
            ))}
          </div>
        </div>

        {/* Risk factors */}
        {assess?.top_risk_factors?.length > 0 && (
          <Card className="p-5">
            <CardHeader title="Top Risk Factors" icon={<WarnIcon className="w-4 h-4"/>} />
            <div className="flex flex-wrap gap-2">
              {assess.top_risk_factors.map((rf, i) => (
                <span key={i} className="text-xs bg-danger/10 border border-danger/25 text-danger/90 px-3 py-1.5 rounded-full">
                  ⚠ {rf}
                </span>
              ))}
            </div>
          </Card>
        )}

        {/* Projection chart + radar */}
        <div className="grid lg:grid-cols-5 gap-6">
          <Card className="p-5 lg:col-span-3">
            <CardHeader title="90-Day Balance Projection" icon={<ChartIcon className="w-4 h-4"/>} />
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="aGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a45" />
                  <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false}
                         interval={Math.floor(chartData.length / 5)} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false}
                         tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => [fmt(v), 'Balance']}
                           contentStyle={{ background: '#ffffff', border: '1px solid #e7e5ef', borderRadius: 12 }} />
                  <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.5} />
                  <Area type="monotone" dataKey="balance" stroke="#6366f1" strokeWidth={2}
                        fill="url(#aGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            {proj?.estimated_default_day && (
              <p className="text-xs text-danger mt-2">
                ⚠ Projected zero balance in <strong>{proj.estimated_default_day} days</strong>
              </p>
            )}
          </Card>

          {/* Component radar */}
          {radarData.length > 0 && (
            <Card className="p-5 lg:col-span-2">
              <CardHeader title="Risk Components" icon={<ShieldIcon className="w-4 h-4"/>} />
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#2a2a45" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 9 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 40]} tick={{ fill: '#64748b', fontSize: 8 }} />
                    <Radar dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}
        </div>

        {/* Survival buffer */}
        {buf && !buf.error && (
          <Card className="p-5">
            <CardHeader title="Survival Buffer" icon={<ShieldIcon className="w-4 h-4"/>} />
            <div className="grid sm:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-slate-400 mb-1">Buffer Required</p>
                <p className="font-bold text-slate-900">{fmt(buf.buffer_amount)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Monthly Essentials</p>
                <p className="font-bold text-slate-900">{fmt(buf.total_monthly_essential)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Coverage</p>
                <p className="font-bold text-slate-900">{buf.buffer_coverage_months} months</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Ring-Fenced</p>
                <p className={`font-bold ${buf.ring_fenced ? 'text-success' : 'text-slate-400'}`}>
                  {buf.ring_fenced ? 'YES' : 'NO'}
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Anomalies */}
        {anomalies.length > 0 && (
          <Card className="p-5">
            <CardHeader title={`${anomalies.length} Transaction Anomalie${anomalies.length > 1 ? 's' : ''}`}
                        icon={<AlertIcon className="w-4 h-4"/>} />
            <div className="space-y-2">
              {anomalies.slice(0, 5).map((a, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className={`w-2 h-2 rounded-full ${
                      a.severity === 'high' ? 'bg-danger' : a.severity === 'medium' ? 'bg-warning' : 'bg-blue-400'
                    }`} />
                    <div>
                      <p className="text-sm text-slate-900 capitalize">{a.category?.replace(/_/g,' ')}</p>
                      <p className="text-xs text-slate-400">{a.date}</p>
                    </div>
                  </div>
                  <span className={`font-bold text-sm ${a.severity === 'high' ? 'text-danger' : 'text-warning'}`}>
                    {fmt(a.amount)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </main>
    </div>
  )
}
