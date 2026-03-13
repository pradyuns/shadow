import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Globe, Radar, ShieldCheck, Workflow } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { extractApiErrorMessage } from '../lib/api'

const setupNotes = [
  'Create a monitor in a few fields instead of a dense wizard.',
  'Keep competitor pages, diffs, and alerts in one review path.',
  'Show a recruiting panel a product that looks organized and trustworthy.',
]

export default function Register() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await register(email, password, fullName)
      navigate('/dashboard')
    } catch (error: unknown) {
      setError(extractApiErrorMessage(error, 'Registration failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-4 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:px-8">
        <section className="hidden lg:block">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">
              <ShieldCheck className="h-4 w-4" />
              Clean onboarding flow
            </div>

            <h1 className="mt-8 text-5xl font-semibold leading-[1.08] text-slate-950">
              Create an account and start demoing a more credible product experience.
            </h1>

            <p className="mt-6 text-lg leading-8 text-slate-600">
              This version emphasizes clearer hierarchy, calmer visuals, and working monitor and alert flows
              that are easier to explain in interviews and recruiter reviews.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Radar className="h-4 w-4 text-blue-600" />
                  Monitor setup
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Configure URLs, cadence, capture mode, and scoped selectors without leaving the form.
                </p>
              </div>
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Workflow className="h-4 w-4 text-emerald-600" />
                  Review flow
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Move from monitor creation to diffs and alerts through a tighter, more standard layout.
                </p>
              </div>
            </div>

            <div className="panel mt-8 p-6">
              <div className="text-sm font-semibold text-slate-950">Recruiter-friendly improvements</div>
              <div className="mt-4 space-y-3">
                {setupNotes.map((item) => (
                  <div key={item} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                    <div className="mt-2 h-2 w-2 rounded-full bg-emerald-600" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-md">
          <div className="mb-6">
            <Link to="/" className="inline-flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
                <Globe className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-950">Shadow</div>
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
                  Monitoring Ops
                </div>
              </div>
            </Link>
          </div>

          <div className="panel p-8">
            <div>
              <p className="page-kicker">Create Account</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950">Set up your workspace</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Create a user, open the dashboard, and review the end-to-end monitoring flow.
              </p>
            </div>

            {error && (
              <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Full name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-field"
                  placeholder="Jane Smith"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field"
                  placeholder="you@company.com"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  placeholder="Minimum 8 characters"
                  minLength={8}
                  required
                />
              </div>

              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Creating account...' : 'Create account'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-blue-700 hover:text-blue-800">
              Sign in
            </Link>
          </p>
        </section>
      </div>
    </div>
  )
}
