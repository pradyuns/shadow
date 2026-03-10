/**
 * Design 4: "Aurora" — Warm, approachable, rounded, modern
 *
 * Personality: Friendly but professional, for product and growth teams
 * Colors: Warm neutrals, soft teal/amber accents, cream backgrounds
 * Layout: Card-heavy, rounded corners everywhere, inviting feel
 */

import { ArrowRight, BarChart2, Bell, Eye, Filter, Globe, Layers, Sparkles } from 'lucide-react'

export default function AuroraLanding() {
  return (
    <div className="min-h-screen bg-[#FAFAF8]">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center">
            <Globe className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-semibold text-gray-900">Shadow</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#features" className="text-sm text-gray-400 hover:text-gray-700 transition">Features</a>
          <a href="#how" className="text-sm text-gray-400 hover:text-gray-700 transition">How it Works</a>
          <button className="text-sm px-5 py-2.5 bg-gray-900 text-white rounded-full hover:bg-gray-800 transition font-medium">
            Sign Up Free
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-8 pt-24 pb-16">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-teal-50 text-teal-700 rounded-full text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            Powered by AI classification
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold leading-[1.1] tracking-tight text-gray-900">
            Stay one step ahead of every competitor
          </h1>

          <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
            Shadow watches the web pages that matter — pricing, features, hiring, messaging —
            and tells you exactly what changed and why it matters.
          </p>

          <div className="mt-10 flex items-center justify-center gap-3">
            <button className="px-7 py-3.5 bg-gray-900 text-white rounded-full font-semibold hover:bg-gray-800 transition text-sm flex items-center gap-2">
              Start Monitoring
              <ArrowRight className="w-4 h-4" />
            </button>
            <button className="px-7 py-3.5 bg-white border border-gray-200 rounded-full text-gray-600 hover:border-gray-300 transition text-sm font-medium shadow-sm">
              See How It Works
            </button>
          </div>
        </div>

        {/* Dashboard preview */}
        <div className="mt-20 rounded-3xl bg-white border border-gray-200/80 shadow-xl shadow-gray-200/40 p-2 max-w-5xl mx-auto">
          <div className="rounded-2xl bg-gray-50 p-8">
            {/* Mini dashboard */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              {[
                { label: 'Active Monitors', value: '24', trend: '+3 this week', color: 'text-teal-600' },
                { label: 'Changes Detected', value: '156', trend: '12 today', color: 'text-amber-600' },
                { label: 'Alerts Sent', value: '47', trend: '8 critical', color: 'text-rose-600' },
              ].map((stat) => (
                <div key={stat.label} className="bg-white rounded-2xl p-5 border border-gray-100">
                  <div className="text-sm text-gray-400 mb-1">{stat.label}</div>
                  <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                  <div className={`text-xs mt-1 ${stat.color}`}>{stat.trend}</div>
                </div>
              ))}
            </div>

            {/* Recent alerts */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-50 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900">Recent Alerts</span>
                <span className="text-xs text-gray-400">View all →</span>
              </div>
              {[
                { severity: 'Critical', color: 'bg-rose-100 text-rose-700', name: 'Stripe', change: 'New usage-based pricing model announced', time: '5m ago' },
                { severity: 'High', color: 'bg-amber-100 text-amber-700', name: 'Linear', change: 'Launched new project management feature', time: '2h ago' },
                { severity: 'Medium', color: 'bg-teal-100 text-teal-700', name: 'Notion', change: 'Added 15 new AI-related job openings', time: '4h ago' },
              ].map((alert, i) => (
                <div key={i} className="px-5 py-3.5 flex items-center gap-3 hover:bg-gray-50/50 transition border-t border-gray-50 first:border-t-0">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${alert.color}`}>{alert.severity}</span>
                  <span className="text-sm font-medium text-gray-900 w-20">{alert.name}</span>
                  <span className="text-sm text-gray-500 flex-1">{alert.change}</span>
                  <span className="text-xs text-gray-300">{alert.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-8 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-gray-900">Built for competitive teams</h2>
          <p className="mt-3 text-gray-400 max-w-md mx-auto">
            Every feature designed to turn competitor activity into strategic advantage.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            { icon: Eye, title: 'Page Monitoring', desc: 'Track any public URL. Pricing pages, changelogs, job boards, homepages, docs — if it has a URL, we can watch it.', color: 'bg-teal-100 text-teal-700' },
            { icon: Filter, title: 'Noise Filtering', desc: 'Timestamps, session tokens, build hashes, ad IDs — stripped automatically so only real changes surface.', color: 'bg-amber-100 text-amber-700' },
            { icon: Sparkles, title: 'AI Classification', desc: 'Each change is classified as critical, high, medium, low, or noise — with a human-readable summary.', color: 'bg-violet-100 text-violet-700' },
            { icon: Bell, title: 'Smart Alerts', desc: 'Slack and email with severity routing. Digest mode bundles low-priority changes into a daily summary.', color: 'bg-rose-100 text-rose-700' },
            { icon: Layers, title: 'Full History', desc: 'Every snapshot, diff, and classification stored. Drill into any change and see what evolved over time.', color: 'bg-blue-100 text-blue-700' },
            { icon: BarChart2, title: 'Cost Control', desc: 'Noise filtering saves 80% of AI costs. Rate limits and circuit breakers keep your spend predictable.', color: 'bg-emerald-100 text-emerald-700' },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-2xl p-6 border border-gray-100 hover:shadow-lg hover:shadow-gray-200/40 transition">
              <div className={`w-10 h-10 rounded-xl ${f.color} flex items-center justify-center mb-4`}>
                <f.icon className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="bg-white py-24">
        <div className="max-w-6xl mx-auto px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">Simple setup, powerful results</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
            <div className="hidden md:block absolute top-8 left-[12.5%] right-[12.5%] h-0.5 bg-gradient-to-r from-teal-200 via-amber-200 to-rose-200" />
            {[
              { num: 1, title: 'Add URLs', desc: 'Paste competitor page URLs and configure check intervals.', emoji: '🔗' },
              { num: 2, title: 'Auto-scrape', desc: 'We fetch and extract text content on your schedule.', emoji: '🔄' },
              { num: 3, title: 'AI analyzes', desc: 'Changes are diffed, filtered, and classified by severity.', emoji: '🧠' },
              { num: 4, title: 'Get alerted', desc: 'Critical changes hit Slack instantly. Digest the rest daily.', emoji: '🔔' },
            ].map((step) => (
              <div key={step.num} className="text-center relative z-10">
                <div className="w-16 h-16 rounded-2xl bg-[#FAFAF8] border border-gray-100 flex items-center justify-center text-2xl mx-auto mb-4 shadow-sm">
                  {step.emoji}
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">{step.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-8 py-24">
        <div className="rounded-3xl bg-gray-900 p-16 text-center relative overflow-hidden">
          <div className="absolute inset-0 opacity-20" style={{
            backgroundImage: `radial-gradient(circle at 30% 50%, rgba(20, 184, 166, 0.3), transparent 50%), radial-gradient(circle at 70% 50%, rgba(245, 158, 11, 0.3), transparent 50%)`,
          }} />
          <div className="relative z-10">
            <h2 className="text-3xl font-bold text-white mb-4">Ready to see what you've been missing?</h2>
            <p className="text-gray-400 mb-8 max-w-md mx-auto">
              Start monitoring competitors in minutes. Free to get started, no credit card needed.
            </p>
            <button className="px-8 py-3.5 bg-white text-gray-900 rounded-full font-semibold hover:bg-gray-100 transition">
              Create Free Account
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8">
        <div className="max-w-6xl mx-auto px-8 flex items-center justify-between text-sm text-gray-300">
          <span>Shadow — Competitor Intelligence Monitor</span>
          <span>v0.1.0</span>
        </div>
      </footer>
    </div>
  )
}
