import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { fetchCreator, fetchCreatorHeatmap, fetchCounterfactual } from '../api'
import { Badge, ScoreBar, PipelineFlow } from '../components/Shared'

export default function CreatorProfile() {
  const { id } = useParams()
  const [creator, setCreator] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [selectedType, setSelectedType] = useState('SHORT')
  const [cf, setCf] = useState(null)

  useEffect(() => {
    fetchCreator(id).then(setCreator)
    fetchCreatorHeatmap(id, 'SHORT').then(setHeatmap)
  }, [id])

  useEffect(() => {
    fetchCreatorHeatmap(id, selectedType).then(setHeatmap)
  }, [id, selectedType])

  // Load counterfactual for first recommendation
  useEffect(() => {
    if (creator?.recommendations?.[0]) {
      fetchCounterfactual(creator.recommendations[0].content_id).then(setCf)
    }
  }, [creator])

  if (!creator) return <div className="page"><p>Loading...</p></div>

  return (
    <div className="page">
      <div className="grid-2" style={{ gridTemplateColumns: '340px 1fr' }}>
        {/* Left: Creator Card */}
        <div>
          <div className="card">
            <div className="flex-row" style={{ marginBottom: 16 }}>
              <div style={{
                width: 48, height: 48, borderRadius: '50%',
                background: 'var(--accent)', color: 'white',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '1.1rem', fontWeight: 700,
              }}>
                {creator.creator_id}
              </div>
              <div>
                <h2>Creator #{creator.creator_id}</h2>
                <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                  Base: {creator.base_engagement}x · Cooldown: {creator.cooldown_hours}h
                </span>
              </div>
            </div>

            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
              <div className="stat-card" style={{ padding: '10px 12px' }}>
                <div className="stat-label">Posts</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{creator.recommendations?.length || 0}</div>
              </div>
              <div className="stat-card" style={{ padding: '10px 12px' }}>
                <div className="stat-label">Avg Score</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                  {creator.recommendations?.length ?
                    (creator.recommendations.reduce((s, r) => s + r.score, 0) / creator.recommendations.length).toFixed(1)
                    : '—'}
                </div>
              </div>
            </div>

            {/* Platform Affinity */}
            <h3 style={{ fontSize: '0.85rem', marginBottom: 8 }}>Platform Affinity</h3>
            {Object.entries(creator.platform_affinity || {}).map(([p, v]) => (
              <div key={p} className="flex-between" style={{ marginBottom: 6, fontSize: '0.8rem' }}>
                <Badge type={p}>{p}</Badge>
                <strong style={{ color: v > 1 ? 'var(--green)' : v < 1 ? 'var(--red)' : 'inherit' }}>
                  {v.toFixed(2)}x
                </strong>
              </div>
            ))}

            {/* Trajectory */}
            <h3 style={{ fontSize: '0.85rem', marginTop: 16, marginBottom: 8 }}>30-Day Trajectory</h3>
            {Object.entries(creator.trajectory || {}).map(([p, t]) => (
              <div key={p} className="flex-between" style={{ marginBottom: 6, fontSize: '0.8rem' }}>
                <span>{p}</span>
                <span style={{
                  color: t > 1 ? 'var(--green)' : t < 1 ? 'var(--red)' : 'var(--text-muted)',
                  fontWeight: 600,
                }}>
                  {t > 1 ? '↑ Trending Up' : t < 1 ? '↓ Trending Down' : '→ Stable'}
                  ({((t - 1) * 100).toFixed(1)}%)
                </span>
              </div>
            ))}

            {/* Data Richness */}
            <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-surface)', borderRadius: 'var(--radius)' }}>
              <div className="flex-between" style={{ marginBottom: 6 }}>
                <span className="text-xs">Data Richness</span>
                <strong>{(creator.data_richness * 100).toFixed(0)}%</strong>
              </div>
              <div className="score-bar" style={{ height: 6 }}>
                <div className="score-bar-fill" style={{
                  width: `${creator.data_richness * 100}%`,
                  background: creator.data_richness >= 0.7 ? 'var(--green)' : 'var(--amber)',
                }} />
              </div>
              {creator.is_cold_start && (
                <div style={{ marginTop: 8 }}>
                  <Badge type="cold">Cold-start mode — using global averages</Badge>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Analysis */}
        <div>
          {/* Counterfactual */}
          {cf && (
            <div className="card animate-in" style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 16 }}>Counterfactual Analysis</h3>
              <div className="grid-3" style={{ marginBottom: 16 }}>
                <div style={{ textAlign: 'center', padding: 12, background: 'var(--green-bg)', borderRadius: 'var(--radius)' }}>
                  <div className="text-xs">Optimal</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--green)' }}>{cf.optimal.score}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{cf.optimal.platform} @ {cf.optimal.slot}:00</div>
                </div>
                <div style={{ textAlign: 'center', padding: 12, background: 'var(--bg-surface)', borderRadius: 'var(--radius)' }}>
                  <div className="text-xs">Random Baseline</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{cf.random_baseline}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Average across all slots</div>
                </div>
                <div style={{ textAlign: 'center', padding: 12, background: 'var(--red-bg)', borderRadius: 'var(--radius)' }}>
                  <div className="text-xs">Worst Possible</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--red)' }}>{cf.worst.score}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{cf.worst.platform} @ {cf.worst.slot}:00</div>
                </div>
              </div>
              <div style={{ textAlign: 'center', padding: 12, border: '2px solid var(--green-border)', borderRadius: 'var(--radius)', background: 'var(--green-bg)' }}>
                <span className="text-xs">Value of PostOptima</span>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--green)' }}>
                  +{cf.optimizer_value} points (+{cf.improvement_pct}% vs worst)
                </div>
              </div>
            </div>
          )}

          {/* Engagement Heatmap */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="flex-between" style={{ marginBottom: 12 }}>
              <h3>Engagement Heatmap</h3>
              <select className="form-select" style={{ width: 160 }} value={selectedType}
                onChange={e => setSelectedType(e.target.value)}>
                <option value="SHORT">Short Form</option>
                <option value="LONG">Long Form</option>
              </select>
            </div>
            {heatmap && (
              <div className="heatmap">
                <div className="heatmap-hours">
                  <div />
                  {Array.from({ length: 24 }, (_, i) => <div key={i} className="heatmap-hour">{i}</div>)}
                </div>
                {Object.entries(heatmap).map(([platform, slots]) => {
                  const maxS = Math.max(...slots.map(s => s.score))
                  return (
                    <div key={platform} className="heatmap-row">
                      <div className="heatmap-label">{platform}</div>
                      {slots.map((s, i) => (
                        <div key={i} className="heatmap-cell"
                          style={{ background: `rgba(26,26,26, ${maxS > 0 ? (s.score / maxS) * 0.9 : 0.05})` }}
                          title={`${platform} ${s.hour}:00 — Score: ${s.score}`}
                        />
                      ))}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Pipeline Flow */}
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Scheduling Pipeline</h3>
            <PipelineFlow activeStep={5} />
          </div>

          {/* Recommendations */}
          {creator.recommendations?.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 12 }}>Recommendation History</h3>
              <table>
                <thead><tr><th>Content</th><th>Platform</th><th>Slot</th><th>Decision</th><th>Score</th></tr></thead>
                <tbody>
                  {creator.recommendations.map(r => (
                    <tr key={r.content_id}>
                      <td>#{r.content_id}</td>
                      <td><Badge type={r.platform}>{r.platform}</Badge></td>
                      <td>{r.recommended_slot}:00</td>
                      <td><Badge type={r.decision}>{r.decision === 'SCHEDULE' ? 'Schedule' : 'Post Now'}</Badge></td>
                      <td><ScoreBar score={r.score} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
