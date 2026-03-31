import type { Signup } from '../types'
import Card from './ui/Card'

interface Props {
  signups: Signup[]
}

export default function RosterTab({ signups }: Props) {
  const confirmed = signups.filter((signup) => signup.status === 'confirmed')
  const waitlisted = signups.filter((signup) => signup.status === 'waitlist')

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card data-testid="roster-confirmed-card" className="space-y-5">
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Confirmed</div>
          <div className="text-2xl font-semibold text-ink-950">
            {confirmed.length} {confirmed.length === 1 ? 'player' : 'players'} in this session
          </div>
        </div>

        <div className="space-y-3">
          {confirmed.length === 0 ? (
            <div className="rounded-[1.5rem] bg-sand-50/80 px-4 py-3 text-sm text-ink-700">
              No confirmed players yet
            </div>
          ) : (
            confirmed.map((signup, index) => (
              <div
                key={signup.id}
                className="flex items-center gap-3 rounded-[1.5rem] border border-sand-100 bg-white/80 px-4 py-3"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-700">
                  {index + 1}
                </div>
                <span className="font-medium text-ink-950">{signup.name}</span>
              </div>
            ))
          )}
        </div>
      </Card>

      {waitlisted.length > 0 ? (
        <Card data-testid="roster-waitlist-card" className="space-y-5">
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
              Waitlist
            </div>
            <div className="text-2xl font-semibold text-ink-950">
              {waitlisted.length} {waitlisted.length === 1 ? 'player waiting' : 'players waiting'}
            </div>
          </div>

          <div className="space-y-3">
            {waitlisted.map((signup, index) => (
              <div
                key={signup.id}
                className="flex items-center gap-3 rounded-[1.5rem] border border-amber-200 bg-amber-50/70 px-4 py-3"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-100 text-sm font-semibold text-amber-700">
                  W{index + 1}
                </div>
                <span className="font-medium text-ink-950">{signup.name}</span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  )
}
