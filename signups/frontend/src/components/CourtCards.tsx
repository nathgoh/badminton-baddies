import type { Court } from '../types'
import { formatCancellationStatus, formatTime } from '../utils'

interface Props {
  courts: Court[]
  confirmedCount: number
  waitlistCount: number
  totalCapacity: number
  sessionDate: string
  cancelWindowHours: number
}

export default function CourtCards({
  courts,
  confirmedCount,
  waitlistCount: _waitlistCount,
  totalCapacity,
  sessionDate,
  cancelWindowHours,
}: Props) {
  const isFull = confirmedCount >= totalCapacity
  const remainingSpots = totalCapacity - confirmedCount
  const summaryValue = isFull
    ? null
    : `${remainingSpots} spot${remainingSpots === 1 ? '' : 's'} left before waitlist`
  const cancellationStatus = formatCancellationStatus(sessionDate, cancelWindowHours)

  return (
    <section className="public-signup-summary">
      <div className="public-signup-summary-header">
        <div>
          <div className="public-signup-summary-label">Session Summary</div>
        </div>
        <div className={`public-signup-summary-status ${isFull ? 'is-full' : 'is-open'}`}>
          {isFull ? 'Full' : 'Open'}
        </div>
      </div>
      <div className="public-signup-summary-body">
        {summaryValue ? <div className="public-signup-summary-value">{summaryValue}</div> : null}
        <div className="public-signup-summary-meta">{cancellationStatus}</div>
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
