export type SignupStatus = 'confirmed' | 'waitlist' | 'cancelled'

export interface Session {
  id: string
  name: string
  date: string
  is_active: boolean
  cancel_window_hours: number
  access_token: string
  created_at: string
}

export interface Court {
  id: string
  session_id: string
  name: string
  start_time: string
  end_time: string
  max_players: number
  total_cost: number
}

export interface Signup {
  id: string
  session_id: string
  timestamp: string
  email: string
  name: string
  status: SignupStatus
  payment_agreed: boolean
  amount_owed: number | null
  amount_adjusted: boolean
  cancelled_at: string | null
  paid: boolean
}

export interface Player {
  email: string
  name: string
  venmo_or_phone: string
  first_seen: string
  last_seen: string
}

export interface PublicSessionResponse {
  session: Session
  courts: Court[]
  signups: Signup[]
  confirmed_count: number
  waitlist_count: number
  total_capacity: number
}

export interface AdminSessionResponse {
  session: Session
  courts: Court[]
  signups: Signup[]
  total_cost: number
  total_capacity: number
  confirmed_count: number
  waitlist_count: number
}

export interface PlayerLookupResponse {
  name: string
  venmo_or_phone: string
}

export interface CancelLookupResponse {
  signup: Signup
  can_cancel: boolean
  reason: string | null
}

export interface CostCalculationResult {
  total_cost: number
  confirmed_count: number
  base_amount: number
}

