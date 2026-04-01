import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import {
  ArrowRight,
  Bell,
  Clock3,
  Eye,
  FileText,
  GitCompareArrows,
  LayoutDashboard,
  Radar,
  Settings,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'

/* ═══════════════════════════════════════════════════════════════════════════
   Scoped styles — keeps landing page self-contained
   ═══════════════════════════════════════════════════════════════════════════ */
const scopedStyles = `
  html:has(.sh-landing) {
    scrollbar-gutter: stable;
  }
  .sh-landing {
    --sh-ff: 'Space Grotesk', 'Avenir Next', 'Segoe UI', system-ui, sans-serif;
    --sh-ease: cubic-bezier(0.16, 1, 0.3, 1);
  }
  .sh-landing * { box-sizing: border-box; }
  .sh-landing a { text-decoration: none; }

  /* Buttons — explicit colors override inherited link color */
  .sh-btn {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--sh-ff); font-weight: 600; border-radius: 12px;
    transition: background 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    cursor: pointer; border: none;
  }
  .sh-landing .sh-btn-dark,
  .sh-landing a.sh-btn-dark {
    background: #0f172a; color: #fff;
  }
  .sh-landing .sh-btn-dark:hover,
  .sh-landing a.sh-btn-dark:hover {
    background: #1e293b; box-shadow: 0 8px 24px -8px rgba(15, 23, 42, 0.25);
    transform: translateY(-1px);
  }
  .sh-btn-dark:active { transform: translateY(0); box-shadow: none; }

  .sh-landing .sh-btn-outline,
  .sh-landing a.sh-btn-outline {
    background: #fff; color: #334155; border: 1px solid #e2e8f0;
  }
  .sh-landing .sh-btn-outline:hover,
  .sh-landing a.sh-btn-outline:hover {
    background: #f8fafc; border-color: #cbd5e1;
  }

  .sh-landing .sh-nav-link,
  .sh-landing a.sh-nav-link {
    font-size: 14px; font-weight: 500; color: #64748b;
    transition: color 160ms ease;
  }
  .sh-nav-link:hover { color: #0f172a; }

  /* Product mockup glow + float animation */
  .sh-mockup-wrapper {
    position: relative;
    animation: sh-float 6s ease-in-out infinite;
  }
  .sh-mockup-wrapper::before {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: 20px;
    background: linear-gradient(180deg, #e2e8f0 0%, #f1f5f9 100%);
    z-index: -1;
  }
  .sh-mockup-wrapper::after {
    content: '';
    position: absolute;
    inset: 40px;
    border-radius: 40px;
    background: radial-gradient(ellipse at 50% 0%, rgba(37, 99, 235, 0.08) 0%, transparent 70%);
    z-index: -1;
    filter: blur(40px);
  }

  @keyframes sh-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }

  /* Sidebar active indicator pulse */
  .sh-sidebar-pulse {
    animation: sh-pulse 2.5s ease-in-out infinite;
  }
  @keyframes sh-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* Feature cards */
  .sh-feature {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 32px;
    transition: box-shadow 200ms ease, border-color 200ms ease, transform 200ms ease;
  }
  .sh-feature:hover {
    border-color: #cbd5e1;
    box-shadow: 0 16px 40px -16px rgba(15, 23, 42, 0.1);
    transform: translateY(-2px);
  }

  /* CTA banner subtle shimmer */
  .sh-cta-banner {
    position: relative;
    overflow: hidden;
  }
  .sh-cta-banner::after {
    content: '';
    position: absolute;
    top: 0; left: -100%; width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.04), transparent);
    animation: sh-shimmer 8s ease-in-out infinite;
  }
  @keyframes sh-shimmer {
    0%, 100% { left: -100%; }
    50% { left: 150%; }
  }

  /* Word flip animation */
  .sh-word-flip {
    display: inline-block;
    position: relative;
    vertical-align: baseline;
    overflow: hidden;
  }
  .sh-word-flip-item {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    text-align: left;
    transition: transform 550ms var(--sh-ease), opacity 350ms ease;
    will-change: transform, opacity;
  }
  .sh-word-flip-item[data-state="enter"] {
    transform: translateY(0);
    opacity: 1;
  }
  .sh-word-flip-item[data-state="exit-up"] {
    transform: translateY(-110%);
    opacity: 0;
  }
  .sh-word-flip-item[data-state="below"] {
    transform: translateY(110%);
    opacity: 0;
    transition: none;
  }

  /* Gradient background drift */
  @keyframes sh-gradient-drift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  /* Step number hover */
  .sh-step-num {
    transition: transform 300ms var(--sh-ease), background 300ms ease;
  }
  .sh-step-num:hover {
    transform: scale(1.12);
    background: #2563eb !important;
  }

  /* Feature card icon float on hover */
  .sh-feature:hover .sh-feature-icon {
    transform: translateY(-3px);
  }
  .sh-feature-icon {
    transition: transform 300ms var(--sh-ease);
  }

  @media (prefers-reduced-motion: reduce) {
    .sh-reveal { transition-duration: 0.01ms !important; transform: none !important; }
    .sh-mockup-wrapper { animation: none !important; }
    .sh-sidebar-pulse { animation: none !important; }
    .sh-cta-banner::after { animation: none !important; }
  }

  /* Integration cards */
  .sh-int-card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 16px;
    padding: 28px; transition: box-shadow 200ms ease, border-color 200ms ease;
  }
  .sh-int-card:hover {
    border-color: #cbd5e1; box-shadow: 0 8px 24px -8px rgba(15, 23, 42, 0.08);
  }

  /* Page type tags */
  .sh-tag {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 500;
    border: 1px solid #e2e8f0; background: #f8fafc; color: #334155;
    transition: border-color 160ms ease, background 160ms ease;
  }
  .sh-tag:hover { border-color: #cbd5e1; background: #fff; }

  /* Morph page animation */
  .sh-morph-page {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    overflow: hidden;
    font-family: var(--sh-ff);
    box-shadow: 0 8px 32px -8px rgba(15, 23, 42, 0.1);
  }
  .sh-morph-row {
    transition: opacity 600ms ease, transform 600ms var(--sh-ease);
  }
  .sh-morph-row[data-visible="false"] {
    opacity: 0;
    transform: translateY(8px);
  }
  .sh-morph-row[data-visible="true"] {
    opacity: 1;
    transform: translateY(0);
  }
  .sh-morph-val {
    transition: opacity 400ms ease;
    position: relative;
  }
  .sh-morph-highlight {
    position: absolute;
    inset: -2px -6px;
    border-radius: 4px;
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.2);
    opacity: 0;
    transition: opacity 400ms ease 200ms;
  }
  .sh-morph-highlight[data-active="true"] {
    opacity: 1;
  }

  @media (max-width: 768px) {
    .sh-hero-grid { grid-template-columns: 1fr !important; }
    .sh-hero-morph { display: none !important; }
    .sh-hero-text { text-align: center !important; align-items: center !important; }
    .sh-feature-grid { grid-template-columns: 1fr !important; }
    .sh-hero-ctas { flex-direction: column !important; align-items: stretch !important; }
    .sh-mockup-sidebar { display: none !important; }
    .sh-mockup-grid { grid-template-columns: 1fr !important; }
    .sh-stats-grid { grid-template-columns: repeat(2, 1fr) !important; }
    .sh-step-grid { grid-template-columns: 1fr !important; }
    .sh-cta-row { flex-direction: column !important; align-items: flex-start !important; }
    .sh-int-grid { grid-template-columns: 1fr !important; }
  }
`

/* ─── Font loader ───────────────────────────────────────────────────────── */
function useFontLoader() {
  useEffect(() => {
    if (document.querySelector('[data-sh-fonts]')) return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap'
    link.setAttribute('data-sh-fonts', '')
    document.head.appendChild(link)
  }, [])
}

/* ─── Scroll reveal ─────────────────────────────────────────────────────── */
function useInView(threshold = 0.1) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); obs.unobserve(el) } },
      { threshold },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, visible }
}

