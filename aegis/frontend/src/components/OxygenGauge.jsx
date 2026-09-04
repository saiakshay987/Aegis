import { useEffect, useState } from 'react'

function getColor(score) {
  if (score >= 70) return { stroke: '#10b981', text: 'text-success', glow: '#10b981' }
  if (score >= 45) return { stroke: '#3b82f6', text: 'text-blue-400', glow: '#3b82f6' }
  if (score >= 20) return { stroke: '#f59e0b', text: 'text-warning', glow: '#f59e0b' }
  return { stroke: '#ef4444', text: 'text-danger', glow: '#ef4444' }
}

export default function OxygenGauge({ score = 0, size = 160 }) {
  const [animated, setAnimated] = useState(0)
  const r = size * 0.38
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * r
  // Arc covers 270° (from 135° to 405°)
  const arcLen = circumference * 0.75
  const offset = arcLen - (animated / 100) * arcLen
  const color = getColor(animated)

  useEffect(() => {
    const t = setTimeout(() => {
      let cur = 0
      const step = setInterval(() => {
        cur += 1.5
        if (cur >= score) { setAnimated(score); clearInterval(step) }
        else setAnimated(Math.round(cur))
      }, 12)
      return () => clearInterval(step)
    }, 200)
    return () => clearTimeout(t)
  }, [score])

  const labelSize = size < 140 ? 'text-2xl' : 'text-3xl'

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="rotate-[135deg]">
        {/* Track */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke="#2a2a45"
          strokeWidth={size * 0.08}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={color.stroke}
          strokeWidth={size * 0.08}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 0.05s linear',
            filter: `drop-shadow(0 0 6px ${color.glow})`,
          }}
        />
      </svg>
      {/* Centre label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center -rotate-0">
        <span className={`font-bold ${labelSize} ${color.text}`}>{animated}</span>
        <span className="text-xs text-slate-400 -mt-1">/ 100</span>
          <span className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest">Aegis Score</span>
      </div>
    </div>
  )
}
