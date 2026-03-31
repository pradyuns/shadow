import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Clock3, ExternalLink, Pause, Play, Plus, Radar, Search } from 'lucide-react'
import api from '../lib/api'
import type { Monitor } from '../lib/types'
import { extractItems, timeAgo } from '../lib/utils'

export default function Monitors() {
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    api
      .get('/monitors')
      .then(({ data }) => {
        setMonitors(extractItems<Monitor>(data))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const toggleActive = async (id: string, currentState: boolean) => {
    try {
      await api.patch(`/monitors/${id}`, { is_active: !currentState })
      setMonitors((previous) =>
        previous.map((monitor) =>
          monitor.id === id ? { ...monitor, is_active: !currentState } : monitor,
        ),
      )
    } catch {
      // Intentionally silent until a dedicated toast system is added.
    }
  }

  const filtered = monitors.filter((monitor) => {
    const query = search.trim().toLowerCase()
    if (!query) return true

    return (
      monitor.name.toLowerCase().includes(query) ||
      monitor.url.toLowerCase().includes(query) ||
      (monitor.competitor_name || '').toLowerCase().includes(query)
    )
  })

  const activeCount = monitors.filter((monitor) => monitor.is_active).length
  const pausedCount = monitors.filter((monitor) => !monitor.is_active).length
  const issueCount = monitors.filter((monitor) => monitor.consecutive_failures > 0).length

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
          <p className="page-kicker">Monitors</p>
          <h2 className="mt-3 page-title">Source coverage</h2>
          <p className="mt-3 page-subtitle">
            Manage the URLs you track, confirm capture cadence, and jump directly into snapshot and alert review.
          </p>
        </div>

        <Link to="/monitors/new" className="btn-primary">
          <Plus className="h-4 w-4" />
          Add monitor
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Total monitors</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{monitors.length}</div>
          <div className="mt-2 text-sm text-slate-600">{activeCount} active</div>
        </div>
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Paused monitors</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{pausedCount}</div>
          <div className="mt-2 text-sm text-slate-600">Ready to be resumed when needed</div>
        </div>
        <div className="metric-card">
          <div className="text-sm font-medium text-slate-500">Need attention</div>
          <div className="mt-3 text-4xl font-semibold text-slate-950">{issueCount}</div>
          <div className="mt-2 text-sm text-slate-600">Monitors with scrape failures recorded</div>
        </div>
      </div>

      <div className="panel p-5">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by monitor name, URL, or competitor"
            className="input-field pl-11"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="panel px-6 py-14 text-center">
          <Radar className="mx-auto h-10 w-10 text-slate-300" />
          <div className="mt-4 text-lg font-semibold text-slate-950">No monitors found</div>
          <div className="mt-2 text-sm text-slate-600">
            Try adjusting the search or create a new monitor to expand coverage.
          </div>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="hidden grid-cols-[2.2fr_0.85fr_0.9fr_0.9fr_0.85fr] gap-4 border-b border-slate-200 px-6 py-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 lg:grid">
            <div>Monitor</div>
            <div>Type</div>
            <div>Cadence</div>
            <div>Last check</div>
            <div className="text-right">Actions</div>
          </div>

          <div className="divide-y divide-slate-200">
            {filtered.map((monitor) => (
              <div
                key={monitor.id}
                className="grid gap-4 px-6 py-5 lg:grid-cols-[2.2fr_0.85fr_0.9fr_0.9fr_0.85fr] lg:items-center"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/monitors/${monitor.id}`}
                      className="truncate text-sm font-semibold text-slate-950 hover:text-blue-700"
                    >
                      {monitor.name}
                    </Link>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                        monitor.is_active
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {monitor.is_active ? 'Active' : 'Paused'}
                    </span>
                    {monitor.consecutive_failures > 0 && (
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-[11px] font-semibold text-rose-700">
                        Needs review
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-600">
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
                </div>

                <div className="text-sm text-slate-600">
                  <div className="font-medium text-slate-950">{monitor.page_type}</div>
                  <div className="mt-1">{monitor.render_js ? 'JS rendering enabled' : 'Standard capture'}</div>
                </div>

                <div className="text-sm text-slate-600">
                  <div className="font-medium text-slate-950">Every {monitor.check_interval_hours}h</div>
                  <div className="mt-1">{monitor.use_firecrawl ? 'Firecrawl enabled' : 'Default scraper'}</div>
                </div>

                <div className="text-sm text-slate-600">
                  <div className="inline-flex items-center gap-1 font-medium text-slate-950">
                    <Clock3 className="h-3.5 w-3.5" />
                    {timeAgo(monitor.last_checked_at)}
                  </div>
                  <div className="mt-1">
                    {monitor.last_change_at ? `Changed ${timeAgo(monitor.last_change_at)}` : 'No recent changes'}
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-end gap-2">
                  <Link to={`/monitors/${monitor.id}`} className="btn-secondary">
                    View
                  </Link>
                  <button
                    type="button"
                    onClick={() => toggleActive(monitor.id, monitor.is_active)}
                    className="btn-ghost border border-slate-200"
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
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
