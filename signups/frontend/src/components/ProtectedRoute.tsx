import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAdminAuth } from '../auth/useAdminAuth'

interface Props {
  children: ReactNode
}

export default function ProtectedRoute({ children }: Props) {
  const { isAuthenticated, loading } = useAdminAuth()
  if (loading) return null
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />
  }
  return <>{children}</>
}
