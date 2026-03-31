import { useEffect, useState } from 'react'

import { loginWithGoogle, logoutFromServer, verifyAuth } from '../api/client'

interface AuthState {
  email: string | null
  loading: boolean
}

export function useAdminAuth() {
  const [state, setState] = useState<AuthState>({
    email: null,
    loading: true,
  })

  // On mount, verify the cookie-based session with the server
  useEffect(() => {
    verifyAuth().then((result) => {
      setState({ email: result?.email ?? null, loading: false })
    })
  }, [])

  async function logout() {
    await logoutFromServer()
    setState({ email: null, loading: false })
  }

  async function loginWithIdToken(idToken: string) {
    setState((current) => ({ ...current, loading: true }))
    try {
      const result = await loginWithGoogle(idToken)
      setState({ email: result.email, loading: false })
      return result
    } catch (error) {
      setState((current) => ({ ...current, loading: false }))
      throw error
    }
  }

  return { ...state, loginWithIdToken, logout, isAuthenticated: !!state.email }
}
