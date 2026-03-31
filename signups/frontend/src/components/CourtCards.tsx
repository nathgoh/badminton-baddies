import type { Court } from '../types'
import { formatCancellationStatus, formatTime } from '../utils'
import Card from './ui/Card'

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
  waitlistCount,
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
    <Card className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
            Session Summary
          </div>
          {summaryValue ? (
            <div className="text-2xl font-semibold text-ink-950">{summaryValue}</div>
          ) : null}
          <div className="text-sm text-ink-700">{cancellationStatus}</div>
        </div>
        <div
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            isFull ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
          }`}
        >
          {isFull ? 'Full' : 'Open'}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3 rounded-[1.5rem] bg-sand-50/80 p-4 text-sm text-ink-700">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-700">
            Confirmed
          </div>
          <div className="mt-1 text-lg font-semibold text-ink-950">{confirmedCount}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-700">
            Capacity
          </div>
          <div className="mt-1 text-lg font-semibold text-ink-950">{totalCapacity}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-700">
            Waitlist
          </div>
          <div className="mt-1 text-lg font-semibold text-ink-950">{waitlistCount}</div>
        </div>
      </div>
      <div className="space-y-3">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Courts</div>
        {courts.map((court) => (
          <div
            key={court.id}
            className="flex flex-col gap-2 rounded-[1.5rem] border border-sand-100 bg-white/80 px-4 py-3 text-sm text-ink-700 sm:flex-row sm:items-center sm:justify-between"
          >
            <span className="font-medium text-ink-950">
              <strong>{court.name}</strong> · {formatTime(court.start_time)} - {formatTime(court.end_time)}
            </span>
            <span className="rounded-full bg-sand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-ink-700">
              {court.max_players} spot{court.max_players === 1 ? '' : 's'}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}
