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
    <div className="admin-shell admin-login-page">
      <section className="admin-card admin-login-card">
        <div className="admin-card-label">Court signup admin</div>
        <h1 className="admin-card-title">Admin sign in</h1>
        <p className="admin-login-copy">
          Use your authorized Google account to manage sessions, rosters, and player records.
        </p>
        <div className="admin-login-action">
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
      </section>
    </div>
  )
}
