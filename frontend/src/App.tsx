import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import LandingPage from './landing-pages/Design4_Aurora'
import ClosedBetaSignup from './pages/ClosedBetaSignup'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/closed-beta" element={<ClosedBetaSignup />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
