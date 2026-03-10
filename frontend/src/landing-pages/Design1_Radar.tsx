/**
 * Design 1: "Radar" — Dark, data-dense, terminal-inspired
 *
 * Personality: Technical, powerful, for engineers and PMs who love dashboards
 * Colors: Near-black backgrounds, electric green/cyan accents, monospace touches
 * Layout: Asymmetric grid, live-data feel, subtle grid background
 */

import { Activity, Bell, Eye, GitCompare, Radio, Shield, Zap } from 'lucide-react'

const features = [
  { icon: Eye, label: 'Deep Monitoring', desc: 'Track pricing pages, changelogs, job boards, and homepages across your competitive landscape.' },
  { icon: GitCompare, label: 'Smart Diffing', desc: 'Noise-filtered text diffs cut through timestamps, session tokens, and cache busters to surface real changes.' },
  { icon: Zap, label: 'AI Classification', desc: 'Claude analyzes every change — is it a pricing shift, feature launch, or just a typo fix?' },
  { icon: Bell, label: 'Instant Alerts', desc: 'Slack and email notifications with severity levels. Digest mode for high-volume monitors.' },
  { icon: Shield, label: 'Suppression Engine', desc: 'Same-summary dedup, severity escalation, and oscillation detection eliminate alert fatigue.' },
  { icon: Activity, label: 'Full Pipeline Visibility', desc: 'Every scrape, diff, and classification is logged. Drill into any change in the historical timeline.' },
]

export default function RadarLanding() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100 overflow-hidden">
      {/* Background grid */}
      <div className="fixed inset-0 opacity-[0.03]" style={{
        backgroundImage: `linear-gradient(rgba(0,255,170,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,170,0.3) 1px, transparent 1px)`,
        backgroundSize: '60px 60px',
      }} />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-5 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <Radio className="w-5 h-5 text-emerald-400" />
          <span className="font-mono text-sm font-bold tracking-wider text-emerald-400">SHADOW</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#features" className="text-sm text-gray-500 hover:text-gray-300 transition">Features</a>
          <a href="#pipeline" className="text-sm text-gray-500 hover:text-gray-300 transition">Pipeline</a>
          <button className="text-sm font-mono px-4 py-2 border border-emerald-500/30 text-emerald-400 rounded hover:bg-emerald-500/10 transition">
            Sign In
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-7xl mx-auto px-8 pt-24 pb-32">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/20 bg-emerald-500/5 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono text-emerald-400">MONITORING ACTIVE</span>
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold leading-[1.1] tracking-tight">
            Know what your competitors change
            <span className="text-emerald-400"> before they announce it</span>
          </h1>

          <p className="mt-6 text-lg text-gray-400 max-w-xl leading-relaxed">
            Continuous monitoring, intelligent diffing, and AI-powered classification.
            Shadow watches competitor websites and tells you what matters.
          </p>

          <div className="mt-10 flex items-center gap-4">
            <button className="px-6 py-3 bg-emerald-500 text-black font-semibold rounded-lg hover:bg-emerald-400 transition shadow-lg shadow-emerald-500/20">
              Start Monitoring
            </button>
            <button className="px-6 py-3 text-gray-400 hover:text-white transition font-mono text-sm">
              View Demo →
            </button>
          </div>
        </div>

        {/* Terminal preview */}
        <div className="mt-16 rounded-xl border border-gray-800 bg-[#0d0d15] overflow-hidden shadow-2xl">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
            <span className="ml-4 text-xs font-mono text-gray-600">shadow — alert feed</span>
          </div>
          <div className="p-6 font-mono text-sm space-y-3">
            <div className="flex gap-3">
              <span className="text-gray-600">14:32:07</span>
              <span className="text-red-400 font-bold">CRITICAL</span>
              <span className="text-gray-300">Acme Corp pricing page — <span className="text-yellow-300">Enterprise tier increased $299 → $399/mo</span></span>
            </div>
            <div className="flex gap-3">
              <span className="text-gray-600">14:28:15</span>
              <span className="text-orange-400 font-bold">HIGH</span>
              <span className="text-gray-300">Rival.io changelog — <span className="text-yellow-300">New API v3 with GraphQL support launched</span></span>
            </div>
            <div className="flex gap-3">
              <span className="text-gray-600">14:15:42</span>
              <span className="text-yellow-400 font-bold">MEDIUM</span>
              <span className="text-gray-300">Competitor X jobs page — <span className="text-yellow-300">12 new ML engineer positions posted</span></span>
            </div>
            <div className="flex gap-3">
              <span className="text-gray-600">14:02:18</span>
              <span className="text-emerald-500">filtered</span>
              <span className="text-gray-500">Beta Inc homepage — noise only (copyright year, build hashes)</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-8 py-24">
        <h2 className="text-sm font-mono text-emerald-400 mb-4 tracking-wider">CAPABILITIES</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.label} className="p-6 rounded-xl border border-gray-800 bg-gray-900/30 hover:border-emerald-500/30 transition group">
              <f.icon className="w-5 h-5 text-emerald-400 mb-4 group-hover:scale-110 transition" />
              <h3 className="font-semibold text-white mb-2">{f.label}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pipeline visualization */}
      <section id="pipeline" className="relative z-10 max-w-7xl mx-auto px-8 py-24">
        <h2 className="text-sm font-mono text-emerald-400 mb-4 tracking-wider">HOW IT WORKS</h2>
        <div className="flex flex-col md:flex-row items-start gap-4">
          {['Scrape', 'Extract', 'Diff', 'Filter Noise', 'Classify (AI)', 'Alert'].map((step, i) => (
            <div key={step} className="flex items-center gap-4 flex-1">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-mono text-sm font-bold">
                  {i + 1}
                </div>
                <span className="mt-2 text-xs font-mono text-gray-400 text-center">{step}</span>
              </div>
              {i < 5 && <div className="hidden md:block w-full h-px bg-gradient-to-r from-emerald-500/30 to-transparent" />}
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-gray-800 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-8 flex items-center justify-between">
          <span className="text-xs font-mono text-gray-600">SHADOW v0.1.0</span>
          <span className="text-xs text-gray-600">Competitor Intelligence Monitor</span>
        </div>
      </footer>
    </div>
  )
}
