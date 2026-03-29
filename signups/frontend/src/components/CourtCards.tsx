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

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 12,
        marginBottom: 20,
      }}
    >
      {courts.map((court) => {
        const spotsLabel = isFull
          ? `Full${waitlistCount > 0 ? ` · ${waitlistCount} waitlist` : ''}`
          : `${confirmedCount} / ${court.max_players} spots`

        return (
          <div
            key={court.id}
            style={{ border: '1px solid #e0e0e0', borderRadius: 8, padding: 14 }}
          >
            <div style={{ fontWeight: 600 }}>{court.name}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              {formatTime(court.start_time)} - {formatTime(court.end_time)}
            </div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                marginTop: 8,
                color: isFull ? '#c62828' : '#137333',
              }}
            >
              {spotsLabel}
            </div>
          </div>
        )
      })}
    </div>
  )
}

