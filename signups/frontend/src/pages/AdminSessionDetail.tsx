import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import CostCalculator from '../components/CostCalculator'
import RosterManager from '../components/RosterManager'
import { getAdminSession } from '../api/client'
import type { AdminSessionResponse } from '../types'
import { useMobile } from '../hooks/useMobile'

export default function AdminSessionDetail() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<AdminSessionResponse | null>(null)
  const navigate = useNavigate()
  const isMobile = useMobile()

  async function load() {
    if (!id) {
      return
    }
    setData(await getAdminSession(id))
  }

  useEffect(() => {
    void load()
  }, [id])

  if (!data) {
    return <div style={{ textAlign: 'center', marginTop: 60 }}>Loading...</div>
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24, fontFamily: 'sans-serif' }}>
      <button
        onClick={() => navigate('/admin')}
        style={{
          fontSize: 12,
          color: '#3f51b5',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          marginBottom: 16,
        }}
      >
        ← Back to sessions
      </button>
      <h2 style={{ margin: '0 0 20px' }}>{data.session.name}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 24 }}>
        <CostCalculator data={data} onRefresh={() => void load()} />
        <RosterManager signups={data.signups} onRefresh={() => void load()} />
      </div>
    </div>
  )
}

