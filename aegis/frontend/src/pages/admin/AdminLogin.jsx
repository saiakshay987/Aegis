import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BankIcon, LockIcon, ArrowRightIcon } from '../../components/Icons.jsx'
import Spinner from '../../components/Spinner.jsx'
import { getPortfolioSummary } from '../../api/client.js'

// Simple password gate for demo — replace with real auth in production
const ADMIN_PASS = 'aegis2024'

export default function AdminLogin() {
  const [pass,    setPass]    = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [show,    setShow]    = useState(false)
  const nav = useNavigate()

  const handleLogin = async () => {
    if (pass !== ADMIN_PASS) {
      setError(`Wrong password. Hint: ${ADMIN_PASS}`)
      return
    }
    setLoading(true); setError('')
    try {
      await getPortfolioSummary()   // validate backend reachable
      localStorage.setItem('aegis_role', 'admin')
      nav('/admin')
    } catch {
      setError('Cannot reach the backend. Is uvicorn running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface bg-grid flex items-center justify-center p-4">
      <div className="orb w-72 h-72 bg-indigo-700 top-10 right-10 opacity-20" />
      <div className="orb w-56 h-56 bg-purple-700 bottom-10 left-10 opacity-20" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="glass rounded-3xl p-8 w-full max-w-md relative z-10 shadow-glow"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-900/80 border border-indigo-700 mb-4">
            <BankIcon className="w-7 h-7 text-indigo-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Bank Admin</h1>
          <p className="text-slate-400 text-sm mt-1">Portfolio Command Center</p>
        </div>

        <div className="mb-4">
          <label className="text-xs text-slate-400 uppercase tracking-wider mb-2 block">Admin Password</label>
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              className="input-field pr-10"
              placeholder="Enter password"
              value={pass}
              onChange={e => { setPass(e.target.value); setError('') }}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShow(s => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <LockIcon className="w-4 h-4" />
            </button>
          </div>
        </div>

        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="text-danger text-xs mb-4 p-3 bg-danger/10 border border-danger/20 rounded-xl">
            {error}
          </motion.p>
        )}

        <button onClick={handleLogin} disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3">
          {loading ? <Spinner size="sm" /> : <><BankIcon className="w-4 h-4" /> Enter Dashboard <ArrowRightIcon className="w-4 h-4" /></>}
        </button>

        <button onClick={() => nav('/')}
          className="mt-6 text-xs text-slate-500 hover:text-slate-300 transition-colors w-full text-center">
          ← Back to home
        </button>
      </motion.div>
    </div>
  )
}
