import { ArrowLeft, ArrowRight, Mail } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import api, { extractApiErrorMessage } from '../lib/api'

export default function ClosedBetaSignup() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setErrorMessage(null)

    try {
      await api.post('/public/beta-signups', { email })
      setSubmitted(true)
    } catch (error: unknown) {
      setErrorMessage(extractApiErrorMessage(error, 'Unable to submit right now. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="panel w-full max-w-xl p-8 md:p-10">
        <Link to="/" className="btn-ghost -ml-2 mb-6 w-fit">
          <ArrowLeft className="h-4 w-4" />
          Back to landing page
        </Link>

        <div className="page-kicker">Closed beta</div>
        <h1 className="page-title mt-3">Request access</h1>
        <p className="page-subtitle mt-3">
          Enter your email and we will notify you when we open operating console access.
        </p>

        {submitted ? (
          <div className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
            You are on the list. We will reach out when your closed beta slot opens.
          </div>
        ) : (
          <form className="mt-8 space-y-4" onSubmit={onSubmit}>
            <label className="block">
              <span className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-slate-700">
                <Mail className="h-4 w-4" />
                Work email
              </span>
              <input
                className="input-field"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
                required
              />
            </label>

            {errorMessage && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {errorMessage}
              </div>
            )}

            <button className="btn-primary w-full" type="submit" disabled={loading}>
              {loading ? 'Submitting...' : 'Join closed beta'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
