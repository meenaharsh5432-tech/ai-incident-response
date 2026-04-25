import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { parseDate } from '../utils/date'
import { createApiKey, getErrorMessage, listApiKeys, revokeApiKey } from '../api/client'

export default function APIKeys({ onKeyCreated }) {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [serviceName, setServiceName] = useState('')
  const [generating, setGenerating] = useState(false)
  const [newKey, setNewKey] = useState(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const [revoking, setRevoking] = useState(null)

  const loadKeys = useCallback(async () => {
    setLoading(true)
    try {
      setKeys(await listApiKeys())
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load API keys.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadKeys()
  }, [loadKeys])

  async function handleGenerate(e) {
    e.preventDefault()
    if (!serviceName.trim()) return
    setGenerating(true)
    setError('')
    try {
      const result = await createApiKey(serviceName.trim())
      setNewKey(result)
      setShowForm(false)
      setServiceName('')
      onKeyCreated?.(result.key)
      loadKeys()
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to generate API key.'))
    } finally {
      setGenerating(false)
    }
  }

  async function handleRevoke(id) {
    setRevoking(id)
    try {
      await revokeApiKey(id)
      setKeys((prev) => prev.filter((k) => k.id !== id))
      if (newKey?.id === id) setNewKey(null)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to revoke API key.'))
    } finally {
      setRevoking(null)
    }
  }

  function copyKey() {
    navigator.clipboard.writeText(newKey.key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      {newKey && (
        <div className="rounded-[1.9rem] border border-amber-400/30 bg-amber-500/10 p-6 backdrop-blur-xl">
          <p className="text-xs uppercase tracking-[0.24em] text-amber-400">
            Save this key — it won&apos;t be shown again
          </p>
          <div className="mt-4 flex items-center gap-3">
            <code className="min-w-0 flex-1 break-all rounded-xl bg-slate-900 px-4 py-3 font-mono text-sm text-amber-200">
              {newKey.key}
            </code>
            <button
              onClick={copyKey}
              className="shrink-0 rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:bg-amber-500/20"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="mt-3 text-xs text-slate-400">Service: {newKey.service_name}</p>
        </div>
      )}

      {error && (
        <div className="rounded-[1.5rem] border border-rose-400/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
          {error}
        </div>
      )}

      <section className="rounded-[1.9rem] border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Access</p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-white">API Keys</h2>
          </div>
          {!showForm && (
            <button
              onClick={() => {
                setShowForm(true)
                setNewKey(null)
              }}
              className="rounded-full border border-cyan-300/30 bg-cyan-400/10 px-5 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/15"
            >
              Generate New API Key
            </button>
          )}
        </div>

        {showForm && (
          <form onSubmit={handleGenerate} className="mb-6 flex flex-wrap gap-3">
            <input
              autoFocus
              type="text"
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              placeholder="Service name (e.g. my-api)"
              maxLength={100}
              required
              className="min-w-0 flex-1 rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-cyan-400/50 focus:outline-none"
            />
            <button
              type="submit"
              disabled={generating || !serviceName.trim()}
              className="rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-5 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/15 disabled:opacity-50"
            >
              {generating ? 'Generating…' : 'Generate'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                setServiceName('')
              }}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300 transition hover:bg-white/10"
            >
              Cancel
            </button>
          </form>
        )}

        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-[1.25rem] border border-white/10 bg-white/5" />
            ))}
          </div>
        ) : keys.length === 0 ? (
          <p className="text-sm text-slate-400">No API keys yet. Generate one to start sending errors.</p>
        ) : (
          <div className="overflow-hidden rounded-[1.25rem] border border-white/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-5 py-3 text-left text-xs uppercase tracking-[0.2em] text-slate-500">
                    Service
                  </th>
                  <th className="px-5 py-3 text-left text-xs uppercase tracking-[0.2em] text-slate-500">
                    Created
                  </th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {keys.map((k) => (
                  <tr key={k.id}>
                    <td className="px-5 py-4">
                      <span className="font-medium text-white">{k.service_name}</span>
                      {k.description && (
                        <p className="mt-0.5 text-xs text-slate-400">{k.description}</p>
                      )}
                    </td>
                    <td className="px-5 py-4 text-slate-400">
                      {format(parseDate(k.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => handleRevoke(k.id)}
                        disabled={revoking === k.id}
                        className="rounded-lg border border-rose-400/20 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300 transition hover:bg-rose-500/20 disabled:opacity-50"
                      >
                        {revoking === k.id ? 'Revoking…' : 'Revoke'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
