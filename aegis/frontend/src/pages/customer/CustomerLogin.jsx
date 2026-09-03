import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldIcon, UserIcon, ArrowRightIcon } from '../../components/Icons.jsx'
import Spinner from '../../components/Spinner.jsx'
import { getAssessment } from '../../api/client.js'

const DEMO_IDS = ['USR0001', 'USR0050', 'USR0100', 'USR0250', 'USR0420']

export default function CustomerLogin() {
  const [userId, setUserId]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const nav = useNavigate()

  const handleLogin = async (uid) => {
    const id = (uid || userId).trim()
    if (!id) { setError('Enter a User ID'); return }
    setLoading(true); setError('')
    try {
      await getAssessment(id)   // validates the user exists
      localStorage.setItem('aegis_uid',  id)
      localStorage.setItem('aegis_role', 'customer')
      nav('/customer')
    } catch (e) {
      setError(e.response?.status === 404
        ? `User "${id}" not found. Try USR0001 – USR0500.`
        : 'Cannot reach the backend. Is uvicorn running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface bg-grid flex items-center justify-center p-4">
      <div className="orb w-72 h-72 bg-aegis-600 -top-20 -left-20" />
      <div className="orb w-60 h-60 bg-purple-700 bottom-10 right-10" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="glass rounded-3xl p-8 w-full max-w-md relative z-10 shadow-glow"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-aegis-900/80 border border-aegis-700 mb-4 animate-float">
            <ShieldIcon className="w-7 h-7 text-aegis-400" />
          </div>
          <h1 className="text-2xl font-bold gradient-text">Customer Portal</h1>
          <p className="text-slate-400 text-sm mt-1">Enter your User ID to view your financial health</p>
        </div>

        {/* Input */}
        <div className="mb-4">
          <label className="text-xs text-slate-400 uppercase tracking-wider mb-2 block">User ID</label>
          <input
            className="input-field font-mono"
            placeholder="e.g. USR0001"
            value={userId}
            onChange={e => { setUserId(e.target.value.toUpperCase()); setError('') }}
            onKeyDown={e => e.key === 'Enter' && handleLogin()}
            autoFocus
          />
        </div>

        {error && (
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="text-danger text-xs mb-4 p-3 bg-danger/10 border border-danger/20 rounded-xl"
          >
            {error}
          </motion.p>
        )}

        <button
          onClick={() => handleLogin()}
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3"
        >
          {loading ? <Spinner size="sm" /> : <><UserIcon className="w-4 h-4" /> Sign In <ArrowRightIcon className="w-4 h-4" /></>}
        </button>

        {/* Demo IDs */}
        <div className="mt-6">
          <p className="text-xs text-slate-500 text-center mb-3">— Quick demo access —</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {DEMO_IDS.map(id => (
              <button
                key={id}
                onClick={() => handleLogin(id)}
                className="font-mono text-xs px-3 py-1.5 rounded-lg bg-surface border border-border
                           hover:border-aegis-500 hover:text-aegis-300 transition-all text-slate-400"
              >
                {id}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => nav('/')}
          className="mt-6 text-xs text-slate-500 hover:text-slate-300 transition-colors w-full text-center"
        >
          ← Back to home
        </button>
      </motion.div>
    </div>
  )
}
