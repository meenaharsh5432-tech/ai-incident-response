import { useCallback, useEffect, useMemo, useState } from 'react'
import { format, formatDistanceToNow } from 'date-fns'
import { parseDate } from './utils/date'
import StatsCard from './components/StatsCard'
import IncidentList from './components/IncidentList'
import IncidentDetail from './components/IncidentDetail'
import ErrorRateGraph from './components/ErrorRateGraph'
import MTTRChart from './components/MTTRChart'
import APIKeys from './components/APIKeys'
import { getErrorMessage, getHealth, getIncident, getIncidents, getStats } from './api/client'

const TABS = ['Overview', 'Active', 'Resolved', 'API Keys']

function fmtDuration(seconds) {
  if (seconds == null) return '--'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

function Panel({ title, eyebrow, children, action }) {
  return (
    <section className="rounded-[1.9rem] border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          {eyebrow && <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{eyebrow}</p>}
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-white">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export default function App() {
  const [tab, setTab] = useState('Overview')
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [now, setNow] = useState(() => new Date())
  const [incidents, setIncidents] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedIncident, setSelectedIncident] = useState(null)
  const [loadingOverview, setLoadingOverview] = useState(true)
  const [loadingIncidents, setLoadingIncidents] = useState(true)
  const [loadingSelected, setLoadingSelected] = useState(false)
  const [overviewError, setOverviewError] = useState('')
  const [incidentsError, setIncidentsError] = useState('')
  const [selectedError, setSelectedError] = useState('')
  const [activeKey, setActiveKey] = useState(null)
  const [snippetLang, setSnippetLang] = useState('python')

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true)
    setOverviewError('')

    try {
      const [statsData, healthData] = await Promise.all([getStats(), getHealth()])
      setStats(statsData)
      setHealth(healthData)
    } catch (error) {
      setOverviewError(getErrorMessage(error, 'Unable to load dashboard data.'))
    } finally {
      setLoadingOverview(false)
    }
  }, [])

  const loadIncidents = useCallback(async () => {
    setLoadingIncidents(true)
    setIncidentsError('')

    try {
      const status = tab === 'Resolved' ? 'resolved' : tab === 'Active' ? 'active' : undefined
      const data = await getIncidents({ status, page, page_size: 20 })
      setIncidents(data.items)
      setTotal(data.total)
    } catch (error) {
      setIncidentsError(getErrorMessage(error, 'Unable to load incidents.'))
    } finally {
      setLoadingIncidents(false)
    }
  }, [page, tab])

  const loadSelectedIncident = useCallback(async () => {
    if (!selectedId) {
      setSelectedIncident(null)
      setSelectedError('')
      return
    }

    setLoadingSelected(true)
    setSelectedError('')

    try {
      const incident = await getIncident(selectedId)
      setSelectedIncident(incident)
    } catch (error) {
      setSelectedIncident(null)
      setSelectedError(getErrorMessage(error, 'Unable to load incident detail.'))
    } finally {
      setLoadingSelected(false)
    }
  }, [selectedId])

  const refreshAll = useCallback(() => {
    loadOverview()
    if (tab !== 'Overview') {
      loadIncidents()
    }
    loadSelectedIncident()
  }, [loadIncidents, loadOverview, loadSelectedIncident, tab])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  useEffect(() => {
    if (tab === 'Overview') return
    loadIncidents()
  }, [loadIncidents, tab])

  useEffect(() => {
    loadSelectedIncident()
  }, [loadSelectedIncident])

  useEffect(() => {
    if (tab === 'Overview') return

    if (incidents.length === 0) {
      setSelectedId(null)
      return
    }

    if (!selectedId || !incidents.some((incident) => incident.id === selectedId)) {
      setSelectedId(incidents[0].id)
    }
  }, [incidents, selectedId, tab])

  useEffect(() => {
    const timer = setInterval(() => {
      refreshAll()
    }, 30000)

    return () => clearInterval(timer)
  }, [refreshAll])

  useEffect(() => {
    const clockTimer = setInterval(() => {
      setNow(new Date())
    }, 1000)

    return () => clearInterval(clockTimer)
  }, [])

  function handleSelect(id) {
    setSelectedId(id)
    setSelectedIncident(null)
  }

  const summary = useMemo(() => {
    if (!stats) return []

    return [
      {
        label: 'Active incidents',
        value: stats.active_incidents,
        sub: `${stats.errors_last_hour} new errors in the last hour`,
        color: 'red',
        icon: 'activity',
      },
      {
        label: 'Critical now',
        value: stats.critical_incidents,
        sub: 'Highest-priority clusters still open',
        color: 'amber',
        icon: 'alert',
      },
      {
        label: 'Resolved in 24h',
        value: stats.resolved_last_24h,
        sub: 'Operational throughput for the last day',
        color: 'green',
        icon: 'check',
      },
      {
        label: 'Average MTTR',
        value: fmtDuration(stats.avg_mttr_seconds),
        sub: 'Mean time to resolution across resolved incidents',
        color: 'blue',
        icon: 'clock',
      },
    ]
  }, [stats])

  const lastUpdated = stats?.last_updated ? format(parseDate(stats.last_updated), 'MMM d, HH:mm:ss') : null
  const liveNow = format(now, 'MMM d, HH:mm:ss')
  const syncLabel = stats?.last_updated
    ? `${formatDistanceToNow(parseDate(stats.last_updated), { addSuffix: true })}`
    : 'Waiting for first backend response.'
  const selectedTabLabel = tab === 'Resolved' ? 'resolved' : 'active'

  return (
    <div className="min-h-screen px-4 py-4 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/70 px-6 py-7 shadow-[0_40px_120px_rgba(2,6,23,0.45)] backdrop-blur-xl">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-[0.34em] text-cyan-300">AI Incident Response</p>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Beautiful ops visibility, grounded in the live backend.
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
                Track active incidents, inspect AI-assisted diagnosis, and move from alert to resolution with a frontend that reflects backend state clearly instead of hiding failures.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">API health</p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {health?.status === 'ok' ? 'Connected' : 'Checking'}
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  {health?.status === 'ok' ? `Live at ${liveNow}` : 'FastAPI is being checked from the client.'}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Last sync</p>
                <p className="mt-2 text-lg font-semibold text-white">{lastUpdated || '--'}</p>
                <p className="mt-1 text-sm text-slate-400">{syncLabel}</p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm">
            <a
              href="http://localhost:9090"
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200 transition hover:bg-white/10"
            >
              Prometheus
            </a>
            <a
              href="http://localhost:3001"
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200 transition hover:bg-white/10"
            >
              Grafana
            </a>
            <button
              onClick={refreshAll}
              className="rounded-full border border-cyan-300/30 bg-cyan-400/10 px-4 py-2 text-cyan-100 transition hover:bg-cyan-400/15"
            >
              Refresh now
            </button>
            {selectedIncident?.last_seen && (
              <span className="text-sm text-slate-400">
                Selected incident updated{' '}
                {formatDistanceToNow(parseDate(selectedIncident.last_seen), { addSuffix: true })}
              </span>
            )}
          </div>
        </header>

        <nav className="mt-6 flex flex-wrap gap-2">
          {TABS.map((item) => (
            <button
              key={item}
              onClick={() => {
                setTab(item)
                setPage(1)
                if (item === 'Overview') {
                  setSelectedId(null)
                  setSelectedIncident(null)
                }
              }}
              className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${
                tab === item
                  ? 'bg-white text-slate-950'
                  : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
              }`}
            >
              {item}
            </button>
          ))}
        </nav>

        {overviewError && (
          <div className="mt-6 rounded-[1.5rem] border border-rose-400/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
            {overviewError}
          </div>
        )}

        <main className="mt-6 space-y-6">
          {tab === 'Overview' && (
            <>
              {loadingOverview && !stats ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <div key={index} className="h-40 animate-pulse rounded-[1.75rem] border border-white/10 bg-white/5" />
                  ))}
                </div>
              ) : stats ? (
                <>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {summary.map((item) => (
                      <StatsCard key={item.label} {...item} />
                    ))}
                  </div>

                  <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                    <div className="space-y-6">
                      <div className="grid gap-6 lg:grid-cols-2">
                        <ErrorRateGraph data={stats.error_timeline} />
                        <MTTRChart data={stats.mttr_by_service} />
                      </div>

                      <Panel title="Service pressure" eyebrow="24-hour distribution">
                        {stats.errors_by_service.length === 0 ? (
                          <p className="text-sm text-slate-400">No recent service errors were found.</p>
                        ) : (
                          <div className="space-y-4">
                            {stats.errors_by_service.map((service, index) => {
                              const max = Math.max(...stats.errors_by_service.map((entry) => entry.count), 1)
                              return (
                                <div key={service.service}>
                                  <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                                    <span className="font-medium text-white">{service.service}</span>
                                    <span className="text-slate-400">{service.count} events</span>
                                  </div>
                                  <div className="h-3 rounded-full bg-slate-900">
                                    <div
                                      className="h-3 rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-amber-300"
                                      style={{
                                        width: `${Math.max((service.count / max) * 100, 8)}%`,
                                        opacity: Math.max(0.45, 1 - index * 0.08),
                                      }}
                                    />
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </Panel>
                    </div>

                    <Panel title="Recent active incidents" eyebrow="Live queue">
                      {stats.recent_incidents?.length ? (
                        <div className="space-y-3">
                          {stats.recent_incidents.map((incident) => (
                            <button
                              key={incident.id}
                              onClick={() => {
                                setTab('Active')
                                setPage(1)
                                handleSelect(incident.id)
                              }}
                              className="w-full rounded-[1.5rem] border border-white/10 bg-white/5 p-4 text-left transition hover:border-cyan-300/30 hover:bg-cyan-400/10"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <p className="text-sm font-semibold text-white">{incident.error_type}</p>
                                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                                    {incident.service_name}
                                  </p>
                                </div>
                                <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-rose-100">
                                  {incident.severity}
                                </span>
                              </div>
                              <div className="mt-4 flex items-center justify-between text-sm text-slate-400">
                                <span>{incident.occurrence_count}x occurrences</span>
                                <span>{formatDistanceToNow(parseDate(incident.last_seen), { addSuffix: true })}</span>
                              </div>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-400">No active incidents right now.</p>
                      )}
                    </Panel>
                  </div>

                  <section className="rounded-[1.9rem] border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
                    <div className="mb-5 flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Integration</p>
                        <h2 className="mt-2 text-xl font-semibold tracking-tight text-white">Get Started</h2>
                        <p className="mt-1 text-sm text-slate-400">
                          {activeKey
                            ? 'Copy the snippet below — your API key is pre-filled.'
                            : 'Generate an API key on the API Keys tab to auto-fill your key here.'}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {['python', 'node'].map((lang) => (
                          <button
                            key={lang}
                            onClick={() => setSnippetLang(lang)}
                            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                              snippetLang === lang
                                ? 'bg-white text-slate-950'
                                : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                            }`}
                          >
                            {lang === 'python' ? 'Python' : 'Node.js'}
                          </button>
                        ))}
                      </div>
                    </div>
                    <pre className="overflow-x-auto rounded-xl bg-slate-900 px-5 py-4 text-sm leading-7 text-slate-200">
                      {snippetLang === 'python' ? (
                        <code>{`from incident_reporter import IncidentReporter\nreporter = IncidentReporter(\n    api_url="https://your-domain.com",\n    service_name="your-service",\n    api_key="${activeKey ?? '<YOUR_API_KEY>'}"\n)\nreporter.setup_fastapi(app)`}</code>
                      ) : (
                        <code>{`const { IncidentReporter } = require('incident-reporter')\nconst reporter = new IncidentReporter({\n    apiUrl: 'https://your-domain.com',\n    serviceName: 'your-service',\n    apiKey: '${activeKey ?? '<YOUR_API_KEY>'}'\n})\napp.use(reporter.middleware())`}</code>
                      )}
                    </pre>
                    {!activeKey && (
                      <button
                        onClick={() => setTab('API Keys')}
                        className="mt-4 rounded-full border border-cyan-300/30 bg-cyan-400/10 px-5 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/15"
                      >
                        Generate API Key →
                      </button>
                    )}
                  </section>
                </>
              ) : (
                <Panel title="Dashboard unavailable" eyebrow="Connection state">
                  <p className="text-sm text-slate-400">The backend did not return overview data yet.</p>
                </Panel>
              )}
            </>
          )}

          {tab === 'API Keys' && (
            <APIKeys onKeyCreated={(key) => setActiveKey(key)} />
          )}

          {(tab === 'Active' || tab === 'Resolved') && (
            <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
              <Panel
                title={`${total} ${selectedTabLabel} incident${total === 1 ? '' : 's'}`}
                eyebrow="Incident queue"
                action={<span className="text-sm text-slate-400">Page {page}</span>}
              >
                {incidentsError && (
                  <div className="mb-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    {incidentsError}
                  </div>
                )}

                {loadingIncidents ? (
                  <div className="space-y-3">
                    {Array.from({ length: 5 }).map((_, index) => (
                      <div key={index} className="h-28 animate-pulse rounded-[1.5rem] border border-white/10 bg-white/5" />
                    ))}
                  </div>
                ) : (
                  <IncidentList incidents={incidents} onSelect={handleSelect} selectedId={selectedId} />
                )}

                {total > 20 && (
                  <div className="mt-5 flex items-center justify-between gap-3">
                    <button
                      onClick={() => setPage((current) => Math.max(1, current - 1))}
                      disabled={page === 1}
                      className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10 disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage((current) => current + 1)}
                      disabled={page * 20 >= total}
                      className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                )}
              </Panel>

              <div>
                {selectedError && (
                  <div className="mb-4 rounded-[1.5rem] border border-rose-400/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
                    {selectedError}
                  </div>
                )}

                {loadingSelected && selectedId ? (
                  <div className="h-80 animate-pulse rounded-[1.9rem] border border-white/10 bg-white/5" />
                ) : selectedIncident ? (
                  <IncidentDetail
                    incident={selectedIncident}
                    onResolved={() => {
                      loadOverview()
                      loadIncidents()
                      loadSelectedIncident()
                    }}
                    onDiagnosed={setSelectedIncident}
                    onFeedback={loadOverview}
                  />
                ) : (
                  <Panel title="Select an incident" eyebrow="Detail view">
                    <p className="text-sm text-slate-400">
                      Choose an incident from the queue to inspect diagnosis, evidence, and resolution workflow.
                    </p>
                  </Panel>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