function Reveal({ children, delay = 0, style }: { children: ReactNode; delay?: number; style?: CSSProperties }) {
  const { ref, visible } = useInView()
  return (
    <div ref={ref} className="sh-reveal" style={{
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0)' : 'translateY(24px)',
      transition: `opacity 650ms var(--sh-ease) ${delay}ms, transform 650ms var(--sh-ease) ${delay}ms`,
      ...style,
    }}>
      {children}
    </div>
  )
}

/* ─── Flip words ────────────────────────────────────────────────────────── */
function FlipWords({ words, interval = 2200 }: { words: string[]; interval?: number }) {
  const [index, setIndex] = useState(0)
  const [prevIndex, setPrevIndex] = useState<number | null>(null)

  useEffect(() => {
    const id = setInterval(() => {
      setPrevIndex(index)
      setIndex(i => (i + 1) % words.length)
    }, interval)
    return () => clearInterval(id)
  }, [index, words.length, interval])

  const longest = useMemo(
    () => words.reduce((a, b) => a.length > b.length ? a : b, ''),
    [words],
  )

  return (
    <span className="sh-word-flip" style={{
      height: '1.15em',
      lineHeight: 'inherit',
      color: '#2563eb',
    }}>
      {/* Invisible sizer — extra padding prevents period clipping */}
      <span style={{ visibility: 'hidden' }}>{longest}<span style={{ letterSpacing: '0.05em' }}>&nbsp;</span></span>
      {words.map((word, i) => {
        let state = 'below'
        if (i === index) state = 'enter'
        else if (i === prevIndex) state = 'exit-up'
        return (
          <span key={word} className="sh-word-flip-item" data-state={state}>
            {word}
          </span>
        )
      })}
    </span>
  )
}

