import { useNavigate, useLocation } from 'react-router-dom'
import { ShieldIcon } from './Icons.jsx'

export default function Navbar({ role }) {
  const navigate  = useNavigate()
  const location  = useLocation()
  const userId    = localStorage.getItem('aegis_uid') || ''

  const logout = () => {
    localStorage.clear()
    navigate('/')
  }

  const customerTabs = [
    { label: 'Dashboard',     path: '/customer' },
    { label: 'Cashflow',      path: '/customer/projection' },
    { label: 'Repayment',     path: '/customer/repayment' },
    { label: 'Anomalies',     path: '/customer/anomalies' },
    { label: 'Safety Buffer', path: '/customer/buffer' },
  ]
  const adminTabs = [
    { label: 'Portfolio',  path: '/admin' },
    { label: 'At-Risk',    path: '/admin#risk' },
  ]
  const tabs = role === 'admin' ? adminTabs : customerTabs

  return (
    <header className="glass border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => navigate(role === 'admin' ? '/admin' : '/customer')}>
          <ShieldIcon className="w-6 h-6 text-aegis-400" />
          <span className="font-bold text-lg gradient-text">Aegis</span>
          <span className="text-xs border border-aegis-700 text-aegis-400 rounded-full px-2 py-0.5">
            {role === 'admin' ? 'Admin' : 'Customer'}
          </span>
        </div>

        {/* Nav tabs */}
        <nav className="hidden md:flex items-center gap-1">
          {tabs.map(t => {
            const active = location.pathname === t.path
            return (
              <button
                key={t.path}
                onClick={() => navigate(t.path)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                  ${active
                    ? 'bg-aegis-600/20 text-aegis-300 border border-aegis-600/40'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
              >
                {t.label}
              </button>
            )
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {userId && (
            <span className="hidden sm:block text-xs font-mono text-slate-500 bg-surface px-2 py-1 rounded-lg border border-border">
              {userId}
            </span>
          )}
          <button onClick={logout} className="btn-ghost text-sm py-1.5">
            Sign out
          </button>
        </div>
      </div>
    </header>
  )
}
