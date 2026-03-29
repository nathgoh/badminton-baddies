import { useState } from 'react'

import { loginWithGoogle } from '../api/client'

interface AuthState {
  jwt: string | null
  email: string | null
  loading: boolean
}

export function useAdminAuth() {
  const [state, setState] = useState<AuthState>({
    jwt: localStorage.getItem('admin_jwt'),
    email: localStorage.getItem('admin_email'),
    loading: false,
  })

  function logout() {
    localStorage.removeItem('admin_jwt')
    localStorage.removeItem('admin_email')
    setState({ jwt: null, email: null, loading: false })
  }

  async function loginWithIdToken(idToken: string) {
    setState((current) => ({ ...current, loading: true }))
    try {
      const result = await loginWithGoogle(idToken)
      localStorage.setItem('admin_jwt', result.access_token)
      localStorage.setItem('admin_email', result.email)
      setState({ jwt: result.access_token, email: result.email, loading: false })
      return result
    } catch (error) {
      setState((current) => ({ ...current, loading: false }))
      throw error
    }
  }

  return { ...state, loginWithIdToken, logout, isAuthenticated: !!state.jwt }
}

