const icons = {
  activity: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M3 12h4l2.5-5 5 10 2.5-5H21" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  alert: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M12 9v4" strokeLinecap="round" />
      <path d="M12 17h.01" strokeLinecap="round" />
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.72 3h16.92a2 2 0 0 0 1.72-3L13.71 3.86a2 2 0 0 0-3.42 0Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="m7.5 12.5 3 3 6-7" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  ),
  clock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
}

export default function StatsCard({ label, value, sub, color = 'blue', icon = 'activity' }) {
  const colors = {
    blue: 'border-cyan-400/30 from-cyan-500/20 via-cyan-500/10 to-slate-950',
    red: 'border-rose-400/30 from-rose-500/20 via-rose-500/10 to-slate-950',
    green: 'border-emerald-400/30 from-emerald-500/20 via-emerald-500/10 to-slate-950',
    amber: 'border-amber-400/30 from-amber-500/20 via-amber-500/10 to-slate-950',
  }

  return (
    <div className={`rounded-[1.75rem] border bg-gradient-to-br p-5 shadow-[0_24px_80px_rgba(15,23,42,0.35)] ${colors[color] ?? colors.blue}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.24em] text-slate-400">{label}</p>
          <p className="mt-4 text-3xl font-semibold tracking-tight text-white">{value ?? '--'}</p>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-100 backdrop-blur">
          {icons[icon] ?? icons.activity}
        </div>
      </div>
      {sub && <p className="mt-5 text-sm text-slate-400">{sub}</p>}
    </div>
  )
}
