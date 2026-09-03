import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getAssessment } from '../../api/client.js'
import OxygenGauge from '../../components/OxygenGauge.jsx'
import RiskBadge   from '../../components/RiskBadge.jsx'
import StatCard    from '../../components/StatCard.jsx'
import { PageSpinner } from '../../components/Spinner.jsx'
import { ChartIcon, AlertIcon, HeartIcon, BankIcon, ArrowRightIcon, WarnIcon, CashIcon } from '../../components/Icons.jsx'

const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

export default function CustomerHome() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const uid = localStorage.getItem('aegis_uid')
  const nav = useNavigate()

  useEffect(() => {
    getAssessment(uid)
      .then(setData)
      .catch(() => setError('Failed to load your data. Check the backend.'))
      .finally(() => setLoading(false))
  }, [uid])

  if (loading) return <PageSpinner />
  if (error)   return <div className="text-danger text-center py-20">{error}</div>
  if (!data)   return null

  const score    = data.financial_oxygen_score ?? 0
  const isBad    = data.risk_status === 'At-Risk' || data.risk_status === 'Critical'

  return (
    <div className="space-y-6">
      {/* Top greeting bar */}
      <motion.div
        initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome back, <span className="gradient-text">{data.name || uid}</span>
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">Your financial health snapshot · Live</p>
        </div>
        <RiskBadge status={data.risk_status} size="lg" pulse={isBad} />
      </motion.div>

      {/* Distress alert */}
      {isBad && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
          className="glass border border-danger/40 rounded-2xl p-4 flex items-start gap-3 bg-danger/5"
        >
          <WarnIcon className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-danger text-sm">Financial Stress Detected</p>
            <p className="text-slate-300 text-sm mt-0.5">
              Aegis has identified signs of financial pressure on your account.
              Check your repayment plan — we may be able to help.
            </p>
            <button onClick={() => nav('/customer/repayment')}
              className="mt-2 text-xs text-danger underline underline-offset-2 hover:text-red-300">
              View adaptive repayment plan →
            </button>
          </div>
        </motion.div>
      )}

      {/* Main grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Gauge card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}
          className="glass rounded-2xl p-6 flex flex-col items-center justify-center gap-4"
        >
          <OxygenGauge score={score} size={180} />
          <div className="text-center">
            <p className="text-sm font-semibold text-white">Financial Oxygen Score</p>
            <p className="text-xs text-slate-400 mt-1 max-w-[200px] text-center">
              How much breathing room you have above your living floor
            </p>
          </div>
        </motion.div>

        {/* Stats */}
        <div className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
          {[
            { label: 'Current Balance',   value: fmt(data.balance),          icon: <CashIcon className="w-4 h-4"/>,  color: 'aegis'   },
            { label: 'Living Floor',      value: fmt(data.living_floor),      icon: <HeartIcon className="w-4 h-4"/>, color: 'blue'    },
            { label: 'Monthly Income',    value: fmt(data.monthly_income),    icon: <ChartIcon className="w-4 h-4"/>, color: 'success' },
            { label: 'Monthly Expenses',  value: fmt(data.monthly_expenses),  icon: <BankIcon  className="w-4 h-4"/>, color: 'warning' },
          ].map((s, i) => (
            <motion.div key={s.label}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 + 0.15 }}>
              <StatCard {...s} />
            </motion.div>
          ))}
        </div>
      </div>

      {/* Active loans + quick nav */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
          className="sm:col-span-2 lg:col-span-1 glass rounded-2xl p-5 flex flex-col justify-between"
        >
          <span className="text-xs text-slate-400 uppercase tracking-wider">Active Loans</span>
          <span className="text-4xl font-bold text-white mt-2">{data.active_loans ?? 0}</span>
          <span className="text-xs text-slate-500 mt-1">loan(s) being monitored</span>
        </motion.div>

        {[
          { label: 'Cashflow Projection', icon: <ChartIcon className="w-5 h-5"/>, path: '/customer/projection', desc: '30/60/90 day balance forecast' },
          { label: 'Anomaly Report',      icon: <AlertIcon className="w-5 h-5"/>, path: '/customer/anomalies',  desc: 'Unusual transaction flags' },
          { label: 'Safety Buffer',       icon: <HeartIcon className="w-5 h-5"/>, path: '/customer/buffer',     desc: 'Essential expense ring-fence' },
        ].map((item, i) => (
          <motion.button
            key={item.path}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 + 0.45 }}
            onClick={() => nav(item.path)}
            className="glass rounded-2xl p-5 text-left card-hover group"
          >
            <div className="text-aegis-400 mb-3 group-hover:text-aegis-300 transition-colors">{item.icon}</div>
            <p className="font-semibold text-sm text-white">{item.label}</p>
            <p className="text-xs text-slate-400 mt-1">{item.desc}</p>
            <div className="mt-3 flex items-center gap-1 text-xs text-aegis-400 opacity-0 group-hover:opacity-100 transition-opacity">
              View <ArrowRightIcon className="w-3 h-3" />
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
