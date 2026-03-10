/**
 * Design 3: "Obsidian" — Bold, editorial, high-contrast
 *
 * Personality: Authoritative, magazine-like, for executives and strategists
 * Colors: True black, stark white, single orange accent
 * Layout: Large typography, dramatic whitespace, editorial feel
 */

import { ArrowUpRight, ChevronRight, Radio } from 'lucide-react'

export default function ObsidianLanding() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto border-b border-white/10">
        <span className="text-xl font-bold tracking-tight">Shadow</span>
        <div className="flex items-center gap-8">
          <a href="#about" className="text-sm text-white/40 hover:text-white transition">About</a>
          <a href="#capabilities" className="text-sm text-white/40 hover:text-white transition">Capabilities</a>
          <button className="text-sm px-5 py-2 bg-orange-500 text-black font-semibold rounded hover:bg-orange-400 transition">
            Request Access
          </button>
        </div>
      </nav>

      {/* Hero — editorial style with massive type */}
      <section className="max-w-7xl mx-auto px-8 pt-32 pb-24">
        <div className="flex items-start gap-4 mb-8">
          <Radio className="w-4 h-4 text-orange-500 mt-1 animate-pulse" />
          <span className="text-sm text-orange-500 uppercase tracking-widest font-medium">Real-time competitive intelligence</span>
        </div>

        <h1 className="text-6xl sm:text-8xl font-bold leading-[0.95] tracking-tight max-w-5xl">
          Your competitors
          <br />
          are changing.
          <br />
          <span className="text-white/20">Are you watching?</span>
        </h1>

        <div className="mt-16 flex items-end justify-between border-t border-white/10 pt-8">
          <p className="text-lg text-white/50 max-w-md leading-relaxed">
            Shadow monitors competitor websites around the clock, uses AI to classify
            every change, and delivers actionable intelligence directly to your team.
          </p>
          <button className="flex items-center gap-2 px-6 py-3 bg-orange-500 text-black font-semibold rounded hover:bg-orange-400 transition group">
            Get Started
            <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition" />
          </button>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y border-white/10">
        <div className="max-w-7xl mx-auto px-8 grid grid-cols-2 md:grid-cols-4 divide-x divide-white/10">
          {[
            { value: '6h', label: 'Check interval' },
            { value: '< 5s', label: 'Alert latency' },
            { value: '80%', label: 'Noise filtered' },
            { value: '5', label: 'Severity levels' },
          ].map((stat) => (
            <div key={stat.label} className="py-8 px-6">
              <div className="text-3xl font-bold text-orange-500">{stat.value}</div>
              <div className="text-sm text-white/40 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="max-w-7xl mx-auto px-8 py-32">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-24">
          <div>
            <h2 className="text-sm text-orange-500 uppercase tracking-widest mb-6">Capabilities</h2>
            <h3 className="text-4xl font-bold leading-tight mb-6">
              A complete pipeline from URL to actionable insight
            </h3>
            <p className="text-white/40 leading-relaxed mb-8">
              Shadow doesn't just scrape pages — it understands them. Our six-stage pipeline
              transforms raw HTML into classified competitive intelligence.
            </p>
            <button className="flex items-center gap-2 text-orange-500 hover:text-orange-400 transition text-sm font-medium group">
              See the architecture
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition" />
            </button>
          </div>

          <div className="space-y-6">
            {[
              { title: 'Smart Scraping', desc: 'httpx for static pages, Playwright for SPAs. Auto-detects which method works best.' },
              { title: 'Text Extraction', desc: 'BeautifulSoup strips scripts, styles, and noise. CSS selectors narrow focus to relevant sections.' },
              { title: 'Noise Filtering', desc: '20+ global patterns catch timestamps, session tokens, ad IDs, and build hashes before they waste your attention.' },
              { title: 'AI Classification', desc: 'Claude reads every diff and assigns severity (critical → noise) and categories (pricing, features, hiring, etc.).' },
              { title: 'Alert Suppression', desc: 'Deduplication, severity escalation, and oscillation detection prevent alert fatigue.' },
              { title: 'Multi-Channel Delivery', desc: 'Slack Block Kit messages and HTML emails with severity routing and digest mode.' },
            ].map((item, i) => (
              <div key={i} className="flex gap-6 p-6 border-l-2 border-white/10 hover:border-orange-500 transition group">
                <span className="text-sm font-mono text-white/20 group-hover:text-orange-500 transition">0{i + 1}</span>
                <div>
                  <h4 className="font-semibold mb-1">{item.title}</h4>
                  <p className="text-sm text-white/40 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="about" className="max-w-7xl mx-auto px-8 py-32 border-t border-white/10">
        <div className="max-w-2xl">
          <h2 className="text-5xl font-bold leading-tight mb-8">
            Stop guessing.
            <br />
            Start knowing.
          </h2>
          <p className="text-white/40 mb-8 leading-relaxed">
            Every hour your competitors make changes you don't see. Shadow turns
            that blind spot into your strategic advantage.
          </p>
          <button className="px-8 py-4 bg-orange-500 text-black font-semibold rounded hover:bg-orange-400 transition">
            Request Early Access
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-8 flex items-center justify-between text-xs text-white/20">
          <span>Shadow © 2026</span>
          <span>Competitor Intelligence Monitor v0.1.0</span>
        </div>
      </footer>
    </div>
  )
}
