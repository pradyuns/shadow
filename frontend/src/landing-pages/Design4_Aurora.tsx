import { ArrowRight, Bell, CheckCircle2, Clock3, GitCompare, Globe, Radar, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

const trustNotes = [
  'Snapshot history stays attached to every monitor.',
  'Alerts are severity-ranked before they reach the team.',
  'Slack and email delivery can be configured per channel.',
]

const workflowSteps = [
  {
    title: 'Configure the sources that matter',
    copy: 'Add a competitor URL, set the page type, and choose a review cadence that matches your market.',
  },
  {
    title: 'Capture and compare snapshots',
    copy: 'Shadow collects page content, stores a historical record, and computes diffs you can inspect later.',
  },
  {
    title: 'Review only meaningful changes',
    copy: 'Alerts are routed by severity so teams can triage urgent changes without losing the audit trail.',
  },
]

export default function AuroraLanding() {
  return (
    <div className="min-h-screen">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
            <Globe className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <div className="text-lg font-semibold text-slate-950">Shadow</div>
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
              Competitor Monitoring
            </div>
          </div>
        </div>

        <div className="hidden items-center gap-8 md:flex">
          <a href="#workflow" className="text-sm font-medium text-slate-600 hover:text-slate-950">
            Workflow
          </a>
          <a href="#trust" className="text-sm font-medium text-slate-600 hover:text-slate-950">
            Why it works
          </a>
          <Link to="/login" className="text-sm font-semibold text-slate-700 hover:text-slate-950">
            Sign in
          </Link>
          <Link to="/register" className="btn-primary">
            Create account
          </Link>
        </div>
      </nav>

      <section className="mx-auto max-w-7xl px-4 pb-20 pt-10 lg:px-8 lg:pt-16">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700">
              <ShieldCheck className="h-4 w-4" />
              Built for reviewable competitor monitoring
            </div>

            <h1 className="mt-8 max-w-3xl text-5xl font-semibold leading-[1.04] text-slate-950 sm:text-6xl">
              Track competitor page changes without the noisy, over-designed demo feel.
            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              Shadow gives teams a clean workflow for monitoring key pages, checking diffs, and
              routing alerts with enough context to trust the output.
            </p>

            <div className="mt-10 flex flex-col gap-3 sm:flex-row">
              <Link to="/register" className="btn-primary">
                Start monitoring
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/login" className="btn-secondary">
                Open dashboard
              </Link>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <div className="metric-card">
                <div className="text-sm font-medium text-slate-500">Coverage</div>
                <div className="mt-3 text-3xl font-semibold text-slate-950">24</div>
                <div className="mt-1 text-sm text-slate-600">Active monitors across pricing, hiring, and changelog pages</div>
              </div>
              <div className="metric-card">
                <div className="text-sm font-medium text-slate-500">Review queue</div>
                <div className="mt-3 text-3xl font-semibold text-slate-950">8</div>
                <div className="mt-1 text-sm text-slate-600">Open alerts with clear severity ranking and timestamps</div>
              </div>
              <div className="metric-card">
                <div className="text-sm font-medium text-slate-500">Change history</div>
                <div className="mt-3 text-3xl font-semibold text-slate-950">100%</div>
                <div className="mt-1 text-sm text-slate-600">Snapshots and diffs remain inspectable for every monitored page</div>
              </div>
            </div>
          </div>

          <div className="panel p-4 sm:p-6">
            <div className="rounded-[28px] border border-slate-200 bg-slate-50/80 p-4 sm:p-5">
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Monitoring workflow</div>
                  <div className="mt-1 text-sm text-slate-600">
                    A calmer product frame that reads like software, not a landing page generator.
                  </div>
                </div>
                <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  Operational
                </div>
              </div>

              <div className="mt-5 grid gap-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white">
                        <Radar className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-slate-950">Monitor configuration</div>
                        <div className="text-xs text-slate-500">Pricing pages, changelogs, docs, and hiring pages</div>
                      </div>
                    </div>
                    <div className="text-sm font-semibold text-slate-950">24 active</div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                      <GitCompare className="h-4 w-4 text-blue-600" />
                      Latest diff
                    </div>
                    <div className="mt-3 text-sm leading-6 text-slate-600">
                      Stripe pricing updated usage-based packaging and added a new annual billing note.
                    </div>
                    <div className="mt-4 flex items-center gap-3 text-xs text-slate-500">
                      <Clock3 className="h-3.5 w-3.5" />
                      5 minutes ago
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                      <Bell className="h-4 w-4 text-amber-600" />
                      Triage queue
                    </div>
                    <div className="mt-3 space-y-3 text-sm text-slate-600">
                      <div className="flex items-center justify-between">
                        <span>Critical alerts</span>
                        <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">2</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Awaiting acknowledgement</span>
                        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">8</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Delivery configured</span>
                        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">Slack + Email</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="text-sm font-semibold text-slate-950">Why recruiters can read this quickly</div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    {trustNotes.map((note) => (
                      <div key={note} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
                        <div className="flex items-start gap-2">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                          <span>{note}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="workflow" className="border-y border-slate-200/80 bg-white/80 py-20">
        <div className="mx-auto max-w-7xl px-4 lg:px-8">
          <div className="max-w-2xl">
            <p className="page-kicker">Workflow</p>
            <h2 className="mt-3 text-4xl font-semibold text-slate-950">
              The product flow is straightforward by design.
            </h2>
            <p className="mt-4 text-lg leading-8 text-slate-600">
              Configure sources, let the system capture changes, and review alerts with enough context
              to decide what matters.
            </p>
          </div>

          <div className="mt-12 grid gap-5 lg:grid-cols-3">
            {workflowSteps.map((step, index) => (
              <div key={step.title} className="panel p-6">
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-sm font-semibold text-white">
                  {index + 1}
                </div>
                <h3 className="mt-5 text-xl font-semibold text-slate-950">{step.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{step.copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="trust" className="mx-auto max-w-7xl px-4 py-20 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="page-kicker">Why it works</p>
            <h2 className="mt-3 text-4xl font-semibold text-slate-950">
              A product frame that feels closer to a real operating tool.
            </h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="panel-muted p-6">
              <div className="text-sm font-semibold text-slate-950">Structured pages</div>
              <p className="mt-2 text-sm leading-7 text-slate-600">
                Headers, summaries, and status blocks are organized like internal SaaS software rather than a design exercise.
              </p>
            </div>
            <div className="panel-muted p-6">
              <div className="text-sm font-semibold text-slate-950">Actionable alerts</div>
              <p className="mt-2 text-sm leading-7 text-slate-600">
                Severity, timestamps, and acknowledgement state stay visible so changes can be triaged quickly.
              </p>
            </div>
            <div className="panel-muted p-6">
              <div className="text-sm font-semibold text-slate-950">Audit-ready history</div>
              <p className="mt-2 text-sm leading-7 text-slate-600">
                Snapshots and diffs live with the monitor, which makes recruiter demos easier to explain and inspect.
              </p>
            </div>
            <div className="panel-muted p-6">
              <div className="text-sm font-semibold text-slate-950">Delivery controls</div>
              <p className="mt-2 text-sm leading-7 text-slate-600">
                Notification settings can be configured by channel with severity thresholds and optional digest delivery.
              </p>
            </div>
          </div>
        </div>

        <div className="panel mt-12 flex flex-col items-start justify-between gap-6 p-8 lg:flex-row lg:items-center">
          <div>
            <div className="text-2xl font-semibold text-slate-950">Ready to review the product in context?</div>
            <div className="mt-2 text-sm leading-7 text-slate-600">
              Open the app, create a monitor, and walk through the alert and snapshot flow directly.
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link to="/register" className="btn-primary">
              Create account
            </Link>
            <Link to="/login" className="btn-secondary">
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
