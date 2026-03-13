import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import {
  Bell,
  Globe,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Radar,
  Settings,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import api from '../lib/api'

const navItems = [
  {
    to: '/dashboard',
    icon: LayoutDashboard,
    label: 'Overview',
    detail: 'Activity, coverage, and recent changes',
  },
  {
    to: '/monitors',
    icon: Radar,
    label: 'Monitors',
    detail: 'URLs, cadence, and capture settings',
  },
  {
    to: '/alerts',
    icon: Bell,
    label: 'Alerts',
    detail: 'Severity triage and follow-up',
  },
  {
    to: '/settings',
    icon: Settings,
    label: 'Settings',
    detail: 'Profile, notifications, and delivery',
  },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [resending, setResending] = useState(false)
  const [resendMessage, setResendMessage] = useState('')

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleResendVerification = async () => {
    setResending(true)
    setResendMessage('')
    try {
      await api.post('/auth/resend-verification')
      setResendMessage('Verification email sent. Check your inbox.')
    } catch {
      setResendMessage('Could not send email. Try again later.')
    }
    setResending(false)
  }

  const showVerificationBanner = user && !user.is_email_verified

  return (
    <div className="min-h-screen">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 border-r border-slate-800 bg-slate-950 text-slate-100 transition-transform duration-200 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-white/10 px-6 py-5">
            <Link
              to="/dashboard"
              className="flex items-center gap-3"
              onClick={() => setSidebarOpen(false)}
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/10">
                <Globe className="h-5 w-5 text-blue-300" />
              </div>
              <div>
                <div className="text-lg font-semibold text-white">Shadow</div>
                <div className="text-xs tracking-[0.18em] text-slate-400 uppercase">
                  Monitoring Ops
                </div>
              </div>
            </Link>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="rounded-xl p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="px-6 py-5">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-300">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Operational view</p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    Review changes, confirm severity, and keep alerts auditable.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <nav className="flex-1 space-y-1 px-4">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `group flex items-start gap-3 rounded-2xl px-4 py-3 ${
                    isActive
                      ? 'bg-white/10 text-white ring-1 ring-white/10'
                      : 'text-slate-300 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <item.icon className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-semibold">{item.label}</div>
                  <div className="mt-1 text-xs leading-5 text-slate-400 group-hover:text-slate-300">
                    {item.detail}
                  </div>
                </div>
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-white/10 p-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500/15 text-sm font-semibold text-blue-200">
                  {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold text-white">
                    {user?.full_name || 'User'}
                  </div>
                  <div className="truncate text-xs text-slate-400">{user?.email}</div>
                </div>
              </div>
              <button type="button" onClick={handleLogout} className="btn-secondary mt-4 w-full">
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 lg:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm lg:hidden"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <p className="page-kicker">Competitive Intelligence</p>
                <h1 className="text-sm font-semibold text-slate-950 sm:text-base">
                  Shadow operating console
                </h1>
              </div>
            </div>

            <div className="hidden items-center gap-3 sm:flex">
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-right">
                <div className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                  Logged in
                </div>
                <div className="text-sm font-semibold text-slate-900">
                  {user?.full_name || user?.email}
                </div>
              </div>
              <Link to="/monitors/new" className="btn-primary">
                <Radar className="h-4 w-4" />
                New monitor
              </Link>
            </div>
          </div>
        </header>

        {showVerificationBanner && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 lg:px-8">
            <div className="mx-auto flex max-w-7xl items-center gap-3">
              <Mail className="h-4 w-4 shrink-0 text-amber-600" />
              <p className="flex-1 text-sm text-amber-800">
                Verify your email to unlock full access.{' '}
                {resendMessage ? (
                  <span className="font-medium">{resendMessage}</span>
                ) : (
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resending}
                    className="font-semibold underline hover:no-underline disabled:opacity-50"
                  >
                    {resending ? 'Sending...' : 'Resend verification email'}
                  </button>
                )}
              </p>
            </div>
          </div>
        )}

        <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
