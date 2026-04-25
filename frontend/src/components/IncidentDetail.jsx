import { useState } from 'react'
import { format, formatDistanceToNow } from 'date-fns'
import { parseDate } from '../utils/date'
import SeverityBadge from './SeverityBadge'
import DiagnosisPanel from './DiagnosisPanel'
import { getErrorMessage, resolveIncident } from '../api/client'

function fmtMTTR(seconds) {
  if (seconds == null) return null
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

export default function IncidentDetail({ incident, onResolved, onDiagnosed, onFeedback }) {
  const [resolving, setResolving] = useState(false)
  const [notes, setNotes] = useState('')
  const [showNotes, setShowNotes] = useState(false)
  const [showErrors, setShowErrors] = useState(false)
  const [error, setError] = useState('')

  async function handleResolve() {
    setResolving(true)
    setError('')

    try {
      await resolveIncident(incident.id, notes || null)
      setShowNotes(false)
      onResolved?.()
    } catch (resolveError) {
      setError(getErrorMessage(resolveError, 'Unable to resolve this incident right now.'))
    } finally {
      setResolving(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-[1.9rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Incident detail</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">{incident.error_type}</h2>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-100">
                {incident.service_name}
              </span>
              <SeverityBadge severity={incident.severity} />
              <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${
                incident.status === 'resolved'
                  ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                  : 'border-rose-400/30 bg-rose-500/10 text-rose-100'
              }`}>
                {incident.status}
              </span>
            </div>
          </div>

          {incident.status === 'active' && (
            <div className="shrink-0">
              {showNotes ? (
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <input
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="Add resolution notes"
                    className="rounded-full border border-white/10 bg-slate-950/85 px-4 py-2 text-sm text-white focus:border-emerald-300/40 focus:outline-none"
                  />
                  <button
                    onClick={handleResolve}
                    disabled={resolving}
                    className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-50 transition hover:bg-emerald-500/20 disabled:opacity-50"
                  >
                    {resolving ? 'Saving...' : 'Confirm'}
                  </button>
                  <button
                    onClick={() => setShowNotes(false)}
                    className="text-sm text-slate-400 transition hover:text-white"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowNotes(true)}
                  className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-50 transition hover:bg-emerald-500/20"
                >
                  Resolve
                </button>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {error}
          </div>
        )}

        <div className="mt-6 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <div>
            <p className="uppercase tracking-[0.18em] text-slate-500">First seen</p>
            <p className="mt-2 text-sm text-white">{format(parseDate(incident.first_seen), 'MMM d, HH:mm')}</p>
          </div>
          <div>
            <p className="uppercase tracking-[0.18em] text-slate-500">Last seen</p>
            <p className="mt-2 text-sm text-white">
              {formatDistanceToNow(parseDate(incident.last_seen), { addSuffix: true })}
            </p>
          </div>
          <div>
            <p className="uppercase tracking-[0.18em] text-slate-500">Occurrences</p>
            <p className="mt-2 text-base font-semibold text-white">{incident.occurrence_count}</p>
          </div>
          <div>
            <p className="uppercase tracking-[0.18em] text-slate-500">MTTR</p>
            <p className="mt-2 text-sm text-white">{fmtMTTR(incident.mttr_seconds) ?? '--'}</p>
          </div>
        </div>

        {incident.resolution_notes && (
          <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
            <span className="font-semibold">Resolution: </span>
            {incident.resolution_notes}
          </div>
        )}
      </div>

      <DiagnosisPanel incident={incident} onDiagnosed={onDiagnosed} onFeedback={onFeedback} />

      {incident.errors?.length > 0 && (
        <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <button
            onClick={() => setShowErrors((value) => !value)}
            className="flex w-full items-center justify-between text-left text-xs font-semibold uppercase tracking-[0.24em] text-slate-400"
          >
            <span>Error Samples ({incident.errors.length})</span>
            <span>{showErrors ? 'Hide' : 'Show'}</span>
          </button>

          {showErrors && (
            <div className="mt-4 max-h-96 space-y-3 overflow-y-auto">
              {incident.errors.slice(0, 20).map((errorItem) => (
                <div key={errorItem.id} className="rounded-2xl border border-white/10 bg-slate-950/80 p-4 text-xs">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-slate-400">
                      {format(parseDate(errorItem.created_at), 'MMM d HH:mm:ss')} · {errorItem.environment}
                    </span>
                  </div>
                  <p className="break-words text-sm text-slate-200">{errorItem.message}</p>
                  {errorItem.stack_trace && (
                    <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-500">
                      {errorItem.stack_trace.slice(0, 800)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
