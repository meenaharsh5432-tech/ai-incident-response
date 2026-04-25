import { useState } from 'react'
import App from '../App'

const STORAGE_KEY = 'ai_ir_auth'

export default function PasswordGate() {
  const [authenticated, setAuthenticated] = useState(
    () => localStorage.getItem(STORAGE_KEY) === 'authenticated'
  )
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    if (password === import.meta.env.VITE_DASHBOARD_PASSWORD) {
      localStorage.setItem(STORAGE_KEY, 'authenticated')
      setAuthenticated(true)
    } else {
      setError('Incorrect password')
      setPassword('')
    }
  }

  function handleLock() {
    localStorage.removeItem(STORAGE_KEY)
    setAuthenticated(false)
    setPassword('')
    setError('')
  }

  if (authenticated) {
    return <App onLock={handleLock} />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="rounded-[2rem] border border-white/10 bg-slate-900/80 p-8 shadow-[0_40px_120px_rgba(2,6,23,0.6)] backdrop-blur-xl">
          <p className="text-xs uppercase tracking-[0.34em] text-cyan-300">AI Incident Response</p>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-white">Dashboard access</h1>
          <p className="mt-2 text-sm text-slate-400">Enter your password to continue.</p>

          <form onSubmit={handleSubmit} className="mt-7 space-y-4">
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError('') }}
              placeholder="Password"
              autoFocus
              className="w-full rounded-full border border-white/10 bg-slate-950/80 px-5 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-300/40 focus:outline-none"
            />

            {error && (
              <p className="px-1 text-xs text-rose-400">{error}</p>
            )}

            <button
              type="submit"
              className="w-full rounded-full bg-cyan-500/20 border border-cyan-300/30 px-5 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-500/30 active:scale-[0.98]"
            >
              Enter Dashboard
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
