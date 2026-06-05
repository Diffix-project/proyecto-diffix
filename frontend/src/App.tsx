import { Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut } from '@clerk/clerk-react'
import { useClerkToken } from '@/hooks/useClerkToken'
import AppLayout from '@/components/AppLayout'

// Páginas
import LandingPage from '@/features/auth/LandingPage'
import LoginPage from '@/features/auth/LoginPage'
import RegisterPage from '@/features/auth/RegisterPage'
import DashboardPage from '@/features/dashboard/DashboardPage'
import CompetitorsPage from '@/features/competitors/CompetitorsPage'
import NewCompetitorPage from '@/features/competitors/NewCompetitorPage'
import CompetitorDetailPage from '@/features/competitors/CompetitorDetailPage'
import SettingsPage from '@/features/settings/SettingsPage'
import BillingPage from '@/features/billing/BillingPage'

export default function App() {
  // Registra el getter del token de Clerk en el cliente axios.
  useClerkToken()

  return (
    <Routes>
      {/* Ruta raíz: redirige a /dashboard si autenticado, sino muestra landing */}
      <Route
        path="/"
        element={
          <>
            <SignedIn>
              <Navigate to="/dashboard" replace />
            </SignedIn>
            <SignedOut>
              <LandingPage />
            </SignedOut>
          </>
        }
      />

      {/* Auth (no requieren estar logueado) */}
      <Route path="/login/*" element={<LoginPage />} />
      <Route path="/register/*" element={<RegisterPage />} />

      {/* Rutas autenticadas con layout de sidebar */}
      <Route
        element={
          <>
            <SignedIn>
              <AppLayout />
            </SignedIn>
            <SignedOut>
              <Navigate to="/login" replace />
            </SignedOut>
          </>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/competitors" element={<CompetitorsPage />} />
        <Route path="/competitors/new" element={<NewCompetitorPage />} />
        <Route path="/competitors/:id" element={<CompetitorDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/billing" element={<BillingPage />} />
      </Route>
    </Routes>
  )
}
