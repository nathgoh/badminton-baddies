import type { Court } from '../types'
import { formatTime } from '../utils'

interface Props {
  courts: Court[]
  confirmedCount: number
  waitlistCount: number
  totalCapacity: number
}

export default function CourtCards({
  courts,
  confirmedCount,
  waitlistCount,
  totalCapacity,
}: Props) {
  const isFull = confirmedCount >= totalCapacity
  const totalSpotsLabel = isFull
    ? `Full${waitlistCount > 0 ? ` · ${waitlistCount} waitlist` : ''}`
    : `${totalCapacity - confirmedCount} spot${
        totalCapacity - confirmedCount === 1 ? '' : 's'
      } left before waitlist`

  return (
    <section className="public-signup-summary">
      <div className="public-signup-summary-header">
        <div>
          <div className="public-signup-summary-label">Session Summary</div>
          <div className="public-signup-summary-value">{totalSpotsLabel}</div>
        </div>
        <div className={`public-signup-summary-status ${isFull ? 'is-full' : 'is-open'}`}>
          {isFull ? 'Full' : 'Open'}
        </div>
      </div>
      <div className="public-signup-courts-label">Courts</div>
      <div className="public-signup-courts-list">
        {courts.map((court) => (
          <div key={court.id} className="public-signup-court-row">
            <span>
              <strong>{court.name}</strong> · {formatTime(court.start_time)} -{' '}
              {formatTime(court.end_time)}
            </span>
            <span>
              {court.max_players} spot{court.max_players === 1 ? '' : 's'}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
