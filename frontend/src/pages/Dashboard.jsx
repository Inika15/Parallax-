import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchStats, fetchRecommendations, fetchHeatmap } from '../api'
import { Badge, StatCard, ScoreBar } from '../components/Shared'

// ── Mini SVG Line Chart Component ─────────────────────────
function LineChart({ data, labels, width = 500, height = 160, color = '#1a7a3a' }) {
  if (!data || data.length === 0) return null
  const padding = { top: 20, right: 16, bottom: 28, left: 40 }
  const w = width - padding.left - padding.right
  const h = height - padding.top - padding.bottom
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1

  const points = data.map((v, i) => ({
    x: padding.left + (i / (data.length - 1)) * w,
    y: padding.top + h - ((v - min) / range) * h,
  }))

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
  const areaD = pathD + ` L ${points[points.length - 1].x} ${padding.top + h} L ${points[0].x} ${padding.top + h} Z`

  // Y axis ticks
  const yTicks = [min, min + range * 0.5, max].map(v => ({
    value: v.toFixed(1),
    y: padding.top + h - ((v - min) / range) * h,
  }))

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      {/* Grid lines */}
      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={padding.left} y1={t.y} x2={width - padding.right} y2={t.y}
            stroke="var(--border)" strokeDasharray="3,3" />
          <text x={padding.left - 6} y={t.y + 4} textAnchor="end"
            fontSize="9" fill="var(--text-hint)" fontFamily="var(--font)">{t.value}</text>
        </g>
      ))}
      {/* Area fill */}
      <path d={areaD} fill={`${color}15`} />
      {/* Line */}
      <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* Dots */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3" fill="white" stroke={color} strokeWidth="1.5" />
          {/* X label */}
          {(i % Math.ceil(data.length / 8) === 0 || i === data.length - 1) && (
            <text x={p.x} y={padding.top + h + 16} textAnchor="middle"
              fontSize="8" fill="var(--text-hint)" fontFamily="var(--font)">
              {labels ? labels[i] : i}
            </text>
          )}
        </g>
      ))}
    </svg>
  )
}

// ── Mini SVG Pie Chart Component ──────────────────────────
function PieChart({ slices, size = 140 }) {
  if (!slices || slices.length === 0) return null
  const cx = size / 2, cy = size / 2, r = size / 2 - 8
  const total = slices.reduce((s, sl) => s + sl.value, 0) || 1

  let cumAngle = -Math.PI / 2
  const paths = slices.map((sl, i) => {
    const angle = (sl.value / total) * 2 * Math.PI
    const x1 = cx + r * Math.cos(cumAngle)
    const y1 = cy + r * Math.sin(cumAngle)
    cumAngle += angle
    const x2 = cx + r * Math.cos(cumAngle)
    const y2 = cy + r * Math.sin(cumAngle)
    const largeArc = angle > Math.PI ? 1 : 0
    const midAngle = cumAngle - angle / 2
    const labelR = r * 0.65
    const lx = cx + labelR * Math.cos(midAngle)
    const ly = cy + labelR * Math.sin(midAngle)
    return { d: `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`, ...sl, lx, ly, pct: ((sl.value / total) * 100).toFixed(0) }
  })

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width={size} height={size}>
        {paths.map((p, i) => (
          <g key={i}>
            <path d={p.d} fill={p.color} stroke="white" strokeWidth="2" />
            {p.value > 0 && (
              <text x={p.lx} y={p.ly + 3} textAnchor="middle" fontSize="10"
                fill="white" fontWeight="600" fontFamily="var(--font)">{p.pct}%</text>
            )}
          </g>
        ))}
      </svg>
      <div style={{ fontSize: '0.75rem' }}>
        {slices.map((sl, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: sl.color }} />
            <span>{sl.label}: <strong>{sl.value}</strong></span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Loading Skeleton ──────────────────────────────────────
function LoadingSkeleton() {
  return (
    <div className="page" style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: '1.5rem', color: 'var(--text-hint)', animation: 'pulse 1.5s infinite' }}>
        ⏳ Loading dashboard data...
      </div>
      <p className="text-muted" style={{ marginTop: 12, fontSize: '0.85rem' }}>
        Connecting to PostOptima API on localhost:8000
      </p>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recs, setRecs] = useState([])
  const [heatmap, setHeatmap] = useState(null)
  const [hoveredCell, setHoveredCell] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const profile = JSON.parse(localStorage.getItem('postoptima_profile') || '{}')

  useEffect(() => {
    Promise.all([
      fetchStats().then(setStats),
      fetchRecommendations(20).then(r => setRecs(r || [])),
      fetchHeatmap().then(setHeatmap),
    ]).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton />

  const greeting = profile.experience === 'beginner' ? 'Welcome aboard! 🌱'
    : profile.experience === 'growing' ? 'Let\'s grow together 📈'
    : profile.experience === 'professional' ? 'Welcome back, Pro 🏆'
    : 'Welcome to PostOptima'

  // ── Chart Data ────────────────────────────────────────
  // Score distribution for line chart (sorted recs by content_id)
  const sortedRecs = [...recs].sort((a, b) => parseInt(a.content_id) - parseInt(b.content_id))
  const scoreData = sortedRecs.map(r => r.score)
  const scoreLabels = sortedRecs.map(r => `#${r.content_id}`)

  // Platform distribution for pie chart
  const platformCounts = {}
  recs.forEach(r => { platformCounts[r.platform] = (platformCounts[r.platform] || 0) + 1 })
  const platformSlices = [
    { label: 'Instagram', value: platformCounts['Instagram'] || 0, color: '#6b2178' },
    { label: 'YouTube', value: platformCounts['YouTube'] || 0, color: '#8b1a1a' },
  ]

  // Decision distribution for pie chart
  const decisionCounts = {}
  recs.forEach(r => { decisionCounts[r.decision] = (decisionCounts[r.decision] || 0) + 1 })
  const decisionSlices = [
    { label: 'Post Now', value: decisionCounts['POST_NOW'] || 0, color: '#1a7a3a' },
    { label: 'Schedule', value: decisionCounts['SCHEDULE'] || 0, color: '#7a5a00' },
  ]

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

      {/* ── Charts Row: Line Graph + Pie Charts ─────────── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* Score Trend Line Chart */}
        <div className="card" style={{ animationDelay: '0.05s' }}>
          <div className="card-header">
            <h3>Score Distribution</h3>
            <span className="text-xs">Optimization scores across content items</span>
          </div>
          <LineChart
            data={scoreData}
            labels={scoreLabels}
            width={520}
            height={180}
            color="#1a7a3a"
          />
        </div>

        {/* Pie Charts: Platform + Decision */}
        <div className="card" style={{ animationDelay: '0.1s' }}>
          <div className="card-header">
            <h3>Distribution Overview</h3>
            <span className="text-xs">Platform & scheduling breakdown</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'center' }}>
            <div>
              <div className="text-xs" style={{ marginBottom: 8 }}>Platform Split</div>
              <PieChart slices={platformSlices} size={120} />
            </div>
            <div>
              <div className="text-xs" style={{ marginBottom: 8 }}>Decision Split</div>
              <PieChart slices={decisionSlices} size={120} />
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Recommendations Table */}
        <div className="card" style={{ animationDelay: '0.15s' }}>
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

        {/* Heatmap — now using teal gradient for consistency */}
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
                        style={{ background: `rgba(15, 110, 86, ${opacity})` }}
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
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: '0.6rem', color: 'var(--text-hint)' }}>
                <span>Off-peak (0.6)</span>
                <span>Peak (1.0)</span>
              </div>
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
