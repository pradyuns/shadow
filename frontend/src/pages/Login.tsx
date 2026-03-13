import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, Bell, CheckCircle2, GitCompare, Globe, ShieldCheck, XCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { extractApiErrorMessage } from '../lib/api'

const highlights = [
  'Review alerts by severity instead of reading raw page diffs.',
  'Keep snapshot history attached to every monitored URL.',
  'Show a recruiter a product flow that looks deliberate and inspectable.',
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
              Sign in to a product flow that reads like an operations tool.
            </h1>

            <p className="mt-6 text-lg leading-8 text-slate-600">
              Review monitors, snapshots, diffs, and alerts from a cleaner interface that feels closer to
              production software than a generated mockup.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <GitCompare className="h-4 w-4 text-blue-600" />
                  Diff review
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Snapshots and change history stay inspectable directly from the monitor detail page.
                </p>
              </div>
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Bell className="h-4 w-4 text-amber-600" />
                  Alert triage
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Acknowledge high-signal alerts without leaving the dashboard workflow.
                </p>
              </div>
            </div>

            <div className="panel mt-8 p-6">
              <div className="text-sm font-semibold text-slate-950">What changes in this pass</div>
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
              <p className="page-kicker">Sign In</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950">Welcome back</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Use your account to review active monitors, recent diffs, and unresolved alerts.
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
