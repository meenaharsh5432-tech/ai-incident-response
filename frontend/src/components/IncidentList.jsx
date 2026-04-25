import { formatDistanceToNow } from 'date-fns'
import SeverityBadge from './SeverityBadge'

const statusDot = {
  active: 'bg-rose-400 shadow-[0_0_18px_rgba(251,113,133,0.65)]',
  resolved: 'bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.4)]',
  suppressed: 'bg-slate-500',
}

export default function IncidentList({ incidents = [], onSelect, selectedId }) {
  if (incidents.length === 0) {
    return (
      <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-6 py-14 text-center text-slate-400 backdrop-blur">
        <p className="text-sm uppercase tracking-[0.28em] text-slate-500">All clear</p>
        <p className="mt-3 text-lg text-white">No incidents match the current view.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {incidents.map((incident) => (
        <button
          key={incident.id}
          onClick={() => onSelect(incident.id)}
          className={`w-full rounded-[1.5rem] border p-4 text-left transition duration-200 ${
            selectedId === incident.id
              ? 'border-cyan-300/40 bg-cyan-400/10 shadow-[0_20px_60px_rgba(34,211,238,0.15)]'
              : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]'
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2">
              <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${statusDot[incident.status] ?? statusDot.active}`} />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{incident.error_type}</p>
                <p className="mt-1 truncate text-xs uppercase tracking-[0.2em] text-slate-400">{incident.service_name}</p>
              </div>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <SeverityBadge severity={incident.severity} />
              <span className="text-xs text-slate-400">
                {incident.occurrence_count}x · {formatDistanceToNow(new Date(incident.last_seen), { addSuffix: true })}
              </span>
            </div>
          </div>
          {incident.ai_diagnosis?.root_cause && (
            <p className="mt-3 pl-4 text-sm text-slate-300">{incident.ai_diagnosis.root_cause}</p>
          )}
        </button>
      ))}
    </div>
  )
}
