import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

interface Props {
  children: ReactNode
}

export default function ProtectedRoute({ children }: Props) {
  const jwt = localStorage.getItem('admin_jwt')
  if (!jwt) {
    return <Navigate to="/admin/login" replace />
  }
  return <>{children}</>
}

