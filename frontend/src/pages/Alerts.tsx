import { useEffect, useState } from 'react'
import { Bell, Check, Filter, ShieldCheck, TriangleAlert } from 'lucide-react'
import api from '../lib/api'
import type { Alert } from '../lib/types'
import { SEVERITY_COLORS, alertTitle, primaryAlertCategory, type SeverityLevel } from '../lib/types'

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low'] as const

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [showAcked, setShowAcked] = useState(false)
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')

    const params = new URLSearchParams({ per_page: '50' })
    if (filter !== 'all') params.set('severity', filter)
    if (!showAcked) params.set('is_acknowledged', 'false')

    api
      .get(`/alerts?${params}`)
      .then(({ data }) => {
        setAlerts(Array.isArray(data) ? data : data.items || [])
        setLoading(false)
      })
      .catch(() => {
        setError('Unable to load alerts right now.')
        setLoading(false)
      })
  }, [filter, showAcked])

  const acknowledge = async (alertId: string) => {
    setAcknowledgingId(alertId)
    setError('')

    try {
      await api.patch(`/alerts/${alertId}/acknowledge`)
      setAlerts((previous) =>
        previous.map((alert) =>
          alert.id === alertId
            ? { ...alert, is_acknowledged: true, acknowledged_at: new Date().toISOString() }
            : alert,
        ),
      )
    } catch {
      setError('Unable to acknowledge this alert.')
    } finally {
      setAcknowledgingId(null)
    }
  }

  const criticalCount = alerts.filter((alert) => alert.severity === 'critical').length
  const highCount = alerts.filter((alert) => alert.severity === 'high').length
  const pendingCount = alerts.filter((alert) => !alert.is_acknowledged).length

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="max-w-3xl">
        <p className="page-kicker">Alerts</p>
        <h2 className="mt-3 page-title">Change review queue</h2>
        <p className="mt-3 page-subtitle">
          Triage meaningful changes, acknowledge what has been reviewed, and keep severity visible for recruiters or hiring managers scanning the product.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Pending review</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{pendingCount}</div>
          <div className="mt-2 text-sm text-slate-600">Unacknowledged alerts still open</div>
        </div>
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Critical alerts</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{criticalCount}</div>
          <div className="mt-2 text-sm text-slate-600">Highest-priority items in the current view</div>
        </div>
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">High severity</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{highCount}</div>
          <div className="mt-2 text-sm text-slate-600">Still meaningful, usually worth a same-day review</div>
        </div>
      </div>

      <div className="panel p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {SEVERITIES.map((severity) => (
              <button
                key={severity}
                type="button"
                onClick={() => setFilter(severity)}
                className={`rounded-2xl px-4 py-2 text-sm font-semibold capitalize ${
                  filter === severity
                    ? 'bg-slate-950 text-white'
                    : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {severity}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setShowAcked(!showAcked)}
            className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold ${
              showAcked
                ? 'bg-blue-50 text-blue-700'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            <Filter className="h-4 w-4" />
            {showAcked ? 'Showing acknowledged' : 'Hide acknowledged'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="panel px-6 py-14 text-center">
          <Bell className="mx-auto h-10 w-10 text-slate-300" />
          <div className="mt-4 text-lg font-semibold text-slate-950">No alerts in this view</div>
          <div className="mt-2 text-sm text-slate-600">
            Try adjusting the filters or wait for the next monitoring cycle to finish.
          </div>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="hidden grid-cols-[auto_1.4fr_0.8fr_0.7fr_0.8fr] gap-4 border-b border-slate-200 px-6 py-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 lg:grid">
            <div>Severity</div>
            <div>Alert</div>
            <div>Category</div>
            <div>Age</div>
            <div className="text-right">Action</div>
          </div>

          <div className="divide-y divide-slate-200">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`grid gap-4 px-6 py-5 lg:grid-cols-[auto_1.4fr_0.8fr_0.7fr_0.8fr] lg:items-center ${
                  alert.is_acknowledged ? 'bg-slate-50/60' : 'bg-white'
                }`}
              >
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
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-sm font-semibold text-slate-950">
                      {alertTitle(alert)}
                    </div>
                    {alert.is_acknowledged && (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                        Reviewed
                      </span>
                    )}
                  </div>
                  <div className="mt-2 text-sm text-slate-600">{alert.summary}</div>
                </div>

                <div className="text-sm text-slate-600">
                  <div className="inline-flex items-center gap-2">
                    {alert.severity === 'critical' ? (
                      <TriangleAlert className="h-4 w-4 text-rose-600" />
                    ) : (
                      <ShieldCheck className="h-4 w-4 text-slate-400" />
                    )}
                    <span>{primaryAlertCategory(alert)}</span>
                  </div>
                </div>

                <div className="text-sm text-slate-600">{timeAgo(alert.created_at)}</div>

                <div className="flex justify-end">
                  {!alert.is_acknowledged ? (
                    <button
                      type="button"
                      onClick={() => acknowledge(alert.id)}
                      disabled={acknowledgingId === alert.id}
                      className="btn-secondary"
                    >
                      <Check className="h-4 w-4" />
                      {acknowledgingId === alert.id ? 'Saving...' : 'Acknowledge'}
                    </button>
                  ) : (
                    <div className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600">
                      <Check className="h-4 w-4" />
                      Acknowledged
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
