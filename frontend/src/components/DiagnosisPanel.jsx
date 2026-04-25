import { useState } from 'react'
import { getErrorMessage, submitFeedback } from '../api/client'

export default function DiagnosisPanel({ incident, onFeedback }) {
  const [submitting, setSubmitting] = useState(false)
  const [feedbackDone, setFeedbackDone] = useState(false)
  const [actualFix, setActualFix] = useState('')
  const [error, setError] = useState('')

  const diagnosis = incident.ai_diagnosis

  if (!diagnosis) {
    return (
      <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">AI Diagnosis</h3>
        <p className="text-sm text-slate-400">Analysis is still running. Check back in a few seconds.</p>
      </div>
    )
  }

  async function handleFeedback(helpful) {
    setSubmitting(true)
    setError('')

    try {
      await submitFeedback(incident.id, helpful, actualFix || null)
      setFeedbackDone(true)
      onFeedback?.()
    } catch (submitError) {
      setError(getErrorMessage(submitError, 'Unable to save feedback right now.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-5 rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <h3 className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">AI Diagnosis</h3>

      <div>
        <p className="mb-1 text-xs uppercase tracking-[0.18em] text-slate-500">Root cause</p>
        <p className="text-sm font-medium text-white">{diagnosis.root_cause}</p>
      </div>

      {diagnosis.steps?.length > 0 && (
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">Recommended steps</p>
          <ol className="space-y-2">
            {diagnosis.steps.map((step, index) => (
              <li key={index} className="flex gap-3 text-sm text-slate-300">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-xs text-slate-200">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {diagnosis.code_snippet && (
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">Code fix</p>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-emerald-400/20 bg-slate-950/90 p-4 text-xs leading-relaxed text-emerald-200">
            {diagnosis.code_snippet}
          </pre>
        </div>
      )}

      {diagnosis.prevention && (
        <div>
          <p className="mb-1 text-xs uppercase tracking-[0.18em] text-slate-500">Prevention</p>
          <p className="text-sm italic text-slate-300">{diagnosis.prevention}</p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      {!feedbackDone ? (
        <div className="border-t border-white/10 pt-4">
          <p className="mb-3 text-xs uppercase tracking-[0.18em] text-slate-500">Was this diagnosis helpful?</p>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <button
              onClick={() => handleFeedback(true)}
              disabled={submitting}
              className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100 transition hover:bg-emerald-500/20 disabled:opacity-50"
            >
              Helpful
            </button>
            <button
              onClick={() => handleFeedback(false)}
              disabled={submitting}
              className="rounded-full border border-rose-400/30 bg-rose-500/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-100 transition hover:bg-rose-500/20 disabled:opacity-50"
            >
              Not quite
            </button>
            <input
              value={actualFix}
              onChange={(event) => setActualFix(event.target.value)}
              placeholder="What was the actual fix? (optional)"
              className="min-w-0 flex-1 rounded-full border border-white/10 bg-slate-950/80 px-4 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-300/40 focus:outline-none"
            />
          </div>
        </div>
      ) : (
        <p className="border-t border-white/10 pt-4 text-sm text-emerald-200">
          Feedback saved. Thanks for helping improve the diagnosis quality.
        </p>
      )}
    </div>
  )
}
