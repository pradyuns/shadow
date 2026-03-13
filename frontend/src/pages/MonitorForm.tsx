import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Globe, Save, ShieldCheck } from 'lucide-react'
import api, { extractApiErrorMessage } from '../lib/api'
import type { PageType } from '../lib/types'

const PAGE_TYPES: { value: PageType; label: string; description: string }[] = [
  { value: 'pricing', label: 'Pricing', description: 'Packaging, plan changes, discounting' },
  { value: 'changelog', label: 'Changelog', description: 'Product announcements and releases' },
  { value: 'homepage', label: 'Homepage', description: 'Messaging, positioning, major launches' },
  { value: 'jobs', label: 'Jobs', description: 'Team growth, role focus, hiring patterns' },
  { value: 'blog', label: 'Blog', description: 'Thought leadership and campaign themes' },
  { value: 'docs', label: 'Docs', description: 'API or product documentation changes' },
  { value: 'other', label: 'Other', description: 'Any other public page worth tracking' },
]

const INTERVALS = [
  { value: 1, label: 'Hourly' },
  { value: 3, label: 'Every 3 hours' },
  { value: 6, label: 'Every 6 hours' },
  { value: 12, label: 'Twice a day' },
  { value: 24, label: 'Daily' },
]

export default function MonitorForm() {
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [competitorName, setCompetitorName] = useState('')
  const [url, setUrl] = useState('')
  const [pageType, setPageType] = useState<PageType>('homepage')
  const [interval, setInterval] = useState(6)
  const [cssSelector, setCssSelector] = useState('')
  const [renderJs, setRenderJs] = useState(false)
  const [useFirecrawl, setUseFirecrawl] = useState(false)
  const [initializing, setInitializing] = useState(Boolean(id))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) {
      setInitializing(false)
      return
    }

    api
      .get(`/monitors/${id}`)
      .then(({ data }) => {
        setName(data.name)
        setCompetitorName(data.competitor_name || '')
        setUrl(data.url)
        setPageType(data.page_type || 'homepage')
        setInterval(data.check_interval_hours)
        setCssSelector(data.css_selector || '')
        setRenderJs(data.render_js)
        setUseFirecrawl(data.use_firecrawl || false)
        setInitializing(false)
      })
      .catch(() => navigate('/monitors'))
  }, [id, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const payload = {
      name,
      competitor_name: competitorName || null,
      url,
      page_type: pageType,
      check_interval_hours: interval,
      css_selector: cssSelector || null,
      render_js: renderJs,
      use_firecrawl: useFirecrawl,
    }

    try {
      if (isEdit) {
        await api.patch(`/monitors/${id}`, payload)
        navigate(`/monitors/${id}`)
      } else {
        const { data } = await api.post('/monitors', payload)
        navigate(`/monitors/${data.id}`)
      }
    } catch (error: unknown) {
      setError(extractApiErrorMessage(error, 'Failed to save monitor'))
    } finally {
      setLoading(false)
    }
  }

  if (initializing) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  const activePageType = PAGE_TYPES.find((page) => page.value === pageType)
  const activeInterval = INTERVALS.find((option) => option.value === interval)

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4">
        <Link to={id ? `/monitors/${id}` : '/monitors'} className="btn-ghost w-fit">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>

        <div className="max-w-3xl">
          <p className="page-kicker">{isEdit ? 'Edit Monitor' : 'New Monitor'}</p>
          <h2 className="mt-3 page-title">
            {isEdit ? 'Update capture settings' : 'Create a monitor'}
          </h2>
          <p className="mt-3 page-subtitle">
            Keep the setup focused: what page to track, how often to check it, and whether capture needs a scoped selector or JavaScript rendering.
          </p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <form onSubmit={handleSubmit} className="panel p-8">
          {error && (
            <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          <div className="space-y-8">
            <section>
              <div className="mb-5">
                <div className="text-base font-semibold text-slate-950">Monitor details</div>
                <div className="mt-1 text-sm text-slate-600">
                  Give the source a clear internal name so review is fast later.
                </div>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Monitor name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input-field"
                    placeholder="Stripe pricing page"
                    required
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">
                    Competitor name
                  </label>
                  <input
                    type="text"
                    value={competitorName}
                    onChange={(e) => setCompetitorName(e.target.value)}
                    className="input-field"
                    placeholder="Stripe"
                  />
                </div>
              </div>

              <div className="mt-5">
                <label className="mb-2 block text-sm font-medium text-slate-700">URL</label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="input-field"
                  placeholder="https://stripe.com/pricing"
                  required
                />
              </div>
            </section>

            <section>
              <div className="mb-5">
                <div className="text-base font-semibold text-slate-950">Page context</div>
                <div className="mt-1 text-sm text-slate-600">
                  Pick the best-fit page type so future review feels more organized.
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {PAGE_TYPES.map((page) => (
                  <button
                    key={page.value}
                    type="button"
                    onClick={() => setPageType(page.value)}
                    className={`rounded-2xl border px-4 py-4 text-left ${
                      pageType === page.value
                        ? 'border-blue-500 bg-blue-50 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="text-sm font-semibold text-slate-950">{page.label}</div>
                    <div className="mt-2 text-xs leading-5 text-slate-600">{page.description}</div>
                  </button>
                ))}
              </div>
            </section>

            <section>
              <div className="mb-5">
                <div className="text-base font-semibold text-slate-950">Capture settings</div>
                <div className="mt-1 text-sm text-slate-600">
                  Control cadence, scope, and fallback scraping behavior.
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Check interval</label>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                  {INTERVALS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setInterval(option.value)}
                      className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${
                        interval === option.value
                          ? 'border-slate-950 bg-slate-950 text-white'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5">
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  CSS selector
                </label>
                <input
                  type="text"
                  value={cssSelector}
                  onChange={(e) => setCssSelector(e.target.value)}
                  className="input-field"
                  placeholder="#pricing-table, .plan-card"
                />
                <p className="helper-text mt-2">
                  Use this only if the full page contains too much unrelated content or frequent layout churn.
                </p>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setRenderJs(!renderJs)}
                  className={`rounded-2xl border p-4 text-left ${
                    renderJs
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-950">JavaScript rendering</div>
                      <div className="mt-2 text-xs leading-5 text-slate-600">
                        Use when the page is an SPA or loads important content after the initial HTML response.
                      </div>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        renderJs ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {renderJs ? 'Enabled' : 'Off'}
                    </span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setUseFirecrawl(!useFirecrawl)}
                  className={`rounded-2xl border p-4 text-left ${
                    useFirecrawl
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-950">Firecrawl fallback</div>
                      <div className="mt-2 text-xs leading-5 text-slate-600">
                        Prefer this for bot-protected sites or pages that fail consistently with the default scraper.
                      </div>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        useFirecrawl ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {useFirecrawl ? 'Enabled' : 'Off'}
                    </span>
                  </div>
                </button>
              </div>
            </section>
          </div>

          <div className="mt-8 flex flex-col gap-3 border-t border-slate-200 pt-6 sm:flex-row sm:justify-end">
            <Link to={id ? `/monitors/${id}` : '/monitors'} className="btn-secondary">
              Cancel
            </Link>
            <button type="submit" disabled={loading} className="btn-primary">
              <Save className="h-4 w-4" />
              {loading ? 'Saving...' : isEdit ? 'Save changes' : 'Create monitor'}
            </button>
          </div>
        </form>

        <div className="space-y-6">
          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <Globe className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Configuration summary</div>
                <div className="text-sm text-slate-600">
                  Live preview of the monitor setup you are about to save.
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Page type</div>
                <div className="mt-2 text-sm font-semibold text-slate-950">{activePageType?.label}</div>
                <div className="mt-1 text-sm text-slate-600">{activePageType?.description}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Cadence</div>
                <div className="mt-2 text-sm font-semibold text-slate-950">{activeInterval?.label}</div>
                <div className="mt-1 text-sm text-slate-600">
                  {renderJs ? 'JavaScript rendering on' : 'Standard HTML capture'}
                  {useFirecrawl ? ' with Firecrawl fallback' : ''}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Scope</div>
                <div className="mt-2 text-sm font-semibold text-slate-950">
                  {cssSelector || 'Full page'}
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  {cssSelector
                    ? 'Changes will focus on the selected content block.'
                    : 'Changes will be computed across the page content.'}
                </div>
              </div>
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">What makes this feel better</div>
                <div className="text-sm text-slate-600">
                  Cleaner defaults and fewer ambiguous choices.
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              {[
                'Competitor name is captured explicitly, which makes the monitor list easier to scan.',
                'Page type and cadence are surfaced as clear decision blocks rather than tiny controls.',
                'Capture options read like operational settings instead of experimental toggles.',
              ].map((item) => (
                <div key={item} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                  <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
