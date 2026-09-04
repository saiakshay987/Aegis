export default function DemoBanner({ label = 'this page' }) {
  return (
    <div className="glass rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-center gap-3">
      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 bg-amber-100 border border-amber-200 rounded-full px-2 py-1 flex-none">
        Demo data
      </span>
      <p className="text-xs text-amber-800">
        Live connection failed — showing demo data for {label} so you can keep exploring. Numbers below are not real.
      </p>
    </div>
  )
}
