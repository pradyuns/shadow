import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, Bell, CheckCircle2, Radar, ShieldCheck, XCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { extractApiErrorMessage } from '../lib/api'

const highlights = [
  'Alerts ranked by business impact — not raw page changes.',
  'Full history of every change attached to each monitored page.',
  'Automated tracking across pricing, features, and positioning.',
]

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const verified = searchParams.get('verified') === 'true'
  const verifyError = searchParams.get('verify_error')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (error: unknown) {
      setError(extractApiErrorMessage(error, 'Invalid credentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-4 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:px-8">
        <section className="hidden lg:block">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700">
              <ShieldCheck className="h-4 w-4" />
              Competitive monitoring workspace
            </div>

            <h1 className="mt-8 text-5xl font-semibold leading-[1.08] text-slate-950">
              Your competitors changed something last night.
            </h1>

            <p className="mt-6 text-lg leading-8 text-slate-600">
              Shadow monitors competitor pages around the clock, detects meaningful changes, and
              alerts your team before the market notices.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Radar className="h-4 w-4 text-blue-600" />
                  Change detection
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Pages are captured and compared automatically on your schedule. Every change is logged.
                </p>
              </div>
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Bell className="h-4 w-4 text-amber-600" />
                  Alert triage
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Severity-ranked alerts so your team focuses on what matters, not noise.
                </p>
              </div>
            </div>

            <div className="panel mt-8 p-6">
              <div className="text-sm font-semibold text-slate-950">Why teams use Shadow</div>
              <div className="mt-4 space-y-3">
                {highlights.map((item) => (
                  <div key={item} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                    <div className="mt-2 h-2 w-2 rounded-full bg-blue-600" />
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
              <img src="/shadow-logo.png" alt="Shadow" className="h-10 w-10 rounded-xl object-cover" />
              <div>
                <div className="text-lg font-semibold text-slate-950">Shadow</div>
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
                  Competitor Intelligence
                </div>
              </div>
            </Link>
          </div>

          <div className="panel p-8">
            <div>
              <p className="page-kicker">Sign In</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950">Welcome back</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Sign in to review active monitors, recent changes, and unresolved alerts.
              </p>
            </div>

            {verified && (
              <div className="mt-6 flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Email verified. You can now sign in with full access.
              </div>
            )}

            {verifyError && (
              <div className="mt-6 flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <XCircle className="h-4 w-4 shrink-0" />
                {verifyError === 'invalid'
                  ? 'Verification link is invalid or expired. Sign in and resend.'
                  : 'Account not found. The link may have expired.'}
              </div>
            )}

            {error && (
              <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
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
                  placeholder="Enter your password"
                  required
                />
              </div>

              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Signing in...' : 'Sign in'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-sm text-slate-600">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-semibold text-blue-700 hover:text-blue-800">
              Create one
            </Link>
          </p>
        </section>
      </div>
    </div>
  )
}
