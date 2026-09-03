import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { getAnomalies } from '../../api/client.js'
import { PageSpinner } from '../../components/Spinner.jsx'
import Card, { CardHeader } from '../../components/Card.jsx'
import { AlertIcon, CheckIcon } from '../../components/Icons.jsx'

const severityConfig = {
  high:   { bg: 'bg-danger/10',  border: 'border-danger/30',  text: 'text-danger',  label: 'High' },
  medium: { bg: 'bg-warning/10', border: 'border-warning/30', text: 'text-warning', label: 'Medium' },
  low:    { bg: 'bg-blue-500/10',border: 'border-blue-500/30',text: 'text-blue-400',label: 'Low' },
}

const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

export default function CustomerAnomalies() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const uid = localStorage.getItem('aegis_uid')

  useEffect(() => {
    getAnomalies(uid).then(setData).finally(() => setLoading(false))
  }, [uid])

  if (loading) return <PageSpinner />

  const anomalies = data?.anomalies || []

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold">Anomaly Report</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Unusual transactions flagged by Aegis ML anomaly detection
        </p>
      </motion.div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {['high', 'medium', 'low'].map(sev => {
          const count = anomalies.filter(a => a.severity === sev).length
          const c = severityConfig[sev]
          return (
            <div key={sev} className={`glass rounded-2xl p-4 border ${c.border} ${c.bg}`}>
              <p className={`text-xs font-medium uppercase tracking-wider ${c.text}`}>{c.label}</p>
              <p className="text-2xl font-bold text-white mt-1">{count}</p>
            </div>
          )
        })}
      </div>

      {/* All-clear */}
      {anomalies.length === 0 && (
        <Card className="p-10 text-center">
          <CheckIcon className="w-12 h-12 text-success mx-auto mb-4" />
          <h2 className="text-xl font-bold text-success mb-2">No anomalies detected</h2>
          <p className="text-slate-400">Your recent transactions look normal. Keep it up!</p>
        </Card>
      )}

      {/* Anomaly list */}
      {anomalies.length > 0 && (
        <Card className="p-5">
          <CardHeader title={`${anomalies.length} flagged transaction${anomalies.length > 1 ? 's' : ''}`}
                      icon={<AlertIcon className="w-4 h-4"/>} />
          <div className="space-y-3">
            {anomalies.map((a, i) => {
              const c = severityConfig[a.severity] || severityConfig.low
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                  className={`rounded-xl p-4 border ${c.border} ${c.bg}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full border ${c.border} ${c.text} ${c.bg}`}>
                        {c.label}
                      </span>
                      <span className="text-sm font-medium text-white capitalize">
                        {a.category?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <span className={`text-lg font-bold ${c.text}`}>{fmt(a.amount)}</span>
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{a.description}</p>
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span>Date: <span className="text-slate-300">{a.date || 'N/A'}</span></span>
                    <span>Expected: <span className="text-slate-300">{fmt(a.expected_range_min)} – {fmt(a.expected_range_max)}</span></span>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </Card>
      )}
    </div>
  )
}
