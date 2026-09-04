import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from 'recharts'
import { getSurvivalBuffer } from '../../api/client.js'
import { PageSpinner } from '../../components/Spinner.jsx'
import Card, { CardHeader } from '../../components/Card.jsx'
import DemoBanner from '../../components/DemoBanner.jsx'
import { HeartIcon, ShieldIcon, WarnIcon } from '../../components/Icons.jsx'

const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

const statusConfig = {
  strong:   { color: 'text-success', bg: 'bg-success/10', border: 'border-success/30', icon: <ShieldIcon className="w-4 h-4"/>, label: 'Strong' },
  adequate: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: <ShieldIcon className="w-4 h-4"/>, label: 'Adequate' },
  thin:     { color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/30', icon: <WarnIcon className="w-4 h-4"/>, label: 'Thin' },
  critical: { color: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/30', icon: <WarnIcon className="w-4 h-4"/>, label: 'Critical' },
  depleted: { color: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/30', icon: <WarnIcon className="w-4 h-4"/>, label: 'Depleted' },
  unknown:  { color: 'text-slate-400', bg: 'bg-[#f8f8fc]', border: 'border-border', icon: <HeartIcon className="w-4 h-4"/>, label: 'Unknown' },
}

export default function CustomerBuffer() {
  const [data,    setData]    = useState(null)
  const [isDemo,  setIsDemo]  = useState(false)
  const [loading, setLoading] = useState(true)
  const uid = localStorage.getItem('aegis_uid')

  useEffect(() => {
    getSurvivalBuffer(uid).then(({ data, isDemo }) => { setData(data); setIsDemo(isDemo) }).finally(() => setLoading(false))
  }, [uid])

  if (loading) return <PageSpinner />
  if (!data || data.error) return (
    <div className="text-center py-20 text-slate-400">
      No survival buffer data available yet. Run the ML batch pipeline first.
    </div>
  )

  const sc = statusConfig[data.buffer_status] || statusConfig.unknown
  const breakdown = Object.entries(data.monthly_essential_breakdown || {}).filter(([,v]) => v > 0)
  const coveragePct = Math.min(100, (data.buffer_coverage_months / 3) * 100)

  const radialData = [{ name: 'Buffer', value: coveragePct, fill: data.buffer_coverage_months >= 3 ? '#10b981' : data.buffer_coverage_months >= 1.5 ? '#6366f1' : '#f59e0b' }]

  return (
    <div className="space-y-6">
      {isDemo && <DemoBanner label="your safety buffer" />}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold">Safety Buffer</h1>
        <p className="text-slate-400 text-sm mt-0.5">Essential expense ring-fence protecting your financial floor</p>
      </motion.div>

      {/* Status banner */}
      <div className={`glass rounded-2xl p-5 border ${sc.border} ${sc.bg} flex items-center gap-4`}>
        <div className={sc.color}>{sc.icon}</div>
        <div>
          <p className={`font-bold ${sc.color}`}>Buffer Status: {sc.label}</p>
          <p className="text-sm text-slate-300 mt-0.5">
            {data.ring_fenced
              ? 'Aegis has ring-fenced your survival buffer — essential expenses are protected.'
              : 'Your buffer is healthy. No ring-fencing required at this time.'}
          </p>
        </div>
      </div>

      {/* Summary + radial */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Radial chart */}
        <Card className="p-6 flex flex-col items-center justify-center">
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart cx="50%" cy="50%" innerRadius="60%" outerRadius="90%" data={radialData} startAngle={90} endAngle={-270}>
                <RadialBar background={{ fill: '#2a2a45' }} dataKey="value" cornerRadius={8} />
                <Tooltip formatter={(v) => [`${v.toFixed(1)}%`, 'Coverage']} />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-center text-sm font-medium text-slate-900 -mt-4">{data.buffer_coverage_months} months coverage</p>
          <p className="text-xs text-slate-400">(target: 3 months)</p>
        </Card>

        {/* Key metrics */}
        <div className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
          <Card className="p-5">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Current Balance</p>
            <p className="text-2xl font-bold text-slate-900">{fmt(data.current_balance)}</p>
          </Card>
          <Card className="p-5">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Buffer Required</p>
            <p className="text-2xl font-bold text-aegis-300">{fmt(data.buffer_amount)}</p>
            <p className="text-xs text-slate-500 mt-1">incl. {data.safety_margin_pct}% safety margin</p>
          </Card>
          <Card className="p-5">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Monthly Essentials</p>
            <p className="text-2xl font-bold text-slate-900">{fmt(data.total_monthly_essential)}</p>
          </Card>
          <Card className="p-5">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Ring-fenced</p>
            <p className={`text-2xl font-bold ${data.ring_fenced ? 'text-success' : 'text-slate-400'}`}>
              {data.ring_fenced ? 'YES' : 'NO'}
            </p>
          </Card>
        </div>
      </div>

      {/* Expense breakdown */}
      {breakdown.length > 0 && (
        <Card className="p-5">
          <CardHeader title="Monthly Essential Breakdown" icon={<HeartIcon className="w-4 h-4"/>} />
          <div className="space-y-3">
            {breakdown.sort(([,a],[,b]) => b - a).map(([cat, amt]) => {
              const pct = Math.round((amt / data.total_monthly_essential) * 100)
              return (
                <div key={cat}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm capitalize text-slate-300">{cat}</span>
                    <span className="text-sm font-semibold text-slate-900">{fmt(amt)}</span>
                  </div>
                  <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, delay: 0.1 }}
                      className="h-full bg-aegis-500 rounded-full"
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}
    </div>
  )
}
