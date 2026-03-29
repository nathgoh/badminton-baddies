import { GoogleLogin } from '@react-oauth/google'
import { useNavigate } from 'react-router-dom'

import { useAdminAuth } from '../auth/useAdminAuth'

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default function AdminLogin() {
  const { loginWithIdToken } = useAdminAuth()
  const navigate = useNavigate()

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        marginTop: 80,
        fontFamily: 'sans-serif',
      }}
    >
      <h2>HBB Admin Login</h2>
      <GoogleLogin
        onSuccess={async (response) => {
          if (!response.credential) {
            return
          }
          try {
            await loginWithIdToken(response.credential)
            navigate('/admin')
          } catch (error) {
            alert(errorMessage(error))
          }
        }}
        onError={() => alert('Google login failed')}
      />
    </div>
  )
}

