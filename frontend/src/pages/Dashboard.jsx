import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchStats, fetchRecommendations, fetchHeatmap } from '../api'
import { Badge, StatCard, ScoreBar } from '../components/Shared'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recs, setRecs] = useState([])
  const [heatmap, setHeatmap] = useState(null)
  const [hoveredCell, setHoveredCell] = useState(null)
  const navigate = useNavigate()
  const profile = JSON.parse(localStorage.getItem('postoptima_profile') || '{}')

  useEffect(() => {
    fetchStats().then(setStats)
    fetchRecommendations(20).then(setRecs)
    fetchHeatmap().then(setHeatmap)
  }, [])

  const greeting = profile.experience === 'beginner' ? 'Welcome aboard! 🌱'
    : profile.experience === 'growing' ? 'Let\'s grow together 📈'
    : profile.experience === 'professional' ? 'Welcome back, Pro 🏆'
    : 'Welcome to PostOptima'

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <h1>{greeting}</h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>Your content optimization command center</p>
        </div>
      </div>

      {/* Stat Cards */}
      {stats && (
        <div className="grid-4" style={{ marginBottom: 24 }}>
          <StatCard label="Total Posts" value={stats.total_posts} sub="Analyzed" />
          <StatCard label="Avg Lift" value={`+${stats.avg_lift}%`} sub="vs. posting randomly" positive />
          <StatCard label="Scheduled" value={stats.scheduled} sub={`${stats.post_now} posted now`} />
          <StatCard label="Creators" value={stats.total_creators} sub={`Avg score: ${stats.avg_score}`} />
        </div>
      )}

      <div className="grid-2">
        {/* Recommendations Table */}
        <div className="card" style={{ animationDelay: '0.1s' }}>
          <div className="card-header flex-between">
            <h3>Recent Recommendations</h3>
            <span className="text-xs">{recs.length} items</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Platform</th>
                  <th>Slot</th>
                  <th>Decision</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {recs.map((r, i) => (
                  <tr key={r.content_id}
                      style={{ animationDelay: `${i * 0.05}s`, cursor: 'pointer' }}
                      className="animate-in"
                      onClick={() => navigate(`/optimize?id=${r.content_id}`)}>
                    <td style={{ fontWeight: 600 }}>#{r.content_id}</td>
                    <td><Badge type={r.platform}>{r.platform}</Badge></td>
                    <td>{r.recommended_slot}:00</td>
                    <td><Badge type={r.decision}>{r.decision === 'SCHEDULE' ? 'Schedule' : 'Post Now'}</Badge></td>
                    <td><ScoreBar score={r.score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Heatmap */}
        <div className="card" style={{ animationDelay: '0.2s' }}>
          <div className="card-header">
            <h3>Platform Activity Heatmap</h3>
            <span className="text-xs">24h × 2 Platforms</span>
          </div>
          {heatmap && (
            <div className="heatmap">
              <div className="heatmap-hours">
                <div />
                {Array.from({ length: 24 }, (_, i) => (
                  <div key={i} className="heatmap-hour">{i}</div>
                ))}
              </div>
              {Object.entries(heatmap).map(([platform, slots]) => (
                <div key={platform} className="heatmap-row">
                  <div className="heatmap-label">{platform}</div>
                  {slots.map((s, i) => {
                    const opacity = Math.max(0.08, s.activity)
                    return (
                      <div
                        key={i}
                        className="heatmap-cell"
                        style={{ background: `rgba(26,26,26, ${opacity})` }}
                        onMouseEnter={() => setHoveredCell({ platform, hour: s.hour, score: s.activity })}
                        onMouseLeave={() => setHoveredCell(null)}
                      >
                        {hoveredCell?.platform === platform && hoveredCell?.hour === s.hour && (
                          <div className="tooltip">{platform} {s.hour}:00 — {s.activity}</div>
                        )}
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Eval Metrics */}
      {stats?.metrics && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card-header"><h3>Evaluation Metrics</h3></div>
          <div className="grid-4">
            {Object.entries(stats.metrics).map(([key, val]) => (
              <div key={key} style={{ textAlign: 'center', padding: '8px 0' }}>
                <div className="stat-label">{key.replace(/_/g, ' ')}</div>
                <div className="stat-value">{(val * 100).toFixed(1)}%</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