/* ─── Page morph animation ──────────────────────────────────────────────── */
const diffSnapshots = [
  {
    competitor: 'Linear',
    url: 'linear.app/pricing',
    changes: [
      { type: 'removed' as const, text: 'Free plan — up to 250 issues' },
      { type: 'added' as const, text: 'Free plan — up to 50 issues' },
      { type: 'unchanged' as const, text: 'Standard — $8/user/mo' },
      { type: 'removed' as const, text: 'Plus — $12/user/mo' },
      { type: 'added' as const, text: 'Plus — $14/user/mo' },
      { type: 'unchanged' as const, text: 'Enterprise — custom pricing' },
    ],
    severity: 'CRITICAL',
    summary: 'Free tier limit reduced, Plus plan price increase',
  },
  {
    competitor: 'Notion',
    url: 'notion.so/product',
    changes: [
      { type: 'unchanged' as const, text: 'Docs, wikis, and projects' },
      { type: 'added' as const, text: 'AI-powered search across workspace' },
      { type: 'unchanged' as const, text: 'Real-time collaboration' },
      { type: 'added' as const, text: 'Notion Mail — unified inbox' },
      { type: 'unchanged' as const, text: 'Custom automations' },
      { type: 'removed' as const, text: 'API access on all plans' },
    ],
    severity: 'HIGH',
    summary: 'Two features added, API access restricted',
  },
  {
    competitor: 'Stripe',
    url: 'stripe.com/docs/changelog',
    changes: [
      { type: 'added' as const, text: 'v2025-03 API — breaking changes' },
      { type: 'removed' as const, text: 'Deprecated: /v1/charges endpoint' },
      { type: 'unchanged' as const, text: 'Payment Intents API' },
      { type: 'unchanged' as const, text: 'Billing portal' },
      { type: 'added' as const, text: 'Embedded checkout v2' },
      { type: 'removed' as const, text: 'Legacy webhooks sunset Mar 30' },
    ],
    severity: 'HIGH',
    summary: 'API deprecation, new checkout version',
  },
]

