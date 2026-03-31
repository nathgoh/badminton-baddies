import { GoogleLogin } from '@react-oauth/google'
import { useNavigate } from 'react-router-dom'

import { useAdminAuth } from '../auth/useAdminAuth'
import Card from '../components/ui/Card'

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default function AdminLogin() {
  const { loginWithIdToken } = useAdminAuth()
  const navigate = useNavigate()

  return (
    <div
      data-testid="admin-login-shell"
      className="mx-auto flex min-h-screen max-w-6xl items-center px-4 py-6 sm:px-6 lg:px-8"
    >
      <div className="grid w-full gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)] lg:items-center">
        <section className="relative overflow-hidden rounded-[2rem] bg-ink-950 px-5 py-6 text-white shadow-soft sm:px-8 sm:py-8">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(245,158,11,0.22),_transparent_32%)]" />
          <div className="relative space-y-5">
            <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sand-50">
              Court signup admin
            </div>
            <div className="space-y-3">
              <h1 className="max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl">
                Admin sign in
              </h1>
              <p className="max-w-2xl text-sm text-slate-200 sm:text-base">
                Access session setup, roster changes, and player records from the mobile-first admin
                workspace.
              </p>
            </div>
            <div className="grid gap-3 text-sm text-slate-200 sm:grid-cols-2">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                Create and adjust sessions without leaving the queue.
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                Keep roster and payment updates accessible from any device.
              </div>
            </div>
          </div>
        </section>

        <Card
          data-testid="admin-login-card"
          className="relative overflow-hidden border-sand-100 bg-white/95 shadow-soft"
        >
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-amber-400 via-emerald-400 to-sky-500" />
          <div className="relative space-y-5">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
                Authorized access
              </p>
              <h2 className="text-2xl font-semibold text-ink-950">Continue with Google</h2>
              <p className="text-sm text-ink-700">
                Use your approved Google account to open the admin dashboard.
              </p>
            </div>

            <div className="rounded-[1.5rem] border border-sand-100 bg-sand-50/80 p-4">
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

            <p className="text-xs text-ink-700">
              If access is denied, confirm that your account is on the admin allowlist.
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}
