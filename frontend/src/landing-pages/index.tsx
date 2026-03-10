/**
 * Landing page design directory — preview all options and switch between them.
 */

import { useState } from 'react'
import RadarLanding from './Design1_Radar'
import PrismLanding from './Design2_Prism'
import ObsidianLanding from './Design3_Obsidian'
import AuroraLanding from './Design4_Aurora'

const designs = [
  { id: 'radar', name: 'Radar', desc: 'Dark, terminal-inspired, data-dense', component: RadarLanding },
  { id: 'prism', name: 'Prism', desc: 'Clean SaaS, indigo gradients, polished', component: PrismLanding },
  { id: 'obsidian', name: 'Obsidian', desc: 'Bold editorial, black + orange accent', component: ObsidianLanding },
  { id: 'aurora', name: 'Aurora', desc: 'Warm, rounded, teal + amber, friendly', component: AuroraLanding },
]

export default function DesignDirectory() {
  const [active, setActive] = useState<string | null>(null)

  if (active) {
    const design = designs.find(d => d.id === active)
    if (design) {
      const Component = design.component
      return (
        <div>
          {/* Floating back button */}
          <button
            onClick={() => setActive(null)}
            className="fixed top-4 right-4 z-50 px-4 py-2 bg-black/80 text-white text-sm rounded-lg backdrop-blur-sm hover:bg-black/90 transition shadow-lg"
          >
            ← Back to Directory
          </button>
          <Component />
        </div>
      )
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-2">Landing Page Designs</h1>
        <p className="text-gray-400 mb-10">Click a design to preview it full-screen. Click "Back to Directory" to return here.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {designs.map((d) => (
            <button
              key={d.id}
              onClick={() => setActive(d.id)}
              className="text-left p-6 rounded-2xl border border-gray-800 bg-gray-900/50 hover:border-gray-600 hover:bg-gray-900 transition group"
            >
              <div className="text-xs font-mono text-gray-500 mb-2 uppercase tracking-wider">Design {designs.indexOf(d) + 1}</div>
              <h2 className="text-xl font-bold text-white mb-1 group-hover:text-blue-400 transition">{d.name}</h2>
              <p className="text-sm text-gray-400">{d.desc}</p>
              <div className="mt-4 text-xs text-blue-400 opacity-0 group-hover:opacity-100 transition">Click to preview →</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
