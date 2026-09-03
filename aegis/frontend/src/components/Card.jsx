export default function Card({ children, className = '', hover = false, glow = false }) {
  return (
    <div className={`
      glass rounded-2xl
      ${hover ? 'card-hover' : ''}
      ${glow  ? 'shadow-glow' : ''}
      ${className}
    `}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, icon, action }) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div className="flex items-center gap-3">
        {icon && (
          <div className="p-2 rounded-xl bg-aegis-900/50 text-aegis-400">
            {icon}
          </div>
        )}
        <div>
          <h3 className="font-semibold text-white">{title}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
