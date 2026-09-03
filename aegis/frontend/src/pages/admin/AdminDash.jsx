import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend
} from 'recharts'
import { getPortfolioSummary, getAtRiskUsers } from '../../api/client.js'
import Navbar    from '../../components/Navbar.jsx'
import StatCard  from '../../components/StatCard.jsx'
import Card, { CardHeader } from '../../components/Card.jsx'
import RiskBadge from '../../components/RiskBadge.jsx'
import { PageSpinner } from '../../components/Spinner.jsx'
import {
  BankIcon, AlertIcon, ChartIcon, UserIcon,
  ShieldIcon, RefreshIcon, ArrowRightIcon
} from '../../components/Icons.jsx'

const fmt  = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`
const fmtN = (n) => Number(n || 0).toLocaleString('en-IN')

const PIE_COLORS = { healthy: '#10b981', at_risk: '#f59e0b', critical: '#ef4444', watch: '#6366f1' }

export default function AdminDash() {
  const [summary,  setSummary]  = useState(null)
  const [atRisk,   setAtRisk]   = useState([])
  const [loading,  setLoading]  = useState(true)
  const [lastSync, setLastSync] = useState(null)
  const nav = useNavigate()

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [s, r] = await Promise.all([getPortfolioSummary(), getAtRiskUsers()])
      setSummary(s)
      setAtRisk(r.users || r)
      setLastSync(new Date())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  if (loading && !summary) return (
    <div className="min-h-screen bg-surface bg-grid">
      <Navbar role="admin" />
      <PageSpinner />
    </div>
  )

  const dist = summary?.risk_distribution || {}
  const pieData = [
    { name: 'Healthy',  value: dist.healthy  || summary?.healthy_count  || 0, fill: PIE_COLORS.healthy  },
    { name: 'Watch',    value:                   summary?.watch_count    || 0, fill: PIE_COLORS.watch    },
    { name: 'At-Risk',  value: dist.at_risk   || summary?.at_risk_count  || 0, fill: PIE_COLORS.at_risk  },
    { name: 'Critical', value: dist.critical  || summary?.critical_count || 0, fill: PIE_COLORS.critical  },
  ].filter(d => d.value > 0)

  const riskPcts   = summary?.risk_percentages || {}
  const loanPort   = summary?.loan_portfolio   || {}
  const alerts     = summary?.alerts           || {}

  return (
    <div className="min-h-screen bg-surface bg-grid">
      <div className="orb w-80 h-80 bg-indigo-700 -top-20 -right-20 opacity-10" />
      <Navbar role="admin" />

      <main className="max-w-7xl mx-auto px-4 py-8 relative z-10 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Portfolio Command Center</h1>
            <p className="text-slate-400 text-sm mt-0.5">
              {lastSync ? `Last sync: ${lastSync.toLocaleTimeString()}` : 'Loading…'}
            </p>
          </div>
          <button onClick={fetchAll} disabled={loading}
            className="btn-ghost flex items-center gap-2 text-sm self-start sm:self-auto">
            <RefreshIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Top KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Users"          value={fmtN(summary?.total_users)}                    icon={<UserIcon  className="w-4 h-4"/>} color="aegis"   loading={loading} />
          <StatCard label="At-Risk + Critical"   value={fmtN((dist.at_risk||0) + (dist.critical||0))}  icon={<AlertIcon className="w-4 h-4"/>} color="warning" loading={loading}
                    sub={`${((riskPcts.at_risk_pct||0) + (riskPcts.critical_pct||0)).toFixed(1)}% of portfolio`} />
          <StatCard label="Defaults Prevented"   value={fmtN(summary?.defaults_prevented ?? alerts.defaults_averted ?? 0)} icon={<ShieldIcon className="w-4 h-4"/>} color="success" loading={loading} />
          <StatCard label="Avg Oxygen Score"     value={(summary?.average_oxygen_score ?? 0).toFixed(1)}                    icon={<ChartIcon  className="w-4 h-4"/>} color="blue"    loading={loading} />
        </div>

        {/* Charts row */}
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Pie chart */}
          <Card className="p-5 lg:col-span-2">
            <CardHeader title="Risk Distribution" icon={<ChartIcon className="w-4 h-4"/>} />
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" paddingAngle={3} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}
                       labelLine={false}>
                    {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [fmtN(v), 'Users']} contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a45', borderRadius: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Bar chart — loan portfolio */}
          <Card className="p-5 lg:col-span-3">
            <CardHeader title="Loan Portfolio Overview" icon={<BankIcon className="w-4 h-4"/>} />
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[
                  { name: 'Total Exposure',    value: loanPort.total_exposure || 0 },
                  { name: 'At-Risk Exposure',  value: loanPort.at_risk_exposure || 0 },
                  { name: 'Monthly EMI',        value: loanPort.total_monthly_emi_collection || 0 },
                ]} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a45" />
                  <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/100000).toFixed(0)}L`} />
                  <Tooltip formatter={(v) => [fmt(v)]} contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a45', borderRadius: 12 }} />
                  <Bar dataKey="value" radius={[6,6,0,0]}>
                    <Cell fill="#6366f1" />
                    <Cell fill="#ef4444" />
                    <Cell fill="#10b981" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Alert metrics row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Missed EMIs"            value={fmtN(alerts.total_missed_emis)}           color="danger"  loading={loading} />
          <StatCard label="Anomalous Transactions" value={fmtN(alerts.anomalous_transactions)}      color="warning" loading={loading} />
          <StatCard label="Need Intervention"      value={fmtN(alerts.users_needing_intervention)}  color="danger"  loading={loading} />
          <StatCard label="Active Interventions"   value={fmtN(summary?.total_active_interventions)} color="aegis"  loading={loading} />
        </div>

        {/* At-risk users table */}
        <Card className="p-5">
          <CardHeader
            title={`At-Risk & Critical Users (${atRisk.length})`}
            icon={<AlertIcon className="w-4 h-4"/>}
            action={
              <span className="text-xs text-slate-500">
                {atRisk.length > 0 ? 'Click any row to investigate' : ''}
              </span>
            }
          />

          {atRisk.length === 0 ? (
            <div className="text-center py-10 text-slate-500">
              No at-risk users detected. Portfolio looks healthy.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-border">
                    <th className="pb-3 pr-4">User</th>
                    <th className="pb-3 pr-4">Status</th>
                    <th className="pb-3 pr-4">Oxygen</th>
                    <th className="pb-3 pr-4">Primary Trigger</th>
                    <th className="pb-3 pr-4">Days in Zone</th>
                    <th className="pb-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {atRisk.map((u, i) => (
                    <motion.tr
                      key={u.user_id}
                      initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
                      onClick={() => nav(`/admin/user/${u.user_id}`)}
                      className="border-b border-border/50 hover:bg-white/[0.02] cursor-pointer transition-colors group"
                    >
                      <td className="py-3 pr-4">
                        <div className="font-medium text-white">{u.name || u.user_id}</div>
                        <div className="text-xs font-mono text-slate-500">{u.user_id}</div>
                      </td>
                      <td className="py-3 pr-4">
                        <RiskBadge status={u.risk_status} pulse={u.risk_status === 'Critical'} />
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${u.financial_oxygen_score}%`,
                                background: u.financial_oxygen_score < 30 ? '#ef4444' : u.financial_oxygen_score < 60 ? '#f59e0b' : '#10b981'
                              }}
                            />
                          </div>
                          <span className="text-xs text-slate-400">{u.financial_oxygen_score?.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 max-w-[200px]">
                        <span className="text-xs text-slate-400 line-clamp-1">{u.primary_trigger || '—'}</span>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`text-xs font-mono ${u.days_in_risk_zone > 30 ? 'text-danger' : 'text-warning'}`}>
                          {u.days_in_risk_zone}d
                        </span>
                      </td>
                      <td className="py-3">
                        <ArrowRightIcon className="w-4 h-4 text-slate-600 group-hover:text-aegis-400 transition-colors" />
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </div>
  )
}
