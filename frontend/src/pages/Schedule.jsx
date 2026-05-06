import { useState, useEffect } from 'react'
import { fetchRecommendations } from '../api'
import { Badge } from '../components/Shared'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function Schedule() {
  const [recs, setRecs] = useState([])
  const [hovered, setHovered] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchRecommendations(100).then(r => { setRecs(r || []); setLoading(false) }) }, [])

  // Distribute recs across days (round-robin by content_id)
  const grid = {}
  recs.forEach((r, i) => {
    const day = i % 7
    const hour = r.recommended_slot
    const key = `${hour}-${day}`
    if (!grid[key]) grid[key] = []
    grid[key].push(r)
  })

  // Find hours that have posts
  const activeHours = [...new Set(recs.map(r => r.recommended_slot))].sort((a, b) => a - b)

  const formatHour = h => {
    const ampm = h < 12 ? 'AM' : 'PM'
    const hr = h === 0 ? 12 : h > 12 ? h - 12 : h
    return `${hr} ${ampm}`
  }

  const igCount = recs.filter(r => r.platform === 'Instagram').length
  const ytCount = recs.filter(r => r.platform === 'YouTube').length

  if (loading) return (
    <div className="page" style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: '1.5rem', color: 'var(--text-hint)', animation: 'pulse 1.5s infinite' }}>⏳ Loading schedule...</div>
    </div>
  )

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <h1>Batch Schedule</h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            Weekly posting calendar — {recs.length} posts spread across optimal time slots
          </p>
        </div>
        <div className="flex-row">
          <div className="flex-row" style={{ gap: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--purple)' }} />
            <span style={{ fontSize: '0.75rem' }}>Instagram ({igCount})</span>
          </div>
          <div className="flex-row" style={{ gap: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--red)' }} />
            <span style={{ fontSize: '0.75rem' }}>YouTube ({ytCount})</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="calendar-grid">
          {/* Header row */}
          <div className="calendar-header" />
          {DAYS.map(d => <div key={d} className="calendar-header">{d}</div>)}

          {/* Hour rows */}
          {activeHours.map(hour => (
            <>
              <div key={`h-${hour}`} className="calendar-hour">{formatHour(hour)}</div>
              {DAYS.map((_, dayIdx) => {
                const key = `${hour}-${dayIdx}`
                const posts = grid[key] || []
                return (
                  <div key={key} className="calendar-cell">
                    {posts.map((p, pi) => (
                      <div
                        key={pi}
                        className={`calendar-dot ${p.platform === 'Instagram' ? 'ig' : 'yt'}`}
                        onMouseEnter={() => setHovered({ ...p, day: DAYS[dayIdx], hour })}
                        onMouseLeave={() => setHovered(null)}
                      />
                    ))}
                  </div>
                )
              })}
            </>
          ))}
        </div>
      </div>

      {/* Hover details */}
      {hovered && (
        <div className="card animate-fade" style={{
          position: 'fixed', bottom: 24, right: 24,
          maxWidth: 280, zIndex: 100, boxShadow: 'var(--shadow-lg)',
        }}>
          <div className="flex-between" style={{ marginBottom: 8 }}>
            <strong>Content #{hovered.content_id}</strong>
            <Badge type={hovered.platform}>{hovered.platform}</Badge>
          </div>
          <div style={{ fontSize: '0.8rem' }}>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted">Time</span>
              <span>{hovered.day} {formatHour(hovered.hour)}</span>
            </div>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted">Decision</span>
              <Badge type={hovered.decision}>{hovered.decision === 'SCHEDULE' ? 'Schedule' : 'Post Now'}</Badge>
            </div>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted">Score</span>
              <strong>{hovered.score}</strong>
            </div>
            <div className="flex-between">
              <span className="text-muted">Content Type</span>
              <span>{hovered.content_type}</span>
            </div>
          </div>
        </div>
      )}

      {/* Summary stats */}
      <div className="grid-3" style={{ marginTop: 20 }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-label">Schedule Decisions</div>
          <div className="stat-value">{recs.filter(r => r.decision === 'SCHEDULE').length}</div>
          <div className="stat-sub">Posts optimally timed</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-label">Post Now Decisions</div>
          <div className="stat-value">{recs.filter(r => r.decision === 'POST_NOW').length}</div>
          <div className="stat-sub">Already at good times</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-label">Peak Hours</div>
          <div className="stat-value">{activeHours.length}</div>
          <div className="stat-sub">Unique time slots used</div>
        </div>
      </div>
    </div>
  )
}
