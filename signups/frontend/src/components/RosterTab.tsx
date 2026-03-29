import type { Signup } from '../types'

interface Props {
  signups: Signup[]
}

export default function RosterTab({ signups }: Props) {
  const confirmed = signups.filter((signup) => signup.status === 'confirmed')
  const waitlisted = signups.filter((signup) => signup.status === 'waitlist')

  return (
    <div>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#137333',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 8,
        }}
      >
        Confirmed - {confirmed.length}
      </div>
      <div
        style={{
          border: '1px solid #e0e0e0',
          borderRadius: 6,
          overflow: 'hidden',
          marginBottom: 20,
        }}
      >
        {confirmed.map((signup, index) => (
          <div
            key={signup.id}
            style={{
              padding: '10px 14px',
              borderBottom: '1px solid #f5f5f5',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: '#e8eaf6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                fontWeight: 600,
                color: '#3f51b5',
                flexShrink: 0,
              }}
            >
              {index + 1}
            </div>
            <span>{signup.name}</span>
          </div>
        ))}
        {confirmed.length === 0 ? (
          <div style={{ padding: '16px 14px', color: '#aaa', textAlign: 'center', fontSize: 13 }}>
            No confirmed players yet
          </div>
        ) : null}
      </div>
      {waitlisted.length > 0 ? (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: '#e65100',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            Waitlist - {waitlisted.length}
          </div>
          <div style={{ border: '1px solid #ffe0b2', borderRadius: 6, overflow: 'hidden' }}>
            {waitlisted.map((signup, index) => (
              <div
                key={signup.id}
                style={{
                  padding: '10px 14px',
                  borderBottom: '1px solid #fff3e0',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                }}
              >
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: '#fff3e0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 10,
                    fontWeight: 600,
                    color: '#e65100',
                    flexShrink: 0,
                  }}
                >
                  W{index + 1}
                </div>
                <span>{signup.name}</span>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}

