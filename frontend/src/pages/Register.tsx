import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Radar, ShieldCheck, Workflow } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { extractApiErrorMessage } from '../lib/api'

const setupNotes = [
  'Set up a monitor in under two minutes — just a URL and a schedule.',
  'Track competitor pricing, features, and positioning in one place.',
  'Severity-ranked alerts so your team acts on signal, not noise.',
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

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

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
              Get started in minutes
            </div>

            <h1 className="mt-8 text-5xl font-semibold leading-[1.08] text-slate-950">
              Stop finding out about competitor changes from your customers.
            </h1>

            <p className="mt-6 text-lg leading-8 text-slate-600">
              Shadow watches competitor pages continuously, catches what changed, and delivers
              clear alerts ranked by business impact.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Radar className="h-4 w-4 text-blue-600" />
                  Monitor setup
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Configure URLs, check frequency, and capture mode in a single form.
                </p>
              </div>
              <div className="metric-card">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Workflow className="h-4 w-4 text-emerald-600" />
                  Automated pipeline
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  Capture, compare, analyze, and alert — fully automated from monitor to inbox.
                </p>
              </div>
            </div>

            <div className="panel mt-8 p-6">
              <div className="text-sm font-semibold text-slate-950">How it works</div>
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
              <p className="page-kicker">Create Account</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950">Set up your workspace</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Create your account and start monitoring competitors in minutes.
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
