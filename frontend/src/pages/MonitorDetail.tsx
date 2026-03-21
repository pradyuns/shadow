import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Bell,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileText,
  GitCompare,
  Pause,
  Play,
  RefreshCcw,
  Settings,
  ShieldCheck,
} from 'lucide-react'
import api from '../lib/api'
import type { Alert, Diff, Monitor, Snapshot } from '../lib/types'
import { SEVERITY_COLORS, alertTitle, type SeverityLevel } from '../lib/types'

type Tab = 'alerts' | 'snapshots' | 'diffs'

async function fetchMonitorDetail(id: string) {
  const [monitorResponse, alertResponse, snapshotResponse, diffResponse] = await Promise.all([
    api.get(`/monitors/${id}`).catch(() => ({ data: null })),
    api.get(`/alerts?monitor_id=${id}&per_page=20`).catch(() => ({ data: [] })),
    api.get(`/monitors/${id}/snapshots?per_page=10`).catch(() => ({ data: [] })),
    api.get(`/monitors/${id}/diffs?per_page=10`).catch(() => ({ data: [] })),
  ])

  return {
    monitor: monitorResponse.data as Monitor | null,
    alerts: Array.isArray(alertResponse.data) ? alertResponse.data : alertResponse.data.items || [],
    snapshots: Array.isArray(snapshotResponse.data)
      ? snapshotResponse.data
      : snapshotResponse.data.items || [],
    diffs: Array.isArray(diffResponse.data) ? diffResponse.data : diffResponse.data.items || [],
  }
}

