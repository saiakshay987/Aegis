export default function Spinner({ size = 'md', className = '' }) {
  const sz = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }[size]
  return (
    <div className={`${sz} ${className} animate-spin rounded-full
      border-2 border-border border-t-aegis-400`} />
  )
}

export function PageSpinner() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <div className="relative">
        <div className="w-16 h-16 rounded-full border-2 border-aegis-800 border-t-aegis-400 animate-spin" />
        <div className="absolute inset-2 rounded-full border-2 border-aegis-700 border-b-aegis-300 animate-spin animate-reverse" />
      </div>
      <p className="text-slate-400 text-sm animate-pulse">Loading…</p>
    </div>
  )
}
