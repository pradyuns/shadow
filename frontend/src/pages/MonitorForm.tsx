import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../lib/api'
import type { PageType } from '../lib/types'
import { ArrowLeft, Globe, Save } from 'lucide-react'

const PAGE_TYPES: { value: PageType; label: string }[] = [
  { value: 'pricing', label: 'Pricing' },
  { value: 'changelog', label: 'Changelog' },
  { value: 'homepage', label: 'Homepage' },
  { value: 'jobs', label: 'Jobs' },
  { value: 'blog', label: 'Blog' },
  { value: 'docs', label: 'Docs' },
  { value: 'other', label: 'Other' },
]

const INTERVALS = [
  { value: 1, label: 'Every hour' },
  { value: 3, label: 'Every 3 hours' },
  { value: 6, label: 'Every 6 hours' },
  { value: 12, label: 'Every 12 hours' },
  { value: 24, label: 'Every 24 hours' },
]

export default function MonitorForm() {
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [pageType, setPageType] = useState<PageType>('homepage')
  const [interval, setInterval] = useState(6)
  const [cssSelector, setCssSelector] = useState('')
  const [renderJs, setRenderJs] = useState(false)
  const [useFirecrawl, setUseFirecrawl] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (id) {
      api.get(`/monitors/${id}`).then(({ data }) => {
        setName(data.name)
        setUrl(data.url)
        setPageType(data.page_type || 'homepage')
        setInterval(data.check_interval_hours)
        setCssSelector(data.css_selector || '')
        setRenderJs(data.render_js)
        setUseFirecrawl(data.use_firecrawl || false)
      }).catch(() => navigate('/monitors'))
    }
  }, [id, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const payload = {
      name,
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
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to save monitor')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 transition mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      <div className="bg-white rounded-2xl border border-gray-100 p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
            <Globe className="w-5 h-5 text-teal-700" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">
              {isEdit ? 'Edit Monitor' : 'New Monitor'}
            </h1>
            <p className="text-xs text-gray-400">
              {isEdit ? 'Update monitoring configuration' : 'Track a competitor page'}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 text-rose-700 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-[#FAFAF8] text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
              placeholder="Stripe Pricing Page"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">URL</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-[#FAFAF8] text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
              placeholder="https://stripe.com/pricing"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Page Type</label>
            <div className="grid grid-cols-4 gap-2">
              {PAGE_TYPES.map((pt) => (
                <button
                  key={pt.value}
                  type="button"
                  onClick={() => setPageType(pt.value)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium transition border ${
                    pageType === pt.value
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {pt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Check Interval</label>
            <div className="grid grid-cols-5 gap-2">
              {INTERVALS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setInterval(opt.value)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium transition border ${
                    interval === opt.value
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              CSS Selector <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={cssSelector}
              onChange={(e) => setCssSelector(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-[#FAFAF8] text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition font-mono"
              placeholder="#pricing-table, .plan-card"
            />
            <p className="text-xs text-gray-400 mt-1.5">
              Focus on specific page elements. Leave blank to monitor the full page.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 rounded-xl bg-[#FAFAF8] border border-gray-100">
              <div>
                <div className="text-sm font-medium text-gray-900">JavaScript Rendering</div>
                <div className="text-xs text-gray-400 mt-0.5">
                  Enable for SPAs and dynamically loaded content
                </div>
              </div>
              <button
                type="button"
                onClick={() => setRenderJs(!renderJs)}
                className={`relative w-11 h-6 rounded-full transition ${renderJs ? 'bg-teal-500' : 'bg-gray-200'}`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${renderJs ? 'translate-x-5.5' : 'translate-x-0.5'}`} />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 rounded-xl bg-[#FAFAF8] border border-gray-100">
              <div>
                <div className="text-sm font-medium text-gray-900">Use Firecrawl</div>
                <div className="text-xs text-gray-400 mt-0.5">
                  Always use Firecrawl for bot-protected sites (e.g., Walmart, Amazon)
                </div>
              </div>
              <button
                type="button"
                onClick={() => setUseFirecrawl(!useFirecrawl)}
                className={`relative w-11 h-6 rounded-full transition ${useFirecrawl ? 'bg-teal-500' : 'bg-gray-200'}`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${useFirecrawl ? 'translate-x-5.5' : 'translate-x-0.5'}`} />
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-gray-900 text-white rounded-full text-sm font-semibold hover:bg-gray-800 transition disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {loading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Monitor'}
          </button>
        </form>
      </div>
    </div>
  )
}