function timeAgo(dateStr: string | null) {
  if (!dateStr) return 'Never'
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function scrapeTone(monitor: Monitor) {
  if (!monitor.is_active) return 'bg-slate-100 text-slate-600'
  if (monitor.consecutive_failures > 0) return 'bg-rose-50 text-rose-700'
  return 'bg-emerald-50 text-emerald-700'
}

export default function MonitorDetail() {
  const { id } = useParams<{ id: string }>()
  const [monitor, setMonitor] = useState<Monitor | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [diffs, setDiffs] = useState<Diff[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('alerts')
  const [triggering, setTriggering] = useState(false)
  const [updatingState, setUpdatingState] = useState(false)
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (!id) return

    fetchMonitorDetail(id).then((data) => {
      setMonitor(data.monitor)
      setAlerts(data.alerts)
      setSnapshots(data.snapshots)
      setDiffs(data.diffs)
      setLoading(false)
    })
  }, [id])

  const triggerScrape = async () => {
    if (!id) return

    setTriggering(true)
    setMessage(null)
    try {
      await api.post(`/monitors/${id}/scrape`)
      setMessage({
        tone: 'success',
        text: 'Scrape job queued. Refresh in a moment to review the latest snapshot and diff.',
      })
    } catch {
      setMessage({
        tone: 'error',
        text: 'Unable to queue a scrape job right now.',
      })
    } finally {
      setTriggering(false)
    }
  }

  const toggleActive = async () => {
    if (!monitor || !id) return

    setUpdatingState(true)
    setMessage(null)
    try {
      const { data } = await api.patch(`/monitors/${id}`, { is_active: !monitor.is_active })
      setMonitor(data)
      setMessage({
        tone: 'success',
        text: data.is_active ? 'Monitor resumed.' : 'Monitor paused.',
      })
    } catch {
      setMessage({
        tone: 'error',
        text: 'Unable to update monitor state.',
      })
    } finally {
      setUpdatingState(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!monitor) {
    return (
      <div className="panel px-6 py-14 text-center">
        <div className="text-lg font-semibold text-slate-950">Monitor not found</div>
        <div className="mt-2 text-sm text-slate-600">
          The requested monitor could not be loaded.
        </div>
        <Link to="/monitors" className="btn-primary mt-6">
          Back to monitors
        </Link>
      </div>
    )
  }

  const tabs: { key: Tab; label: string; icon: typeof Bell; count: number }[] = [
    { key: 'alerts', label: 'Alerts', icon: Bell, count: alerts.length },
    { key: 'snapshots', label: 'Snapshots', icon: FileText, count: snapshots.length },
    { key: 'diffs', label: 'Diffs', icon: GitCompare, count: diffs.length },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4">
        <Link to="/monitors" className="btn-ghost w-fit">
          <ArrowLeft className="h-4 w-4" />
          Back to monitors
        </Link>

        <div className="panel p-8">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <p className="page-kicker">Monitor detail</p>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${scrapeTone(monitor)}`}>
                  {monitor.is_active ? 'Active' : 'Paused'}
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                  {monitor.page_type}
                </span>
              </div>

              <h2 className="mt-3 text-3xl font-semibold text-slate-950">{monitor.name}</h2>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-600">
                <a
                  href={monitor.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-blue-700"
                >
                  {monitor.url}
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
                {monitor.competitor_name && (
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    {monitor.competitor_name}
                  </span>
                )}
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Cadence</div>
                  <div className="mt-2 text-sm font-semibold text-slate-950">
                    Every {monitor.check_interval_hours}h
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    Next run {timeAgo(monitor.next_check_at)}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Last check</div>
                  <div className="mt-2 text-sm font-semibold text-slate-950">
                    {timeAgo(monitor.last_checked_at)}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    Status: {monitor.last_scrape_status || 'Unknown'}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Last change</div>
                  <div className="mt-2 text-sm font-semibold text-slate-950">
                    {timeAgo(monitor.last_change_at)}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    {diffs.length} diff{diffs.length !== 1 ? 's' : ''} recorded
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Capture scope</div>
                  <div className="mt-2 text-sm font-semibold text-slate-950">
                    {monitor.css_selector || 'Full page'}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    {monitor.render_js ? 'JavaScript rendering enabled' : 'Standard HTML capture'}
                  </div>
                </div>
              </div>

              {monitor.last_scrape_error && (
                <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  Last scrape error: {monitor.last_scrape_error}
                </div>
              )}

              {message && (
                <div
                  className={`mt-6 rounded-2xl px-4 py-3 text-sm ${
                    message.tone === 'success'
                      ? 'border border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border border-rose-200 bg-rose-50 text-rose-700'
                  }`}
                >
                  {message.text}
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 xl:justify-end">
              <button type="button" onClick={triggerScrape} disabled={triggering} className="btn-primary">
                <RefreshCcw className="h-4 w-4" />
                {triggering ? 'Queueing...' : 'Scrape now'}
              </button>
              <button
                type="button"
                onClick={toggleActive}
                disabled={updatingState}
                className="btn-secondary"
              >
                {monitor.is_active ? (
                  <>
                    <Pause className="h-4 w-4" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Resume
                  </>
                )}
              </button>
              <Link to={`/monitors/${monitor.id}/edit`} className="btn-secondary">
                <Settings className="h-4 w-4" />
                Edit
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.7fr_1.3fr]">
        <div className="space-y-6">
          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Monitor health</div>
                <div className="text-sm text-slate-600">A concise operational summary.</div>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Alerts pending</div>
                  <div className="text-xs text-slate-500">Unacknowledged items for this source</div>
                </div>
                <div className="text-sm font-semibold text-slate-950">
                  {alerts.filter((alert) => !alert.is_acknowledged).length}
                </div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Snapshots stored</div>
                  <div className="text-xs text-slate-500">Recent capture history</div>
                </div>
                <div className="text-sm font-semibold text-slate-950">{snapshots.length}</div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Consecutive failures</div>
                  <div className="text-xs text-slate-500">Useful for identifying broken capture paths</div>
                </div>
                <div className="text-sm font-semibold text-slate-950">{monitor.consecutive_failures}</div>
              </div>
            </div>
          </div>

          <div className="panel p-6">
            <div className="text-lg font-semibold text-slate-950">What this view improves</div>
            <div className="mt-5 space-y-3">
              {[
                'State, cadence, and scrape health are visible before diving into tabs.',
                'Manual scrape actions give feedback instead of silently doing nothing.',
                'Snapshots, alerts, and diffs stay together around one monitor record.',
              ].map((item) => (
                <div key={item} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                  <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tabItem) => (
              <button
                key={tabItem.key}
                type="button"
                onClick={() => setTab(tabItem.key)}
                className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold ${
                  tab === tabItem.key
                    ? 'bg-slate-950 text-white'
                    : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <tabItem.icon className="h-4 w-4" />
                {tabItem.label}
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] ${
                    tab === tabItem.key ? 'bg-white/15 text-white' : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {tabItem.count}
                </span>
              </button>
            ))}
          </div>

          <div className="panel overflow-hidden">
            {tab === 'alerts' && (
              <>
                {alerts.length === 0 ? (
                  <div className="px-6 py-12 text-center">
                    <Bell className="mx-auto h-10 w-10 text-slate-300" />
                    <div className="mt-4 text-base font-semibold text-slate-950">No alerts yet</div>
                    <div className="mt-2 text-sm text-slate-600">
                      Alerts for this monitor will appear here after a meaningful change is detected.
                    </div>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-200">
                    {alerts.map((alert) => (
                      <div key={alert.id} className="grid gap-4 px-6 py-4 lg:grid-cols-[auto_1fr_auto]">
                        <div>
                          <span
                            className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                              SEVERITY_COLORS[alert.severity as SeverityLevel] || SEVERITY_COLORS.low
                            }`}
                          >
                            {alert.severity.toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-slate-950">
                            {alertTitle(alert)}
                          </div>
                          <div className="mt-1 text-sm text-slate-600">{alert.summary}</div>
                        </div>
                        <div className="text-right text-xs text-slate-500">
                          <div>{timeAgo(alert.created_at)}</div>
                          <div className="mt-1">
                            {alert.is_acknowledged ? 'Acknowledged' : 'Awaiting review'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {tab === 'snapshots' && (
              <>
                {snapshots.length === 0 ? (
                  <div className="px-6 py-12 text-center">
                    <FileText className="mx-auto h-10 w-10 text-slate-300" />
                    <div className="mt-4 text-base font-semibold text-slate-950">No snapshots captured</div>
                    <div className="mt-2 text-sm text-slate-600">
                      Trigger a scrape or wait for the next scheduled run.
                    </div>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-200">
                    {snapshots.map((snapshot) => (
                      <div key={snapshot.id} className="grid gap-4 px-6 py-4 lg:grid-cols-[1fr_auto]">
                        <div>
                          <div className="text-sm font-semibold text-slate-950">
                            Snapshot {snapshot.id.slice(-8)}
                          </div>
                          <div className="mt-1 text-sm text-slate-600">
                            {snapshot.render_method || 'Unknown render method'} · HTTP {snapshot.http_status ?? 'n/a'} ·{' '}
                            {snapshot.fetch_duration_ms ? `${snapshot.fetch_duration_ms} ms` : 'timing unavailable'}
                          </div>
                          <div className="mt-2 font-mono text-xs text-slate-500">
                            {snapshot.text_hash || 'No text hash recorded'}
                          </div>
                        </div>
                        <div className="text-right text-xs text-slate-500">
                          <div className="inline-flex items-center gap-1">
                            <Clock3 className="h-3.5 w-3.5" />
                            {timeAgo(snapshot.created_at)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {tab === 'diffs' && (
              <>
                {diffs.length === 0 ? (
                  <div className="px-6 py-12 text-center">
                    <GitCompare className="mx-auto h-10 w-10 text-slate-300" />
                    <div className="mt-4 text-base font-semibold text-slate-950">No diffs available</div>
                    <div className="mt-2 text-sm text-slate-600">
                      Diffs appear once at least two snapshots are available for comparison.
                    </div>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-200">
                    {diffs.map((diff) => (
                      <div key={diff.id} className="grid gap-4 px-6 py-4 lg:grid-cols-[1fr_auto]">
                        <div>
                          <div className="flex flex-wrap items-center gap-3">
                            <div className="text-sm font-semibold text-slate-950">
                              {diff.is_empty_after_filter ? 'Noise-only diff' : 'Meaningful diff'}
                            </div>
                            {diff.is_empty_after_filter && (
                              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                                Noise only
                              </span>
                            )}
                          </div>
                          <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
                            <span className="text-emerald-700">+{diff.diff_lines_added} lines added</span>
                            <span className="text-rose-700">-{diff.diff_lines_removed} lines removed</span>
                            <span>{diff.noise_lines_removed} noise lines filtered</span>
                          </div>
                        </div>
                        <div className="text-right text-xs text-slate-500">
                          <div className="inline-flex items-center gap-1">
                            <Clock3 className="h-3.5 w-3.5" />
                            {timeAgo(diff.created_at)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
