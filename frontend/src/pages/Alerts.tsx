import { useEffect, useState } from 'react'
import { Bell, Check, ChevronDown, ChevronRight, Filter, Layers, List, ShieldCheck, TriangleAlert } from 'lucide-react'
import api from '../lib/api'
import type { Alert, AlertCluster } from '../lib/types'
import { SEVERITY_COLORS, alertTitle, primaryAlertCategory, type SeverityLevel } from '../lib/types'
import { extractItems, timeAgo } from '../lib/utils'

const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low'] as const

function AlertRow({
  alert,
  acknowledgingId,
  onAcknowledge,
  indent = false,
}: {
  alert: Alert
  acknowledgingId: string | null
  onAcknowledge: (id: string) => void
  indent?: boolean
}) {
  return (
    <div
      className={`grid gap-4 px-6 py-5 lg:grid-cols-[auto_1.4fr_0.8fr_0.7fr_0.8fr] lg:items-center ${
        alert.is_acknowledged ? 'bg-slate-50/60' : 'bg-white'
      } ${indent ? 'pl-12' : ''}`}
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
            onClick={() => onAcknowledge(alert.id)}
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
  )
}

function ClusterRow({
  cluster,
  alerts,
  acknowledgingId,
  onAcknowledge,
}: {
  cluster: AlertCluster
  alerts: Alert[]
  acknowledgingId: string | null
  onAcknowledge: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const clusterAlerts = alerts.filter((a) => a.cluster_id === cluster.id)

  if (clusterAlerts.length === 0) return null

  return (
    <>
      <div
        onClick={() => setExpanded(!expanded)}
        className="grid cursor-pointer gap-4 bg-slate-25 px-6 py-5 transition-colors hover:bg-slate-50 lg:grid-cols-[auto_1.4fr_0.8fr_0.7fr_0.8fr] lg:items-center"
      >
        <div>
          <span
            className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${
              SEVERITY_COLORS[cluster.severity as SeverityLevel] || SEVERITY_COLORS.low
            }`}
          >
            {cluster.severity.toUpperCase()}
          </span>
        </div>

        <div>
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-slate-400" />
            )}
            <div className="text-sm font-semibold text-slate-950">{cluster.title}</div>
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700">
              <Layers className="h-3 w-3" />
              {cluster.alert_count} alerts
            </span>
          </div>
          <div className="ml-6 mt-2 text-sm text-slate-600">
            {cluster.categories.map((c: string) => c.replace('_', ' ')).join(', ')}
          </div>
        </div>

        <div className="text-sm text-slate-600">{cluster.competitor_name}</div>

        <div className="text-sm text-slate-600">{timeAgo(cluster.updated_at)}</div>

        <div className="flex justify-end">
          {cluster.is_resolved ? (
            <div className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600">
              <Check className="h-4 w-4" />
              Resolved
            </div>
          ) : (
            <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-700">
              Open
            </span>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-l-2 border-blue-100">
          {clusterAlerts.map((alert) => (
            <AlertRow
              key={alert.id}
              alert={alert}
              acknowledgingId={acknowledgingId}
              onAcknowledge={onAcknowledge}
              indent
            />
          ))}
        </div>
      )}
    </>
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [clusters, setClusters] = useState<AlertCluster[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [showAcked, setShowAcked] = useState(false)
  const [viewMode, setViewMode] = useState<'flat' | 'clustered'>('clustered')
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')

    const params = new URLSearchParams({ per_page: '50' })
    if (filter !== 'all') params.set('severity', filter)
    if (!showAcked) params.set('is_acknowledged', 'false')

    const alertsPromise = api.get(`/alerts?${params}`).then(({ data }) => extractItems<Alert>(data))

    const clustersPromise = api.get('/clusters?per_page=50').then(({ data }) => extractItems<AlertCluster>(data)).catch(() => [] as AlertCluster[])

    Promise.all([alertsPromise, clustersPromise])
      .then(([alertsData, clustersData]) => {
        setAlerts(alertsData)
        setClusters(clustersData)
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
  const clusterCount = clusters.filter((c) => !c.is_resolved).length

  // alerts without a cluster or whose cluster wasn't returned in the current fetch
  const clusterIds = new Set(clusters.map((c) => c.id))
  const unclusteredAlerts = alerts.filter((a) => !a.cluster_id || !clusterIds.has(a.cluster_id))

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
          Related changes from the same competitor are automatically grouped into clusters.
          Expand a cluster to see individual alerts, or switch to flat view.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Pending review</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{pendingCount}</div>
          <div className="mt-2 text-sm text-slate-600">Unacknowledged alerts still open</div>
        </div>
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Open clusters</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{clusterCount}</div>
          <div className="mt-2 text-sm text-slate-600">Grouped competitive events</div>
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

          <div className="flex items-center gap-2">
            <div className="flex overflow-hidden rounded-2xl border border-slate-200">
              <button
                type="button"
                onClick={() => setViewMode('clustered')}
                className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold ${
                  viewMode === 'clustered'
                    ? 'bg-slate-950 text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Layers className="h-3.5 w-3.5" />
                Clustered
              </button>
              <button
                type="button"
                onClick={() => setViewMode('flat')}
                className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold ${
                  viewMode === 'flat'
                    ? 'bg-slate-950 text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <List className="h-3.5 w-3.5" />
                Flat
              </button>
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
            <div>{viewMode === 'clustered' ? 'Event / Alert' : 'Alert'}</div>
            <div>{viewMode === 'clustered' ? 'Competitor' : 'Category'}</div>
            <div>Age</div>
            <div className="text-right">Action</div>
          </div>

          <div className="divide-y divide-slate-200">
            {viewMode === 'clustered' ? (
              <>
                {clusters.map((cluster) => (
                  <ClusterRow
                    key={cluster.id}
                    cluster={cluster}
                    alerts={alerts}
                    acknowledgingId={acknowledgingId}
                    onAcknowledge={acknowledge}
                  />
                ))}
                {unclusteredAlerts.map((alert) => (
                  <AlertRow
                    key={alert.id}
                    alert={alert}
                    acknowledgingId={acknowledgingId}
                    onAcknowledge={acknowledge}
                  />
                ))}
              </>
            ) : (
              alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  acknowledgingId={acknowledgingId}
                  onAcknowledge={acknowledge}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
