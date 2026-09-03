import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldIcon, ChartIcon, AlertIcon, HeartIcon, ArrowRightIcon } from '../components/Icons.jsx'

const features = [
  { icon: <ChartIcon className="w-6 h-6"/>, title: 'Real-Time Risk Scoring', desc: 'ML-powered composite score tracking EMI burden, cashflow trend, income stability and shock events.' },
  { icon: <AlertIcon className="w-6 h-6"/>, title: 'Anomaly Detection', desc: 'IsolationForest model flags unusual spending before it becomes a crisis.' },
  { icon: <HeartIcon className="w-6 h-6"/>, title: 'Adaptive Repayment', desc: 'Dynamic EMI restructuring that protects your survival buffer while keeping you current.' },
  { icon: <ShieldIcon className="w-6 h-6"/>, title: 'Proactive Intervention', desc: 'Bank ops sees at-risk users 30-90 days ahead — no more surprise defaults.' },
]

const flow = [
  { step: '01', label: 'Transactions Analysed' },
  { step: '02', label: 'Baseline Established' },
  { step: '03', label: 'Distress Scored' },
  { step: '04', label: 'Intervention Triggered' },
  { step: '05', label: 'Recovery Monitored' },
]

export default function LandingPage() {
  const nav = useNavigate()

  return (
    <div className="min-h-screen bg-surface bg-grid relative overflow-hidden">
      {/* Glow orbs */}
      <div className="orb w-96 h-96 bg-aegis-600 -top-32 -left-32" />
      <div className="orb w-80 h-80 bg-purple-600 top-1/2 -right-20" />

      {/* Nav */}
      <header className="glass border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldIcon className="w-6 h-6 text-aegis-400" />
            <span className="font-bold text-lg gradient-text">Aegis</span>
          </div>
          <div className="flex gap-3">
            <button onClick={() => nav('/login/customer')} className="btn-ghost text-sm py-1.5">
              Customer Portal
            </button>
            <button onClick={() => nav('/login/admin')} className="btn-primary text-sm py-1.5">
              Bank Admin
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-16 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="text-center"
        >
          <div className="inline-flex items-center gap-2 glass px-4 py-1.5 rounded-full text-xs text-aegis-300 border border-aegis-700/50 mb-8">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            ML Pipeline Active · 500 Users Monitored
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold mb-6 leading-tight">
            <span className="gradient-text">Financial Guardian</span>
            <br />
            <span className="text-white">for Every Borrower</span>
          </h1>

          <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-10">
            Aegis watches your financial health in real time, detects distress before it
            becomes default, and adapts your repayment — automatically, empathetically.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <motion.button
              whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
              onClick={() => nav('/login/customer')}
              className="btn-primary flex items-center justify-center gap-2 text-base px-8 py-3"
            >
              Customer Portal <ArrowRightIcon className="w-4 h-4" />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
              onClick={() => nav('/login/admin')}
              className="btn-ghost flex items-center justify-center gap-2 text-base px-8 py-3"
            >
              Bank Admin Dashboard
            </motion.button>
          </div>
        </motion.div>
      </section>

      {/* Flow timeline */}
      <section className="max-w-6xl mx-auto px-6 pb-16 relative z-10">
        <div className="flex items-center justify-between overflow-x-auto gap-2 pb-2">
          {flow.map((f, i) => (
            <motion.div
              key={f.step}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 + 0.3 }}
              className="flex flex-col items-center min-w-[100px]"
            >
              <div className="w-10 h-10 rounded-full bg-aegis-900 border-2 border-aegis-600 flex items-center justify-center text-aegis-300 text-xs font-bold mb-2">
                {f.step}
              </div>
              {i < flow.length - 1 && (
                <div className="absolute mt-5 ml-[100px] w-[calc(20%-10px)] h-px bg-gradient-to-r from-aegis-600 to-transparent hidden md:block" />
              )}
              <span className="text-xs text-slate-400 text-center">{f.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Feature cards */}
      <section className="max-w-6xl mx-auto px-6 pb-24 relative z-10">
        <h2 className="text-2xl font-bold text-center mb-10">
          <span className="gradient-text">Everything the system does</span>
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 + 0.5 }}
              className="glass rounded-2xl p-6 card-hover border border-aegis-800/40"
            >
              <div className="text-aegis-400 mb-3">{f.icon}</div>
              <h3 className="font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA row */}
      <section className="border-t border-border py-16 relative z-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <h3 className="text-xl font-bold mb-1">Ready to explore?</h3>
            <p className="text-slate-400 text-sm">Use any user ID like <code className="font-mono text-aegis-300 bg-aegis-900/40 px-1.5 rounded">USR0001</code> – <code className="font-mono text-aegis-300 bg-aegis-900/40 px-1.5 rounded">USR0500</code></p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => nav('/login/customer')} className="btn-primary">
              Enter as Customer
            </button>
            <button onClick={() => nav('/login/admin')} className="btn-ghost">
              Enter as Admin
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
