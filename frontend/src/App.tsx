import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuth } from './hooks/useAuth'
import AppLayout from './components/AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Monitors from './pages/Monitors'
import MonitorDetail from './pages/MonitorDetail'
import MonitorForm from './pages/MonitorForm'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import LandingPage from './landing-pages/Design4_Aurora'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="panel w-full max-w-sm p-8 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <div className="mt-4 text-sm font-medium text-slate-700">Loading your workspace</div>
        </div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (user) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  const { loadFromStorage } = useAuth()

  useEffect(() => {
    loadFromStorage()
  }, [loadFromStorage])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PublicRoute><LandingPage /></PublicRoute>} />
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/monitors" element={<Monitors />} />
          <Route path="/monitors/new" element={<MonitorForm />} />
          <Route path="/monitors/:id" element={<MonitorDetail />} />
          <Route path="/monitors/:id/edit" element={<MonitorForm />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
