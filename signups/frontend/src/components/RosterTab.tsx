import type { Signup } from '../types'

interface Props {
  signups: Signup[]
}

export default function RosterTab({ signups }: Props) {
  const confirmed = signups.filter((signup) => signup.status === 'confirmed')
  const waitlisted = signups.filter((signup) => signup.status === 'waitlist')

  return (
    <div className="public-roster">
      <section className="public-roster-card public-roster-card-confirmed">
        <div className="public-roster-card-header">
          <div className="public-roster-card-label">Confirmed</div>
          <div className="public-roster-card-title">
            {confirmed.length} {confirmed.length === 1 ? 'player' : 'players'} in this session
          </div>
        </div>

        <div className="public-roster-list">
          {confirmed.length === 0 ? (
            <div className="public-roster-empty">No confirmed players yet</div>
          ) : (
            confirmed.map((signup, index) => (
              <div key={signup.id} className="public-roster-row">
                <div className="public-roster-badge">{index + 1}</div>
                <span className="public-roster-name">{signup.name}</span>
              </div>
            ))
          )}
        </div>
      </section>

      {waitlisted.length > 0 ? (
        <section className="public-roster-card public-roster-card-waitlist">
          <div className="public-roster-card-header">
            <div className="public-roster-card-label public-roster-card-label-waitlist">Waitlist</div>
            <div className="public-roster-card-title">
              {waitlisted.length} {waitlisted.length === 1 ? 'player waiting' : 'players waiting'}
            </div>
          </div>

          <div className="public-roster-list">
            {waitlisted.map((signup, index) => (
              <div key={signup.id} className="public-roster-row public-roster-row-waitlist">
                <div className="public-roster-badge public-roster-badge-waitlist">W{index + 1}</div>
                <span className="public-roster-name public-roster-name-waitlist">{signup.name}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
