import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  Clock3,
  Eye,
  FileText,
  Plus,
  Radar,
  ShieldCheck,
} from 'lucide-react'
import api from '../lib/api'
import type { Alert, Monitor, NoiseLearningOverviewItem } from '../lib/types'
import { SEVERITY_COLORS, alertTitle, type SeverityLevel } from '../lib/types'
import { extractItems, timeAgo } from '../lib/utils'

function nextCheckWindow(dateStr: string) {
  const diff = new Date(dateStr).getTime() - Date.now()
  const mins = Math.max(Math.round(diff / 60000), 0)
  if (mins <= 60) return `Due in ${mins}m`
  const hrs = Math.round(mins / 60)
  return `Due in ${hrs}h`
}

export default function Dashboard() {
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [noiseOverview, setNoiseOverview] = useState<NoiseLearningOverviewItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/monitors').catch(() => ({ data: [] })),
      api.get('/alerts?per_page=10').catch(() => ({ data: [] })),
      api.get('/noise-learning/overview?per_page=6').catch(() => ({ data: [] })),
    ]).then(([m, a, noise]) => {
      setMonitors(extractItems<Monitor>(m.data))
      setAlerts(extractItems<Alert>(a.data))
      setNoiseOverview(extractItems<NoiseLearningOverviewItem>(noise.data))
      setLoading(false)
    })
  }, [])

  const activeMonitors = monitors.filter((monitor) => monitor.is_active)
  const monitorsWithSnapshots = monitors.filter((monitor) => monitor.last_checked_at)
  const recentChanges = monitors.filter((monitor) => monitor.last_change_at).length
  const unackedAlerts = alerts.filter((alert) => !alert.is_acknowledged)
  const criticalAlerts = alerts.filter((alert) => alert.severity === 'critical')
  const healthyMonitors = activeMonitors.filter((monitor) => monitor.consecutive_failures === 0).length
  const monitorsRequiringReview = activeMonitors.filter((monitor) => monitor.consecutive_failures > 0)

  const stats = [
    {
      label: 'Active monitors',
      value: activeMonitors.length,
      supporting: `${healthyMonitors} healthy`,
      icon: Radar,
      iconTone: 'bg-blue-50 text-blue-700',
    },
    {
      label: 'Captured snapshots',
      value: monitorsWithSnapshots.length,
      supporting: `${recentChanges} recent changes`,
      icon: FileText,
      iconTone: 'bg-emerald-50 text-emerald-700',
    },
    {
      label: 'Open alerts',
      value: unackedAlerts.length,
      supporting: `${criticalAlerts.length} critical`,
      icon: Bell,
      iconTone: 'bg-amber-50 text-amber-700',
    },
    {
      label: 'Pages needing attention',
      value: monitorsRequiringReview.length,
      supporting: monitorsRequiringReview.length ? 'Review scrape failures' : 'No failures reported',
      icon: AlertTriangle,
      iconTone: 'bg-rose-50 text-rose-700',
    },
  ]

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="page-kicker">Overview</p>
          <h2 className="mt-3 page-title">Monitoring operations</h2>
          <p className="mt-3 page-subtitle">
            Review live coverage, recent diffs, and unresolved alerts from a layout that feels closer
            to an internal product dashboard than a design experiment.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Link to="/alerts" className="btn-secondary">
            Review alerts
          </Link>
          <Link to="/monitors/new" className="btn-primary">
            <Plus className="h-4 w-4" />
            Add monitor
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="metric-card">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-sm font-medium text-slate-500">{stat.label}</div>
                <div className="mt-3 text-4xl font-semibold text-slate-950">{stat.value}</div>
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${stat.iconTone}`}>
                <stat.icon className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-4 text-sm text-slate-600">{stat.supporting}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <div className="panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
            <div>
              <div className="text-lg font-semibold text-slate-950">Recent alerts</div>
              <div className="mt-1 text-sm text-slate-600">
                Latest changes routed into the review queue.
              </div>
            </div>
            <Link to="/alerts" className="btn-ghost">
              View all
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {alerts.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Bell className="mx-auto h-10 w-10 text-slate-300" />
              <div className="mt-4 text-base font-semibold text-slate-950">No alerts yet</div>
              <div className="mt-2 text-sm text-slate-600">
                Add a monitor and trigger a scrape to start generating reviewable events.
              </div>
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {alerts.slice(0, 6).map((alert) => (
                <Link
                  key={alert.id}
                  to="/alerts"
                  className="grid gap-4 px-6 py-4 hover:bg-slate-50/80 lg:grid-cols-[auto_1fr_auto]"
                >
                  <div className="flex items-center">
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
                    <div className="mt-1">{alert.is_acknowledged ? 'Acknowledged' : 'Pending review'}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Workflow status</div>
                <div className="text-sm text-slate-600">The core monitoring path at a glance.</div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">1. Configure monitors</div>
                  <div className="text-xs text-slate-500">Tracked sources with schedule and capture rules</div>
                </div>
                <div className="text-sm font-semibold text-slate-950">{activeMonitors.length}</div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">2. Capture snapshots</div>
                  <div className="text-xs text-slate-500">Monitors with at least one completed check</div>
                </div>
                <div className="text-sm font-semibold text-slate-950">{monitorsWithSnapshots.length}</div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-950">3. Review alerts</div>
                  <div className="text-xs text-slate-500">Unacknowledged alerts still waiting for triage</div>
                </div>
                <div className="text-sm font-semibold text-slate-950">{unackedAlerts.length}</div>
              </div>
            </div>
          </div>

          <div className="panel p-6">
            <div className="text-lg font-semibold text-slate-950">Upcoming checks</div>
            <div className="mt-1 text-sm text-slate-600">
              Next scheduled runs across active monitors.
            </div>

            {activeMonitors.length === 0 ? (
              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
                No active monitors scheduled yet.
              </div>
            ) : (
              <div className="mt-5 space-y-3">
                {activeMonitors
                  .slice()
                  .sort((left, right) => new Date(left.next_check_at).getTime() - new Date(right.next_check_at).getTime())
                  .slice(0, 4)
                  .map((monitor) => (
                    <Link
                      key={monitor.id}
                      to={`/monitors/${monitor.id}`}
                      className="flex items-start justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 hover:border-slate-300 hover:bg-white"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-slate-950">{monitor.name}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                          <Clock3 className="h-3.5 w-3.5" />
                          {nextCheckWindow(monitor.next_check_at)}
                        </div>
                      </div>
                      <div className="ml-4 text-xs text-slate-500">
                        Every {monitor.check_interval_hours}h
                      </div>
                    </Link>
                  ))}
              </div>
            )}
          </div>

          <div className="panel p-6">
            <div className="text-lg font-semibold text-slate-950">Adaptive noise intelligence</div>
            <div className="mt-1 text-sm text-slate-600">
              Monitor-specific learned patterns and weekly filtering impact.
            </div>

            {noiseOverview.length === 0 ? (
              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
                No learned patterns are active yet.
              </div>
            ) : (
              <div className="mt-5 space-y-3">
                {noiseOverview.map((item) => (
                  <Link
                    key={item.monitor_id}
                    to={`/monitors/${item.monitor_id}`}
                    className="flex items-start justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 hover:border-slate-300 hover:bg-white"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-950">{item.monitor_name}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {item.learned_patterns} learned · {item.active_patterns} active
                      </div>
                    </div>
                    <div className="ml-4 text-right">
                      <div className="text-sm font-semibold text-slate-950">{item.lines_filtered_7d} lines/week</div>
                      <div className="text-xs text-slate-500">
                        {(item.avg_confidence * 100).toFixed(0)}% confidence
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <div className="text-lg font-semibold text-slate-950">Monitor coverage</div>
            <div className="mt-1 text-sm text-slate-600">
              Quick view of active sources and recent scrape health.
            </div>
          </div>
          <Link to="/monitors" className="btn-ghost">
            Manage monitors
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {activeMonitors.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <Eye className="mx-auto h-10 w-10 text-slate-300" />
            <div className="mt-4 text-base font-semibold text-slate-950">No active monitors</div>
            <div className="mt-2 text-sm text-slate-600">
              Create your first monitor to start collecting snapshots and alerts.
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {activeMonitors.slice(0, 6).map((monitor) => (
              <Link
                key={monitor.id}
                to={`/monitors/${monitor.id}`}
                className="grid gap-4 px-6 py-4 hover:bg-slate-50/80 lg:grid-cols-[1.5fr_0.7fr_0.7fr]"
              >
                <div>
                  <div className="text-sm font-semibold text-slate-950">{monitor.name}</div>
                  <div className="mt-1 text-sm text-slate-600">{monitor.url}</div>
                </div>

                <div className="text-sm text-slate-600">
                  <div className="font-medium text-slate-950">{monitor.page_type}</div>
                  <div className="mt-1">
                    {monitor.last_change_at ? `Changed ${timeAgo(monitor.last_change_at)}` : 'No changes detected'}
                  </div>
                </div>

                <div className="text-sm text-slate-600">
                  <div className="font-medium text-slate-950">
                    {monitor.consecutive_failures > 0 ? 'Needs review' : 'Healthy'}
                  </div>
                  <div className="mt-1">
                    {monitor.last_checked_at ? `Checked ${timeAgo(monitor.last_checked_at)}` : 'Not checked yet'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
