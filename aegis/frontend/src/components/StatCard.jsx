import { TrendUpIcon, TrendDownIcon } from './Icons.jsx'

export default function StatCard({ label, value, sub, trend, icon, color = 'aegis', loading }) {
  const colors = {
    aegis:   'from-aegis-600/20 to-aegis-800/10 border-aegis-700/30 text-aegis-300',
    success: 'from-success/20 to-success/5  border-success/30  text-success',
    warning: 'from-warning/20 to-warning/5  border-warning/30  text-warning',
    danger:  'from-danger/20  to-danger/5   border-danger/30   text-danger',
    blue:    'from-blue-500/20 to-blue-800/10 border-blue-600/30 text-blue-300',
  }
  const c = colors[color] || colors.aegis

  if (loading) return (
    <div className="glass rounded-2xl p-5">
      <div className="shimmer h-4 w-24 rounded mb-3" />
      <div className="shimmer h-8 w-16 rounded mb-2" />
      <div className="shimmer h-3 w-32 rounded" />
    </div>
  )

  return (
    <div className={`glass rounded-2xl p-5 card-hover bg-gradient-to-br ${c} border`}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        {icon && <span className={`${c.split(' ').pop()}`}>{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      {sub && (
        <div className="flex items-center gap-1 text-xs text-slate-400">
          {trend === 'up'   && <TrendUpIcon className="w-3 h-3 text-success" />}
          {trend === 'down' && <TrendDownIcon className="w-3 h-3 text-danger" />}
          {sub}
        </div>
      )}
    </div>
  )
}
