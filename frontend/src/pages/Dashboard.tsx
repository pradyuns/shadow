import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import type { Monitor, Alert } from '../lib/types'
import { SEVERITY_COLORS, type SeverityLevel } from '../lib/types'
import { Activity, Eye, Bell, AlertTriangle, Plus, ArrowRight, Clock } from 'lucide-react'

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

export default function Dashboard() {
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/monitors').catch(() => ({ data: [] })),
      api.get('/alerts?limit=10').catch(() => ({ data: [] })),
    ]).then(([m, a]) => {
      setMonitors(Array.isArray(m.data) ? m.data : m.data.items || [])
      setAlerts(Array.isArray(a.data) ? a.data : a.data.items || [])
      setLoading(false)
    })
  }, [])

  const activeMonitors = monitors.filter((m) => m.is_active && !m.is_deleted)
  const recentChanges = monitors.filter((m) => m.last_change_at).length
  const unackedAlerts = alerts.filter((a) => !a.is_acknowledged)
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical')

  const stats = [
    { label: 'Active Monitors', value: activeMonitors.length, icon: Eye, color: 'text-teal-600', bg: 'bg-teal-50' },
    { label: 'Changes Detected', value: recentChanges, icon: Activity, color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'Open Alerts', value: unackedAlerts.length, icon: Bell, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Critical', value: criticalAlerts.length, icon: AlertTriangle, color: 'text-rose-600', bg: 'bg-rose-50' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">Your competitive intelligence at a glance</p>
        </div>
        <Link
          to="/monitors/new"
          className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-full text-sm font-semibold hover:bg-gray-800 transition"
        >
          <Plus className="w-4 h-4" />
          Add Monitor
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-2xl p-5 border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-400">{s.label}</span>
              <div className={`w-8 h-8 rounded-xl ${s.bg} flex items-center justify-center`}>
                <s.icon className={`w-4 h-4 ${s.color}`} />
              </div>
            </div>
            <div className="text-3xl font-bold text-gray-900">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent alerts */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-50">
            <h2 className="text-sm font-semibold text-gray-900">Recent Alerts</h2>
            <Link to="/alerts" className="text-xs text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {alerts.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Bell className="w-8 h-8 text-gray-200 mx-auto mb-3" />
              <p className="text-sm text-gray-400">No alerts yet. Add a monitor to get started.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {alerts.slice(0, 6).map((alert) => (
                <Link
                  key={alert.id}
                  to={`/alerts`}
                  className="flex items-center gap-3 px-6 py-3.5 hover:bg-gray-50/50 transition"
                >
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${SEVERITY_COLORS[alert.severity as SeverityLevel] || SEVERITY_COLORS.low}`}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <span className="text-sm text-gray-900 font-medium truncate flex-1">
                    {alert.title || alert.summary}
                  </span>
                  <span className="text-xs text-gray-300 shrink-0 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {timeAgo(alert.created_at)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Monitors overview */}
        <div className="bg-white rounded-2xl border border-gray-100">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-50">
            <h2 className="text-sm font-semibold text-gray-900">Monitors</h2>
            <Link to="/monitors" className="text-xs text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1">
              Manage <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {activeMonitors.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Eye className="w-8 h-8 text-gray-200 mx-auto mb-3" />
              <p className="text-sm text-gray-400 mb-3">No monitors yet</p>
              <Link
                to="/monitors/new"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 text-white rounded-full text-xs font-semibold hover:bg-gray-800 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                Add your first
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {activeMonitors.slice(0, 6).map((m) => (
                <Link
                  key={m.id}
                  to={`/monitors/${m.id}`}
                  className="flex items-center gap-3 px-6 py-3.5 hover:bg-gray-50/50 transition"
                >
                  <div className={`w-2 h-2 rounded-full shrink-0 ${m.consecutive_failures > 0 ? 'bg-amber-400' : 'bg-teal-400'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{m.name}</div>
                    <div className="text-xs text-gray-400 truncate">{m.url}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
