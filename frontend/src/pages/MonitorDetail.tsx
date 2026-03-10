import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../lib/api'
import type { Monitor, Alert, Snapshot, Diff } from '../lib/types'
import { SEVERITY_COLORS, type SeverityLevel } from '../lib/types'
import {
  ArrowLeft,
  Clock,
  ExternalLink,
  Play,
  Pause,
  Settings,
  FileText,
  GitCompare,
  Bell,
} from 'lucide-react'

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

type Tab = 'alerts' | 'snapshots' | 'diffs'

export default function MonitorDetail() {
  const { id } = useParams<{ id: string }>()
  const [monitor, setMonitor] = useState<Monitor | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [diffs, setDiffs] = useState<Diff[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('alerts')
  const [triggering, setTriggering] = useState(false)

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.get(`/monitors/${id}`).catch(() => ({ data: null })),
      api.get(`/alerts?monitor_id=${id}&limit=20`).catch(() => ({ data: [] })),
      api.get(`/monitors/${id}/snapshots?limit=10`).catch(() => ({ data: [] })),
      api.get(`/monitors/${id}/diffs?limit=10`).catch(() => ({ data: [] })),
    ]).then(([m, a, s, d]) => {
      setMonitor(m.data)
      setAlerts(Array.isArray(a.data) ? a.data : a.data.items || [])
      setSnapshots(Array.isArray(s.data) ? s.data : s.data.items || [])
      setDiffs(Array.isArray(d.data) ? d.data : d.data.items || [])
      setLoading(false)
    })
  }, [id])

  const triggerScrape = async () => {
    if (!id) return
    setTriggering(true)
    try {
      await api.post(`/monitors/${id}/scrape`)
    } catch { /* ignore */ }
    setTriggering(false)
  }

  const toggleActive = async () => {
    if (!monitor || !id) return
    try {
      await api.patch(`/monitors/${id}`, { is_active: !monitor.is_active })
      setMonitor({ ...monitor, is_active: !monitor.is_active })
    } catch { /* ignore */ }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!monitor) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400">Monitor not found</p>
        <Link to="/monitors" className="text-teal-600 text-sm mt-2 inline-block">Back to monitors</Link>
      </div>
    )
  }

  const tabs: { key: Tab; label: string; icon: typeof Bell; count: number }[] = [
    { key: 'alerts', label: 'Alerts', icon: Bell, count: alerts.length },
    { key: 'snapshots', label: 'Snapshots', icon: FileText, count: snapshots.length },
    { key: 'diffs', label: 'Diffs', icon: GitCompare, count: diffs.length },
  ]

  return (
    <div className="max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <Link to="/monitors" className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 transition mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Monitors
      </Link>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-3 h-3 rounded-full ${
                !monitor.is_active ? 'bg-gray-300' :
                monitor.consecutive_failures > 2 ? 'bg-rose-400' :
                monitor.consecutive_failures > 0 ? 'bg-amber-400' : 'bg-teal-400'
              }`} />
              <h1 className="text-xl font-bold text-gray-900">{monitor.name}</h1>
              {!monitor.is_active && (
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-500">Paused</span>
              )}
            </div>
            <a
              href={monitor.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-400 hover:text-teal-600 transition flex items-center gap-1"
            >
              {monitor.url}
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <div className="flex items-center gap-5 mt-3 text-xs text-gray-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Every {monitor.check_interval_minutes} minutes
              </span>
              <span>Last checked: {timeAgo(monitor.last_checked_at)}</span>
              {monitor.last_change_at && (
                <span className="text-amber-600">Last change: {timeAgo(monitor.last_change_at)}</span>
              )}
              {monitor.css_selector && (
                <span className="px-2 py-0.5 rounded bg-gray-50 font-mono">{monitor.css_selector}</span>
              )}
              {monitor.render_js && (
                <span className="px-2 py-0.5 rounded bg-violet-50 text-violet-600 font-medium">JS Rendering</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={triggerScrape}
              disabled={triggering}
              className="flex items-center gap-1.5 px-4 py-2 bg-teal-50 text-teal-700 rounded-xl text-sm font-medium hover:bg-teal-100 transition disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              {triggering ? 'Running...' : 'Scrape Now'}
            </button>
            <button
              onClick={toggleActive}
              className="p-2 rounded-xl text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition"
              title={monitor.is_active ? 'Pause' : 'Resume'}
            >
              {monitor.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <Link
              to={`/monitors/${id}/edit`}
              className="p-2 rounded-xl text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition"
            >
              <Settings className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-white rounded-xl p-1 border border-gray-100 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              tab === t.key
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${
              tab === t.key ? 'bg-white/20' : 'bg-gray-100'
            }`}>
              {t.count}
            </span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-2xl border border-gray-100">
        {tab === 'alerts' && (
          alerts.length === 0 ? (
            <div className="p-12 text-center text-sm text-gray-400">No alerts for this monitor yet.</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {alerts.map((alert) => (
                <div key={alert.id} className="px-6 py-4 hover:bg-gray-50/50 transition">
                  <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${SEVERITY_COLORS[alert.severity as SeverityLevel] || SEVERITY_COLORS.low}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-sm font-medium text-gray-900 flex-1">{alert.title || alert.summary}</span>
                    <span className="text-xs text-gray-300">{timeAgo(alert.created_at)}</span>
                  </div>
                  {alert.summary && alert.title && (
                    <p className="text-xs text-gray-400 mt-1.5 ml-14">{alert.summary}</p>
                  )}
                </div>
              ))}
            </div>
          )
        )}

        {tab === 'snapshots' && (
          snapshots.length === 0 ? (
            <div className="p-12 text-center text-sm text-gray-400">No snapshots captured yet.</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {snapshots.map((snap) => (
                <div key={snap._id} className="px-6 py-4 hover:bg-gray-50/50 transition">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        Snapshot {snap._id.slice(-8)}
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">
                        {snap.scraper_type} &middot; HTTP {snap.status_code} &middot; {Math.round(snap.raw_html_length / 1024)}KB raw
                      </div>
                    </div>
                    <div className="text-xs text-gray-300">{timeAgo(snap.fetched_at)}</div>
                  </div>
                  <div className="mt-2 font-mono text-xs text-gray-400 truncate max-w-2xl">
                    {snap.content_hash}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {tab === 'diffs' && (
          diffs.length === 0 ? (
            <div className="p-12 text-center text-sm text-gray-400">No diffs computed yet.</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {diffs.map((d) => (
                <div key={d._id} className="px-6 py-4 hover:bg-gray-50/50 transition">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <GitCompare className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {d.hunks_count} {d.hunks_count === 1 ? 'hunk' : 'hunks'}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5 flex items-center gap-2">
                          <span className="text-green-600">+{d.lines_added}</span>
                          <span className="text-rose-600">-{d.lines_removed}</span>
                          {d.is_noise_only && (
                            <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">Noise only</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-300">{timeAgo(d.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  )
}
