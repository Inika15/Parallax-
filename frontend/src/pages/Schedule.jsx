import { useState, useEffect, useRef } from 'react'
import { fetchRecommendations } from '../api'
import { Badge } from '../components/Shared'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const HOURS = Array.from({ length: 24 }, (_, i) => i)

export default function Schedule() {
  const [recs, setRecs] = useState([])
  const [dragItem, setDragItem] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)
  const [moveHistory, setMoveHistory] = useState([])
  const [tooltip, setTooltip] = useState(null)
  const tooltipRef = useRef(null)

  useEffect(() => { fetchRecommendations(100).then(setRecs) }, [])

  // Distribute recs across days (round-robin by content_id)
  const getGrid = (data) => {
    const grid = {}
    data.forEach((r, i) => {
      const day = i % 7
      const hour = r.recommended_slot
      const key = `${hour}-${day}`
      if (!grid[key]) grid[key] = []
      grid[key].push({ ...r, _dayIdx: day, _origIdx: i })
    })
    return grid
  }

  const grid = getGrid(recs)
  const activeHours = [...new Set(recs.map(r => r.recommended_slot))].sort((a, b) => a - b)

  const formatHour = h => {
    const ampm = h < 12 ? 'AM' : 'PM'
    const hr = h === 0 ? 12 : h > 12 ? h - 12 : h
    return `${hr} ${ampm}`
  }

  // ─── Drag handlers ──────────────────────────────────────
  const handleDragStart = (e, rec) => {
    setDragItem(rec)
    e.dataTransfer.effectAllowed = 'move'
    e.target.style.opacity = '0.4'
  }

  const handleDragEnd = (e) => {
    e.target.style.opacity = '1'
    setDragItem(null)
    setDropTarget(null)
  }

  const handleDragOver = (e, hour, dayIdx) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDropTarget(`${hour}-${dayIdx}`)
  }

  const handleDragLeave = () => {
    setDropTarget(null)
  }

  const handleDrop = (e, hour, dayIdx) => {
    e.preventDefault()
    setDropTarget(null)

    if (!dragItem) return

    const oldSlot = dragItem.recommended_slot
    const oldDay = dragItem._dayIdx

    if (oldSlot === hour && oldDay === dayIdx) return // no change

    // Calculate score impact (simple estimation)
    const oldScore = dragItem.score
    // Moving away from optimal slot reduces score
    const slotDiff = Math.abs(hour - oldSlot)
    const penalty = slotDiff * 3.5 // ~3.5% per hour away from optimal
    const newScore = Math.max(0, Math.round((oldScore - penalty) * 100) / 100)

    const move = {
      content_id: dragItem.content_id,
      from: { slot: oldSlot, day: DAYS[oldDay] },
      to: { slot: hour, day: DAYS[dayIdx] },
      oldScore,
      newScore,
      scoreDelta: round2(newScore - oldScore),
      timestamp: Date.now(),
    }

    setMoveHistory(prev => [move, ...prev.slice(0, 9)])

    // Update the recommendation
    setRecs(prev => prev.map((r, i) => {
      if (r.content_id === dragItem.content_id && i === dragItem._origIdx) {
        return {
          ...r,
          recommended_slot: hour,
          score: newScore,
          _moved: true,
          _originalSlot: r._originalSlot ?? oldSlot,
        }
      }
      return r
    }))

    setDragItem(null)
  }

  const round2 = n => Math.round(n * 100) / 100

  // Stats
  const igCount = recs.filter(r => r.platform === 'Instagram').length
  const ytCount = recs.filter(r => r.platform === 'YouTube').length
  const movedCount = recs.filter(r => r._moved).length
  const avgScore = recs.length > 0 ? round2(recs.reduce((s, r) => s + r.score, 0) / recs.length) : 0

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <h1>Drag & Drop Calendar</h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            Drag posts between time slots — score updates live
            {movedCount > 0 && <span style={{ color: 'var(--yellow)', marginLeft: 8 }}>• {movedCount} moved</span>}
          </p>
        </div>
        <div className="flex-row" style={{ gap: 16 }}>
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
                const isOver = dropTarget === key
                return (
                  <div
                    key={key}
                    className={`calendar-cell ${isOver ? 'drop-hover' : ''}`}
                    onDragOver={(e) => handleDragOver(e, hour, dayIdx)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, hour, dayIdx)}
                  >
                    {posts.map((p, pi) => (
                      <div
                        key={pi}
                        className={`calendar-chip ${p.platform === 'Instagram' ? 'ig' : 'yt'} ${p._moved ? 'moved' : ''}`}
                        draggable
                        onDragStart={(e) => handleDragStart(e, p)}
                        onDragEnd={handleDragEnd}
                        onMouseEnter={(e) => {
                          const rect = e.target.getBoundingClientRect()
                          setTooltip({
                            ...p, day: DAYS[dayIdx], hour,
                            x: rect.left, y: rect.top - 10,
                          })
                        }}
                        onMouseLeave={() => setTooltip(null)}
                        title={`#${p.content_id} • ${p.score}`}
                      >
                        <span className="chip-id">#{p.content_id}</span>
                      </div>
                    ))}
                  </div>
                )
              })}
            </>
          ))}
        </div>
      </div>

      {/* Floating tooltip */}
      {tooltip && (
        <div className="card animate-fade" style={{
          position: 'fixed', bottom: 24, right: 24,
          maxWidth: 300, zIndex: 100, boxShadow: 'var(--shadow-lg)',
        }}>
          <div className="flex-between" style={{ marginBottom: 8 }}>
            <strong>Content #{tooltip.content_id}</strong>
            <Badge type={tooltip.platform}>{tooltip.platform}</Badge>
          </div>
          <div style={{ fontSize: '0.8rem' }}>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted">Time</span>
              <span>{tooltip.day} {formatHour(tooltip.hour)}</span>
            </div>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted">Score</span>
              <strong style={{ color: tooltip._moved ? 'var(--yellow)' : 'var(--green)' }}>
                {tooltip.score}
                {tooltip._moved && <span style={{ fontSize: '0.7rem', opacity: 0.7 }}> (was {tooltip._originalSlot}h)</span>}
              </strong>
            </div>
            <div className="flex-between" style={{ marginBottom: 4 }}>
              <span className="text-muted">Decision</span>
              <Badge type={tooltip.decision}>{tooltip.decision === 'SCHEDULE' ? 'Schedule' : 'Post Now'}</Badge>
            </div>
            {tooltip.explanation?.natural_language && (
              <div style={{ marginTop: 8, padding: '8px 10px', background: 'rgba(255,255,255,0.03)',
                borderRadius: 6, fontSize: '0.75rem', color: '#999', lineHeight: 1.5 }}>
                💡 {tooltip.explanation.natural_language.slice(0, 150)}...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Move history + Stats */}
      <div className="grid-2" style={{ marginTop: 20 }}>
        {/* Stats */}
        <div className="card">
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em',
            color: '#888', marginBottom: 12 }}>Calendar Stats</div>
          <div className="grid-2">
            <div style={{ textAlign: 'center' }}>
              <div className="stat-value">{recs.filter(r => r.decision === 'SCHEDULE').length}</div>
              <div className="stat-sub">Scheduled</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="stat-value">{recs.filter(r => r.decision === 'POST_NOW').length}</div>
              <div className="stat-sub">Post Now</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="stat-value">{activeHours.length}</div>
              <div className="stat-sub">Time Slots</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="stat-value" style={{ color: avgScore > 80 ? 'var(--green)' : 'var(--yellow)' }}>
                {avgScore}
              </div>
              <div className="stat-sub">Avg Score</div>
            </div>
          </div>
        </div>

        {/* Move history */}
        <div className="card">
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em',
            color: '#888', marginBottom: 12 }}>
            Move History {moveHistory.length > 0 && `(${moveHistory.length})`}
          </div>
          {moveHistory.length === 0 ? (
            <div style={{ color: '#555', fontSize: '0.8rem', textAlign: 'center', padding: '20px 0' }}>
              ✋ Drag a post chip to another slot to reschedule
            </div>
          ) : (
            <div style={{ maxHeight: 180, overflowY: 'auto' }}>
              {moveHistory.map((m, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
                  fontSize: '0.78rem',
                }}>
                  <span>
                    #{m.content_id} → {formatHour(m.to.slot)} {m.to.day}
                  </span>
                  <span style={{
                    color: m.scoreDelta >= 0 ? 'var(--green)' : 'var(--red)',
                    fontWeight: 600,
                  }}>
                    {m.scoreDelta >= 0 ? '+' : ''}{m.scoreDelta}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
