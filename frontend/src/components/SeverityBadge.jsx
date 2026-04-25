const cfg = {
  critical: 'border-rose-400/30 bg-rose-500/10 text-rose-200',
  high: 'border-orange-400/30 bg-orange-500/10 text-orange-200',
  medium: 'border-amber-400/30 bg-amber-500/10 text-amber-200',
  low: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200',
}

export default function SeverityBadge({ severity }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${cfg[severity] ?? cfg.medium}`}>
      {severity}
    </span>
  )
}
