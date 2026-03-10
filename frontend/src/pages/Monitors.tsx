import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import type { Monitor } from '../lib/types'
import { Eye, Plus, Search, Clock, ExternalLink, Pause, Play } from 'lucide-react'

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

export default function Monitors() {
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    api.get('/monitors').then(({ data }) => {
      setMonitors(Array.isArray(data) ? data : data.items || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const toggleActive = async (id: string, currentState: boolean) => {
    try {
      await api.patch(`/monitors/${id}`, { is_active: !currentState })
      setMonitors((prev) =>
        prev.map((m) => (m.id === id ? { ...m, is_active: !currentState } : m))
      )
    } catch { /* ignore */ }
  }

  const filtered = monitors
    .filter((m) => !m.is_deleted)
    .filter((m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.url.toLowerCase().includes(search.toLowerCase())
    )

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
          <h1 className="text-2xl font-bold text-gray-900">Monitors</h1>
          <p className="text-sm text-gray-400 mt-1">{filtered.length} competitor pages tracked</p>
        </div>
        <Link
          to="/monitors/new"
          className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-full text-sm font-semibold hover:bg-gray-800 transition"
        >
          <Plus className="w-4 h-4" />
          Add Monitor
        </Link>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search monitors..."
          className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
        />
      </div>

      {/* Monitors list */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
          <Eye className="w-10 h-10 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">No monitors yet</h2>
          <p className="text-sm text-gray-400 mb-6 max-w-sm mx-auto">
            Add a competitor's URL to start tracking changes automatically.
          </p>
          <Link
            to="/monitors/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-full text-sm font-semibold hover:bg-gray-800 transition"
          >
            <Plus className="w-4 h-4" />
            Add Your First Monitor
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((m) => (
            <div
              key={m.id}
              className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-md hover:shadow-gray-100 transition group"
            >
              <div className="flex items-start gap-4">
                {/* Status indicator */}
                <div className={`mt-1.5 w-2.5 h-2.5 rounded-full shrink-0 ${
                  !m.is_active ? 'bg-gray-300' :
                  m.consecutive_failures > 2 ? 'bg-rose-400' :
                  m.consecutive_failures > 0 ? 'bg-amber-400' : 'bg-teal-400'
                }`} />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Link
                      to={`/monitors/${m.id}`}
                      className="text-sm font-semibold text-gray-900 hover:text-teal-600 transition truncate"
                    >
                      {m.name}
                    </Link>
                    {!m.is_active && (
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                        Paused
                      </span>
                    )}
                  </div>
                  <a
                    href={m.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-gray-400 hover:text-teal-600 transition flex items-center gap-1 truncate"
                  >
                    {m.url}
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Every {m.check_interval_minutes}m
                    </span>
                    <span>Checked {timeAgo(m.last_checked_at)}</span>
                    {m.last_change_at && (
                      <span className="text-amber-600">Changed {timeAgo(m.last_change_at)}</span>
                    )}
                    {m.render_js && (
                      <span className="px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 font-medium">JS</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                  <button
                    onClick={() => toggleActive(m.id, m.is_active)}
                    className={`p-2 rounded-xl transition ${m.is_active ? 'text-gray-400 hover:bg-gray-50 hover:text-gray-600' : 'text-teal-600 hover:bg-teal-50'}`}
                    title={m.is_active ? 'Pause' : 'Resume'}
                  >
                    {m.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
