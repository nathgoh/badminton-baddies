import type {
  AdminSessionResponse,
  CancelLookupResponse,
  CostCalculationResult,
  Court,
  Player,
  PlayerLookupResponse,
  PublicSessionResponse,
  Session,
  Signup,
} from '../types'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('admin_jwt')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export async function loginWithGoogle(
  idToken: string,
): Promise<{ access_token: string; email: string }> {
  return request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ id_token: idToken }),
  })
}

export async function getPublicSession(token: string): Promise<PublicSessionResponse> {
  return request(`/api/public/${token}`)
}

export async function submitSignup(
  token: string,
  body: {
    email: string
    name: string
    venmo_or_phone: string
    payment_agreed: boolean
  },
): Promise<Signup> {
  return request(`/api/public/${token}/signup`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function lookupPlayer(
  token: string,
  email: string,
): Promise<PlayerLookupResponse> {
  return request(`/api/public/${token}/player-lookup?email=${encodeURIComponent(email)}`)
}

export async function lookupCancel(
  token: string,
  email: string,
): Promise<CancelLookupResponse> {
  return request(`/api/public/${token}/cancel-lookup?email=${encodeURIComponent(email)}`)
}

export async function cancelSignup(
  token: string,
  signupId: string,
  email: string,
): Promise<Signup> {
  return request(`/api/public/${token}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ signup_id: signupId, email }),
  })
}

export async function listSessions(): Promise<Session[]> {
  return request('/api/sessions')
}

export async function createSession(data: {
  name: string
  date: string
  is_active: boolean
  cancel_window_hours: number
}): Promise<Session> {
  return request('/api/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateSession(id: string, data: Partial<Session>): Promise<Session> {
  return request(`/api/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteSession(id: string): Promise<void> {
  return request(`/api/sessions/${id}`, { method: 'DELETE' })
}

export async function createCourt(
  sessionId: string,
  data: {
    name: string
    start_time: string
    end_time: string
    max_players: number
    total_cost: number
  },
): Promise<Court> {
  return request(`/api/sessions/${sessionId}/courts`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteCourt(courtId: string): Promise<void> {
  return request(`/api/courts/${courtId}`, { method: 'DELETE' })
}

export async function getAdminSession(id: string): Promise<AdminSessionResponse> {
  return request(`/api/admin/sessions/${id}`)
}

export async function calculateCosts(
  sessionId: string,
): Promise<CostCalculationResult> {
  return request(`/api/admin/sessions/${sessionId}/calculate-costs`, { method: 'POST' })
}

export async function updateSignupAmount(
  signupId: string,
  amount: number,
): Promise<Signup> {
  return request(`/api/admin/signups/${signupId}`, {
    method: 'PATCH',
    body: JSON.stringify({ amount_owed: amount, amount_adjusted: true }),
  })
}

export async function promoteFromWaitlist(signupId: string): Promise<Signup> {
  return request(`/api/admin/signups/${signupId}/promote`, { method: 'POST' })
}

export async function adminCancelSignup(signupId: string): Promise<Signup> {
  return request(`/api/admin/signups/${signupId}`, { method: 'DELETE' })
}

export async function regenerateToken(sessionId: string): Promise<Session> {
  return request(`/api/admin/sessions/${sessionId}/regenerate-token`, { method: 'POST' })
}

export async function listPlayers(): Promise<Player[]> {
  return request('/api/admin/players')
}

export async function updatePlayer(
  email: string,
  data: { name?: string; venmo_or_phone?: string },
): Promise<Player> {
  return request(`/api/admin/players/${encodeURIComponent(email)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

