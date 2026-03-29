import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'

import ProtectedRoute from './components/ProtectedRoute'
import AdminLogin from './pages/AdminLogin'
import AdminPlayers from './pages/AdminPlayers'
import AdminSessionDetail from './pages/AdminSessionDetail'
import AdminSessionList from './pages/AdminSessionList'
import SignupPage from './pages/SignupPage'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <Routes>
          <Route path="/s/:token" element={<SignupPage />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminSessionList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/sessions/:id"
            element={
              <ProtectedRoute>
                <AdminSessionDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/players"
            element={
              <ProtectedRoute>
                <AdminPlayers />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/admin/login" replace />} />
        </Routes>
      </BrowserRouter>
    </GoogleOAuthProvider>
  )
}
