import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { Alert } from '../lib/types'
import { SEVERITY_COLORS, type SeverityLevel } from '../lib/types'
import { Bell, Check, Clock, Filter } from 'lucide-react'

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

  useEffect(() => {
    const params = new URLSearchParams({ limit: '50' })
    if (filter !== 'all') params.set('severity', filter)
    if (!showAcked) params.set('acknowledged', 'false')

    api.get(`/alerts?${params}`).then(({ data }) => {
      setAlerts(Array.isArray(data) ? data : data.items || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [filter, showAcked])

  const acknowledge = async (alertId: string) => {
    try {
      await api.post(`/alerts/${alertId}/acknowledge`)
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertId ? { ...a, is_acknowledged: true, acknowledged_at: new Date().toISOString() } : a
        )
      )
    } catch { /* ignore */ }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="text-sm text-gray-400 mt-1">
            {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <div className="flex items-center gap-1 bg-white rounded-xl p-1 border border-gray-100">
          {SEVERITIES.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition capitalize ${
                filter === s ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowAcked(!showAcked)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition ${
            showAcked ? 'bg-teal-50 border-teal-200 text-teal-700' : 'bg-white border-gray-100 text-gray-500'
          }`}
        >
          <Filter className="w-3.5 h-3.5" />
          {showAcked ? 'Showing all' : 'Hiding acknowledged'}
        </button>
      </div>

      {/* Alerts list */}
      {alerts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
          <Bell className="w-10 h-10 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">No alerts</h2>
          <p className="text-sm text-gray-400">
            {filter !== 'all'
              ? `No ${filter} alerts found. Try changing the filter.`
              : 'Alerts will appear here when changes are detected.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`bg-white rounded-2xl border border-gray-100 p-5 transition ${
                alert.is_acknowledged ? 'opacity-60' : 'hover:shadow-md hover:shadow-gray-100'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className={`mt-0.5 text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${SEVERITY_COLORS[alert.severity as SeverityLevel] || SEVERITY_COLORS.low}`}>
                  {alert.severity.toUpperCase()}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-gray-900 mb-0.5">
                    {alert.title || 'Change detected'}
                  </div>
                  <p className="text-sm text-gray-400 mb-2">{alert.summary}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {timeAgo(alert.created_at)}
                    </span>
                    {alert.category && (
                      <span className="px-2 py-0.5 rounded-full bg-gray-50">{alert.category}</span>
                    )}
                    {alert.is_acknowledged && (
                      <span className="text-teal-600 flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        Acknowledged
                      </span>
                    )}
                  </div>
                </div>
                {!alert.is_acknowledged && (
                  <button
                    onClick={() => acknowledge(alert.id)}
                    className="px-3 py-1.5 rounded-xl text-xs font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-900 transition border border-gray-100"
                  >
                    Acknowledge
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