function PageMorph() {
  const [activeIdx, setActiveIdx] = useState(0)
  const [displayIdx, setDisplayIdx] = useState(0)
  const [fading, setFading] = useState(false)

  useEffect(() => {
    const id = setInterval(() => {
      setFading(true)
      setTimeout(() => {
        setActiveIdx(i => (i + 1) % diffSnapshots.length)
        setDisplayIdx(i => (i + 1) % diffSnapshots.length)
        setFading(false)
      }, 400)
    }, 4000)
    return () => clearInterval(id)
  }, [])

  const snap = diffSnapshots[displayIdx]
  const sevColor = snap.severity === 'CRITICAL' ? '#dc2626' : '#c2410c'
  const sevBg = snap.severity === 'CRITICAL' ? '#fef2f2' : '#fff7ed'

  return (
    <div className="sh-morph-page" style={{ width: '100%', maxWidth: 400 }}>
      {/* Browser chrome */}
      <div style={{
        padding: '8px 14px', borderBottom: '1px solid #e2e8f0', background: '#f8fafc',
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <div style={{ display: 'flex', gap: 5 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fca5a5' }} />
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fde68a' }} />
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#86efac' }} />
        </div>
        <div style={{
          marginLeft: 8, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 6,
          padding: '3px 12px', fontSize: 10, color: '#94a3b8', flex: 1, maxWidth: 220,
          transition: 'opacity 300ms ease',
          opacity: fading ? 0 : 1,
        }}>
          {snap.url}
        </div>
      </div>

      {/* Diff content */}
      <div style={{
        padding: '16px 18px 20px',
        opacity: fading ? 0 : 1,
        transform: fading ? 'translateY(4px)' : 'translateY(0)',
        transition: 'opacity 350ms ease, transform 350ms ease',
      }}>
        {/* Competitor header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.02em' }}>
              {snap.competitor}
            </div>
            <div style={{ fontSize: 9, color: '#94a3b8', marginTop: 2 }}>
              Last checked 2m ago
            </div>
          </div>
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
            background: sevBg, color: sevColor,
          }}>
            {snap.severity}
          </span>
        </div>

        {/* Diff lines */}
        <div style={{
          background: '#fafafa', borderRadius: 8, border: '1px solid #e2e8f0',
          padding: '8px 0', fontFamily: 'ui-monospace, "SF Mono", "Cascadia Code", monospace',
        }}>
          {snap.changes.map((line, i) => {
            const colors = {
              added: { bg: '#f0fdf4', color: '#15803d', prefix: '+' },
              removed: { bg: '#fef2f2', color: '#b91c1c', prefix: '−', textDecoration: 'line-through' as const },
              unchanged: { bg: 'transparent', color: '#64748b', prefix: ' ' },
            }
            const c = colors[line.type]
            return (
              <div key={i} style={{
                fontSize: 10, lineHeight: 1.7,
                padding: '1px 12px',
                background: c.bg,
                color: c.color,
                display: 'flex', gap: 8,
                textDecoration: line.type === 'removed' ? 'line-through' : undefined,
              }}>
                <span style={{ opacity: 0.6, flexShrink: 0, width: 10, textAlign: 'center' }}>{c.prefix}</span>
                <span>{line.text}</span>
              </div>
            )
          })}
        </div>

        {/* Summary bar */}
        <div style={{
          marginTop: 12, padding: '7px 10px',
          background: sevBg, borderRadius: 8, border: `1px solid ${snap.severity === 'CRITICAL' ? '#fecaca' : '#fed7aa'}`,
          display: 'flex', alignItems: 'center', gap: 6,
          fontSize: 9, fontWeight: 600, color: sevColor,
        }}>
          <div style={{
            width: 5, height: 5, borderRadius: '50%', background: sevColor,
            animation: 'sh-pulse 2s ease-in-out infinite',
          }} />
          {snap.summary}
        </div>
      </div>

      {/* Step indicators */}
      <div style={{
        padding: '0 18px 14px', display: 'flex', justifyContent: 'center', gap: 6,
      }}>
        {diffSnapshots.map((_, i) => (
          <div key={i} style={{
            width: i === activeIdx ? 16 : 5, height: 5, borderRadius: 3,
            background: i === activeIdx ? '#2563eb' : '#e2e8f0',
            transition: 'width 300ms ease, background 300ms ease',
          }} />
        ))}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   Dashboard mockup — mirrors the real product interface
   ═══════════════════════════════════════════════════════════════════════════ */
function DashboardMockup() {
  const sidebarItems = [
    { icon: LayoutDashboard, label: 'Overview', active: true },
    { icon: Radar, label: 'Monitors' },
    { icon: Bell, label: 'Alerts' },
    { icon: Settings, label: 'Settings' },
  ]

  const stats = [
    { label: 'Active monitors', value: '24', sub: '22 healthy', iconBg: '#eff6ff', iconColor: '#2563eb', Icon: Radar },
    { label: 'Captured snapshots', value: '186', sub: '12 recent changes', iconBg: '#ecfdf5', iconColor: '#059669', Icon: FileText },
    { label: 'Open alerts', value: '8', sub: '2 critical', iconBg: '#fffbeb', iconColor: '#d97706', Icon: Bell },
    { label: 'Healthy coverage', value: '92%', sub: 'No failures reported', iconBg: '#fef2f2', iconColor: '#dc2626', Icon: ShieldCheck },
  ]

  const alerts = [
    { sev: 'CRITICAL', sevBg: '#fef2f2', sevColor: '#be123c', title: 'Stripe deprecated free tier entirely', summary: 'Free plan removed from pricing page — all users migrated to $25/mo Starter', time: '2m ago' },
    { sev: 'HIGH', sevBg: '#fff7ed', sevColor: '#c2410c', title: 'Linear launched AI-powered triage', summary: 'Auto-classification and priority routing now live for all Pro teams', time: '18m ago' },
    { sev: 'MEDIUM', sevBg: '#fffbeb', sevColor: '#b45309', title: 'Notion quietly raised Business plan storage cap', summary: 'Per-file upload limit changed from unlimited to 5GB — not announced in changelog', time: '1h ago' },
  ]

  return (
    <div className="sh-mockup-wrapper" style={{ borderRadius: 20, overflow: 'hidden', border: '1px solid #e2e8f0', background: '#fff' }}>
      {/* Browser chrome */}
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid #e2e8f0', background: '#f8fafc',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#fca5a5' }} />
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#fde68a' }} />
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#86efac' }} />
        </div>
        <div style={{
          marginLeft: 12, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8,
          padding: '4px 16px', fontSize: 12, color: '#94a3b8', flex: 1, maxWidth: 320,
        }}>
          app.shadow.io/dashboard
        </div>
      </div>

      {/* App interface */}
      <div className="sh-mockup-grid" style={{ display: 'grid', gridTemplateColumns: '200px 1fr', minHeight: 420 }}>
        {/* Sidebar */}
        <div className="sh-mockup-sidebar" style={{ background: '#0f172a', padding: '16px 0', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '0 16px 20px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
            <img src="/shadow-logo.png" alt="Shadow" style={{ width: 32, height: 32, borderRadius: 10, objectFit: 'cover' }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>Shadow</div>
              <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.15em', color: '#64748b' }}>Monitoring Ops</div>
            </div>
          </div>

          <div style={{ padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
            {sidebarItems.map(item => (
              <div key={item.label} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                borderRadius: 10, fontSize: 13, fontWeight: 500,
                color: item.active ? '#fff' : '#94a3b8',
                background: item.active ? 'rgba(255,255,255,0.1)' : 'transparent',
              }}>
                <item.icon size={14} />
                {item.label}
                {item.active && (
                  <div className="sh-sidebar-pulse" style={{
                    marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%',
                    background: '#4ade80',
                  }} />
                )}
              </div>
            ))}
          </div>

          <div style={{ marginTop: 'auto', padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8, background: 'rgba(59,130,246,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 600, color: '#93c5fd',
              }}>L</div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 500, color: '#fff' }}>Lebron J.</div>
                <div style={{ fontSize: 10, color: '#64748b' }}>Admin</div>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div style={{ background: '#f8fafc', padding: 20, overflow: 'hidden' }}>
          {/* Header */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94a3b8' }}>Overview</div>
            <div style={{ fontSize: 18, fontWeight: 600, color: '#0f172a', marginTop: 4 }}>Monitoring operations</div>
          </div>

          {/* Stat cards */}
          <div className="sh-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
            {stats.map(stat => (
              <div key={stat.label} style={{
                background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: '14px 16px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 500, color: '#94a3b8' }}>{stat.label}</div>
                    <div style={{ fontSize: 22, fontWeight: 600, color: '#0f172a', marginTop: 6, fontVariantNumeric: 'tabular-nums' }}>{stat.value}</div>
                  </div>
                  <div style={{
                    width: 28, height: 28, borderRadius: 10, background: stat.iconBg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <stat.Icon size={13} color={stat.iconColor} />
                  </div>
                </div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>{stat.sub}</div>
              </div>
            ))}
          </div>

          {/* Alert list */}
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, overflow: 'hidden' }}>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid #e2e8f0',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>Recent alerts</div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>Latest changes routed into the review queue</div>
              </div>
              <div style={{ fontSize: 11, fontWeight: 500, color: '#2563eb', display: 'flex', alignItems: 'center', gap: 4 }}>
                View all <ArrowRight size={11} />
              </div>
            </div>
            {alerts.map((alert, i) => (
              <div key={i} style={{
                padding: '12px 16px',
                borderBottom: i < alerts.length - 1 ? '1px solid #f1f5f9' : undefined,
                display: 'flex', alignItems: 'flex-start', gap: 12,
              }}>
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: '3px 0', borderRadius: 20,
                  background: alert.sevBg, color: alert.sevColor, whiteSpace: 'nowrap', marginTop: 2,
                  width: 62, textAlign: 'center', flexShrink: 0,
                }}>
                  {alert.sev}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{alert.title}</div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{alert.summary}</div>
                </div>
                <div style={{ fontSize: 10, color: '#94a3b8', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                  <Clock3 size={10} /> {alert.time}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   Data
   ═══════════════════════════════════════════════════════════════════════════ */
const features = [
  {
    title: 'Always-on monitoring',
    desc: 'Point Shadow at any competitor page — pricing, changelogs, feature lists, docs, hiring. It watches on your schedule so nothing slips through.',
    Icon: Eye,
    iconBg: '#eff6ff',
    iconColor: '#2563eb',
  },
  {
    title: 'Precise diff detection',
    desc: 'Every revision is compared line-by-line against the last snapshot. You see exactly what changed, when, and how significant it is — no noise.',
    Icon: GitCompareArrows,
    iconBg: '#ecfdf5',
    iconColor: '#059669',
  },
  {
    title: 'Instant alert routing',
    desc: 'Changes are ranked by impact and routed to your team in seconds. Critical pricing shifts surface before minor copy tweaks. Slack, email, or both.',
    Icon: Zap,
    iconBg: '#fffbeb',
    iconColor: '#d97706',
  },
]

const steps = [
  { num: '01', title: 'Add your sources', desc: 'Enter competitor URLs, select page types, and set how frequently Shadow should check for changes.' },
  { num: '02', title: 'Shadow captures and compares', desc: 'Full page snapshots are stored automatically. Every change is detected and logged after each check.' },
  { num: '03', title: 'Triage what matters', desc: 'Alerts route to your team ranked by severity. Acknowledge, investigate, or delegate — all from one queue.' },
]

const pageTypes = [
  { label: 'Pricing pages', desc: 'Track plan changes, feature bundling, and tier restructuring' },
  { label: 'Changelogs', desc: 'Catch feature launches, deprecations, and version updates' },
  { label: 'Feature lists', desc: 'Monitor capability additions, removals, and repositioning' },
  { label: 'Documentation', desc: 'Detect API changes, integration updates, and migration guides' },
  { label: 'Hiring pages', desc: 'Signal new initiatives from role postings and team growth' },
]

/* ═══════════════════════════════════════════════════════════════════════════
   Main component
   ═══════════════════════════════════════════════════════════════════════════ */
export default function AuroraLanding() {
  useFontLoader()
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    const t = requestAnimationFrame(() => setLoaded(true))
    return () => cancelAnimationFrame(t)
  }, [])

  const section = (extra?: CSSProperties): CSSProperties => ({
    width: '100%', maxWidth: 1140, margin: '0 auto', padding: '0 24px', ...extra,
  })

  const stagger = (idx: number, base = 80) => ({
    opacity: loaded ? 1 : 0,
    transform: loaded ? 'translateY(0)' : 'translateY(20px)',
    transition: `opacity 650ms var(--sh-ease) ${base + idx * 120}ms, transform 650ms var(--sh-ease) ${base + idx * 120}ms`,
  } as CSSProperties)

  return (
    <div className="sh-landing" style={{
      minHeight: '100vh',
      width: '100%',
      margin: '0 auto',
      overflowX: 'hidden' as const,
      background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 40%, #f1f5f9 100%)',
      color: '#0f172a',
      fontFamily: 'var(--sh-ff)',
      WebkitFontSmoothing: 'antialiased',
      textRendering: 'optimizeLegibility',
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
    }}>
      <style>{scopedStyles}</style>

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav style={{ width: '100%', ...stagger(0, 0) }}>
        <div style={{
          width: '100%', padding: '20px 40px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img src="/shadow-logo.png" alt="Shadow" style={{ width: 28, height: 28, borderRadius: 6, objectFit: 'cover' }} />
            <span style={{
              fontSize: 22, fontWeight: 700, color: '#0f172a',
              letterSpacing: '-0.04em', lineHeight: 1,
            }}>Shadow</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <a href="#features" className="sh-nav-link">Features</a>
            <Link to="/closed-beta" className="sh-nav-link">Closed beta</Link>
            <Link to="/closed-beta" className="sh-btn sh-btn-dark" style={{ fontSize: 14, padding: '10px 20px' }}>
              Request access <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <section style={section({ paddingTop: 64, paddingBottom: 48 })}>
        <div className="sh-hero-grid" style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, alignItems: 'center',
        }}>
          {/* Left — text */}
          <div className="sh-hero-text" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: '#eff6ff', border: '1px solid #dbeafe', borderRadius: 100,
              padding: '6px 16px', fontSize: 13, fontWeight: 600, color: '#2563eb',
              ...stagger(0),
            }}>
              <ShieldCheck size={14} />
              Competitor intelligence for product teams
            </div>

            <h1 style={{
              marginTop: 24,
              fontSize: 'clamp(32px, 4vw, 50px)',
              fontWeight: 700,
              lineHeight: 1.15,
              letterSpacing: '-0.035em',
              color: '#0f172a',
              ...stagger(1),
            }}>
              Track competitor{' '}
              <FlipWords words={['pricing.', 'launches.', 'signals.', 'moves.', 'strategy.']} />
              <br />Act on what matters.
            </h1>

            <p style={{
              marginTop: 20, fontSize: 16, lineHeight: 1.65, color: '#64748b', maxWidth: 440,
              ...stagger(2),
            }}>
              Shadow monitors competitor pages, captures every revision, detects changes, and routes severity-ranked alerts to your team.
            </p>

            <div className="sh-hero-ctas" style={{
              marginTop: 32, display: 'flex', alignItems: 'center', gap: 12,
              ...stagger(3),
            }}>
              <Link to="/closed-beta" className="sh-btn sh-btn-dark" style={{ fontSize: 15, padding: '14px 28px' }}>
                Join closed beta <ArrowRight size={16} />
              </Link>
              <Link to="/closed-beta" className="sh-btn sh-btn-outline" style={{ fontSize: 15, padding: '14px 24px' }}>
                Request access
              </Link>
            </div>
          </div>

          {/* Right — morphing page animation */}
          <div className="sh-hero-morph" style={{
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            ...stagger(2, 200),
          }}>
            <PageMorph />
          </div>
        </div>
      </section>

      {/* ── Product mockup ──────────────────────────────────────────── */}
      <section style={section({ paddingBottom: 80 })}>
        <Reveal>
          <DashboardMockup />
        </Reveal>
      </section>

      {/* ── Features ────────────────────────────────────────────────── */}
      <section id="features" style={section({ paddingTop: 40, paddingBottom: 80 })}>
        <Reveal>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94a3b8', marginBottom: 12 }}>
              Core capabilities
            </div>
            <h2 style={{ fontSize: 'clamp(26px, 3vw, 36px)', fontWeight: 700, letterSpacing: '-0.025em', color: '#0f172a' }}>
              Everything you need to stay ahead
            </h2>
          </div>
        </Reveal>

        <div className="sh-feature-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          {features.map((feat, i) => (
            <Reveal key={feat.title} delay={i * 80}>
              <div className="sh-feature" style={{ height: '100%' }}>
                <div className="sh-feature-icon" style={{
                  width: 44, height: 44, borderRadius: 14, background: feat.iconBg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20,
                }}>
                  <feat.Icon size={20} color={feat.iconColor} />
                </div>
                <h3 style={{ fontSize: 17, fontWeight: 600, color: '#0f172a', letterSpacing: '-0.01em' }}>
                  {feat.title}
                </h3>
                <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.7, color: '#64748b' }}>
                  {feat.desc}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────── */}
      <section id="how" style={section({ paddingTop: 40, paddingBottom: 80 })}>
        <Reveal>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94a3b8', marginBottom: 12 }}>
              How it works
            </div>
            <h2 style={{ fontSize: 'clamp(26px, 3vw, 36px)', fontWeight: 700, letterSpacing: '-0.025em', color: '#0f172a' }}>
              Set up in minutes, not days
            </h2>
          </div>
        </Reveal>

        <div className="sh-step-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          {steps.map((step, i) => (
            <Reveal key={step.num} delay={i * 80}>
              <div style={{ padding: '0 8px' }}>
                <div className="sh-step-num" style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: '#0f172a', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14, fontWeight: 600, marginBottom: 20, cursor: 'default',
                }}>
                  {step.num}
                </div>
                <h3 style={{ fontSize: 17, fontWeight: 600, color: '#0f172a', letterSpacing: '-0.01em' }}>
                  {step.title}
                </h3>
                <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.7, color: '#64748b' }}>
                  {step.desc}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── What you can monitor ──────────────────────────────────── */}
      <section style={section({ paddingTop: 40, paddingBottom: 80 })}>
        <div className="sh-int-grid" style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 24, alignItems: 'start' }}>
          <Reveal>
            <div className="sh-int-card">
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94a3b8', marginBottom: 12 }}>
                Supported page types
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 20 }}>
                Monitor what matters to your market
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {pageTypes.map(pt => (
                  <div key={pt.label} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: '50%', background: '#2563eb',
                      marginTop: 7, flexShrink: 0,
                    }} />
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>{pt.label}</div>
                      <div style={{ fontSize: 13, color: '#64748b', marginTop: 2, lineHeight: 1.5 }}>{pt.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={120}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div className="sh-int-card">
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.18em', color: '#94a3b8', marginBottom: 12 }}>
                  Notifications
                </div>
                <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 16 }}>
                  Route alerts where your team works
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {['Slack webhooks', 'Email digest', 'Per-channel thresholds', 'Severity filtering', 'Acknowledgement tracking'].map(tag => (
                    <span key={tag} className="sh-tag">{tag}</span>
                  ))}
                </div>
              </div>

            </div>
          </Reveal>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────── */}
      <section style={section({ paddingTop: 20, paddingBottom: 96 })}>
        <Reveal>
          <div className="sh-cta-banner" style={{
            background: '#0f172a', borderRadius: 24, padding: '56px 48px',
            display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
          }}>
            <h2 style={{
              fontSize: 'clamp(24px, 3vw, 32px)', fontWeight: 700,
              color: '#fff', letterSpacing: '-0.025em', maxWidth: 480,
            }}>
              Join the Shadow closed beta
            </h2>
            <p style={{ marginTop: 12, fontSize: 15, color: '#94a3b8', maxWidth: 420, lineHeight: 1.6 }}>
              Share your email and we will invite you when the operating console is ready.
            </p>
            <div className="sh-cta-row" style={{ marginTop: 28, display: 'flex', gap: 12, alignItems: 'center' }}>
              <Link to="/closed-beta" className="sh-btn sh-btn-outline" style={{
                fontSize: 15, padding: '14px 28px', background: '#fff', color: '#0f172a',
                border: 'none',
              }}>
                Request access <ArrowRight size={16} />
              </Link>
              <Link to="/closed-beta" className="sh-nav-link" style={{ fontSize: 14, fontWeight: 500, color: '#94a3b8' }}>
                closed beta form
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer style={{ width: '100%', borderTop: '1px solid #e2e8f0' }}>
        <div style={{
          ...section(), padding: '24px 24px 40px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src="/shadow-logo.png" alt="Shadow" style={{ width: 20, height: 20, borderRadius: 4, objectFit: 'cover' }} />
            <span style={{ fontSize: 15, fontWeight: 600, color: '#94a3b8', letterSpacing: '-0.02em' }}>Shadow</span>
          </div>
          <div style={{ display: 'flex', gap: 20 }}>
            <Link to="/closed-beta" className="sh-nav-link" style={{ fontSize: 13 }}>Closed beta</Link>
            <Link to="/closed-beta" className="sh-nav-link" style={{ fontSize: 13 }}>Request access</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
