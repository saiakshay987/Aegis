const config = {
  'Healthy':  { bg: 'bg-success/10', text: 'text-success', border: 'border-success/30', dot: 'bg-success', label: 'Healthy' },
  'Watch':    { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-400', label: 'Watch' },
  'At-Risk':  { bg: 'bg-warning/10', text: 'text-warning', border: 'border-warning/30', dot: 'bg-warning', label: 'At-Risk' },
  'Critical': { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/30', dot: 'bg-danger', label: 'Critical' },
  'healthy':  { bg: 'bg-success/10', text: 'text-success', border: 'border-success/30', dot: 'bg-success', label: 'Healthy' },
  'at_risk':  { bg: 'bg-warning/10', text: 'text-warning', border: 'border-warning/30', dot: 'bg-warning', label: 'At-Risk' },
  'critical': { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/30', dot: 'bg-danger', label: 'Critical' },
}

export default function RiskBadge({ status, size = 'sm', pulse = false }) {
  const c = config[status] || config['Watch']
  const sz = size === 'lg' ? 'px-4 py-1.5 text-sm' : 'px-2.5 py-1 text-xs'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium
      ${c.bg} ${c.text} ${c.border} ${sz}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${pulse ? 'animate-pulse' : ''}`} />
      {c.label}
    </span>
  )
}
