/**
 * Design 2: "Prism" — Clean, SaaS-polished, gradient-forward
 *
 * Personality: Premium B2B SaaS, trustworthy, conversion-optimized
 * Colors: White backgrounds, indigo-to-violet gradients, soft shadows
 * Layout: Centered, breathing whitespace, clear visual hierarchy
 */

import { ArrowRight, BarChart3, Bell, Eye, GitCompare, Search, Shield } from 'lucide-react'

const features = [
  { icon: Search, title: 'Monitor Any Page', desc: 'Pricing, changelogs, job boards, homepages — track the pages that matter to your strategy.' },
  { icon: GitCompare, title: 'Intelligent Diffs', desc: 'Automated noise filtering strips timestamps and tokens. Only meaningful changes surface.' },
  { icon: BarChart3, title: 'AI-Powered Analysis', desc: 'Every change is classified by severity and category so you can prioritize what to act on.' },
  { icon: Bell, title: 'Smart Notifications', desc: 'Severity-based routing, digest mode, and oscillation detection prevent alert fatigue.' },
]

const steps = [
  { num: '01', title: 'Add competitors', desc: 'Paste URLs for pricing pages, changelogs, job boards, or any page you want to track.' },
  { num: '02', title: 'We watch continuously', desc: 'Every 6 hours (or your custom interval), we scrape, extract text, and compare against the last snapshot.' },
  { num: '03', title: 'AI classifies changes', desc: 'Noise is filtered out. Real changes are analyzed by Claude to determine significance and category.' },
  { num: '04', title: 'You get alerted', desc: 'Critical pricing changes hit Slack instantly. Minor updates go in your daily digest.' },
]

export default function PrismLanding() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Eye className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-lg">Shadow</span>
        </div>
        <div className="flex items-center gap-8">
          <a href="#features" className="text-sm text-gray-500 hover:text-gray-900 transition">Features</a>
          <a href="#how" className="text-sm text-gray-500 hover:text-gray-900 transition">How it Works</a>
          <button className="text-sm px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-full hover:shadow-lg hover:shadow-indigo-500/25 transition font-medium">
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-8 pt-28 pb-20 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-50 rounded-full mb-8">
          <span className="text-xs font-medium text-indigo-600">Now with AI-powered classification</span>
          <ArrowRight className="w-3 h-3 text-indigo-600" />
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold leading-[1.1] tracking-tight max-w-3xl mx-auto">
          Competitor intelligence on{' '}
          <span className="bg-gradient-to-r from-indigo-500 to-violet-600 bg-clip-text text-transparent">
            autopilot
          </span>
        </h1>

        <p className="mt-6 text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
          Shadow monitors competitor websites, detects meaningful changes, and delivers
          classified alerts — so you never miss a pricing shift or feature launch.
        </p>

        <div className="mt-10 flex items-center justify-center gap-4">
          <button className="px-8 py-3.5 bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-full font-semibold hover:shadow-xl hover:shadow-indigo-500/25 transition text-sm">
            Start Free Trial
          </button>
          <button className="px-8 py-3.5 border border-gray-200 rounded-full text-gray-600 hover:border-gray-300 transition text-sm font-medium">
            Watch Demo
          </button>
        </div>

        {/* Preview card */}
        <div className="mt-20 max-w-4xl mx-auto rounded-2xl border border-gray-100 shadow-xl shadow-gray-200/50 overflow-hidden bg-white">
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-100 flex items-center gap-3">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-gray-200" />
              <div className="w-3 h-3 rounded-full bg-gray-200" />
              <div className="w-3 h-3 rounded-full bg-gray-200" />
            </div>
            <div className="flex-1 mx-12">
              <div className="h-6 bg-gray-100 rounded-md max-w-md mx-auto" />
            </div>
          </div>
          <div className="p-8 space-y-4">
            {/* Alert rows */}
            {[
              { severity: 'CRITICAL', color: 'bg-red-50 text-red-700 border-red-100', dot: 'bg-red-500', competitor: 'Stripe', change: 'Pricing tier restructured — new usage-based model', time: '2 min ago' },
              { severity: 'HIGH', color: 'bg-orange-50 text-orange-700 border-orange-100', dot: 'bg-orange-500', competitor: 'Vercel', change: 'New Enterprise plan with SSO and audit logs', time: '1 hour ago' },
              { severity: 'MEDIUM', color: 'bg-yellow-50 text-yellow-700 border-yellow-100', dot: 'bg-yellow-500', competitor: 'Supabase', change: '8 new engineering positions posted in ML team', time: '3 hours ago' },
            ].map((alert, i) => (
              <div key={i} className="flex items-center gap-4 p-4 rounded-xl border border-gray-100 hover:border-indigo-100 hover:bg-indigo-50/30 transition">
                <span className={`w-2 h-2 rounded-full ${alert.dot}`} />
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${alert.color}`}>{alert.severity}</span>
                <span className="font-medium text-sm text-gray-900">{alert.competitor}</span>
                <span className="text-sm text-gray-500 flex-1">{alert.change}</span>
                <span className="text-xs text-gray-400">{alert.time}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-8 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold">Everything you need to stay ahead</h2>
          <p className="mt-3 text-gray-500 max-w-lg mx-auto">
            From scraping to classification to alerting — a complete competitive intelligence pipeline.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {features.map((f) => (
            <div key={f.title} className="flex gap-5 p-6 rounded-2xl hover:bg-gray-50 transition">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-50 to-violet-50 flex items-center justify-center shrink-0">
                <f.icon className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="bg-gray-50 py-24">
        <div className="max-w-6xl mx-auto px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold">How Shadow works</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((s) => (
              <div key={s.num} className="relative">
                <span className="text-5xl font-bold text-indigo-100">{s.num}</span>
                <h3 className="font-semibold mt-2 mb-2">{s.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-8 py-24 text-center">
        <div className="max-w-2xl mx-auto p-12 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
          <h2 className="text-3xl font-bold mb-4">Never miss a competitive move</h2>
          <p className="text-indigo-100 mb-8">Start monitoring your competitors in minutes. No credit card required.</p>
          <button className="px-8 py-3.5 bg-white text-indigo-600 rounded-full font-semibold hover:shadow-lg transition">
            Start Free Trial
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8">
        <div className="max-w-6xl mx-auto px-8 flex items-center justify-between text-sm text-gray-400">
          <span>Shadow — Competitor Intelligence Monitor</span>
          <span>v0.1.0</span>
        </div>
      </footer>
    </div>
  )
}
