import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { runOptimizer, fetchCreators } from '../api'
import { Badge, ScoreBar, PipelineFlow } from '../components/Shared'

export default function Optimize() {
  const [searchParams] = useSearchParams()
  const [creators, setCreators] = useState([])
  const [form, setForm] = useState({
    creator_id: searchParams.get('creator') || '1',
    content_type: 'SHORT',
    submission_hour: 12,
    time_sensitivity: 'Medium',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showCandidates, setShowCandidates] = useState(false)

  useEffect(() => { fetchCreators().then(setCreators) }, [])

  const hours = Array.from({ length: 24 }, (_, i) => {
    const ampm = i < 12 ? 'AM' : 'PM'
    const h = i === 0 ? 12 : i > 12 ? i - 12 : i
    return { value: i, label: `${h} ${ampm}` }
  })

  const run = async () => {
    setLoading(true)
    setResult(null)
    setShowCandidates(false)
    const data = await runOptimizer(form)
    setResult(data)
    setLoading(false)
    setTimeout(() => setShowCandidates(true), 300)
  }

  return (
    <div className="page">
      <h1 style={{ marginBottom: 4 }}>Optimize Content</h1>
      <p className="text-muted" style={{ marginBottom: 24, fontSize: '0.85rem' }}>
        Submit content → watch the optimizer score all 48 platform×slot combinations → see the winner.
      </p>

      <PipelineFlow activeStep={loading ? 2 : result ? 5 : 0} />

      <div className="grid-2" style={{ marginTop: 20, gridTemplateColumns: '340px 1fr' }}>
        {/* Left: Form */}
        <div>
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Submission</h3>
            <div className="form-group">
              <label className="form-label">Creator</label>
              <select className="form-select" value={form.creator_id}
                onChange={e => setForm(f => ({ ...f, creator_id: e.target.value }))}>
                {creators.map(c => (
                  <option key={c.creator_id} value={c.creator_id}>
                    Creator #{c.creator_id} (base: {c.base_engagement})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Content Type</label>
              <select className="form-select" value={form.content_type}
                onChange={e => setForm(f => ({ ...f, content_type: e.target.value }))}>
                <option value="SHORT">Short Form (Reels, Shorts)</option>
                <option value="LONG">Long Form (Videos, Vlogs)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Submission Hour: {hours[form.submission_hour].label}</label>
              <input type="range" min="0" max="23" value={form.submission_hour}
                onChange={e => setForm(f => ({ ...f, submission_hour: parseInt(e.target.value) }))}
                style={{ width: '100%' }} />
            </div>
            <div className="form-group">
              <label className="form-label">Time Sensitivity</label>
              <select className="form-select" value={form.time_sensitivity}
                onChange={e => setForm(f => ({ ...f, time_sensitivity: e.target.value }))}>
                <option value="High">High — post soon</option>
                <option value="Medium">Medium — flexible</option>
                <option value="Low">Low — no rush</option>
              </select>
            </div>
            <button className="btn" style={{ width: '100%' }} onClick={run} disabled={loading}>
              {loading ? 'Optimizing...' : 'Run Optimizer →'}
            </button>
          </div>

          {/* Creator DNA */}
          {result?.creator_dna && (
            <div className="card animate-in" style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 12 }}>Creator DNA</h3>
              <div style={{ fontSize: '0.8rem' }}>
                <div className="flex-between" style={{ marginBottom: 6 }}>
                  <span className="text-muted">Base Multiplier</span>
                  <strong>{result.creator_dna.base_multiplier}</strong>
                </div>
                {Object.entries(result.creator_dna.platform_affinity || {}).map(([p, v]) => (
                  <div key={p} className="flex-between" style={{ marginBottom: 6 }}>
                    <span className="text-muted">{p} Affinity</span>
                    <strong style={{ color: v > 1 ? 'var(--green)' : v < 1 ? 'var(--red)' : 'inherit' }}>
                      {v.toFixed(2)}x
                    </strong>
                  </div>
                ))}
                <div className="flex-between" style={{ marginBottom: 6 }}>
                  <span className="text-muted">Data Richness</span>
                  <strong>{(result.creator_dna.data_richness * 100).toFixed(0)}%</strong>
                </div>
                {result.creator_dna.is_cold_start && (
                  <Badge type="cold">Cold-Start Mode</Badge>
                )}
                {/* Trajectory */}
                {result.creator_dna.trajectory && Object.entries(result.creator_dna.trajectory).map(([p, t]) => (
                  <div key={p} className="flex-between" style={{ marginTop: 6 }}>
                    <span className="text-muted">{p} Trend</span>
                    <span style={{ color: t > 1 ? 'var(--green)' : t < 1 ? 'var(--red)' : 'var(--text-muted)' }}>
                      {t > 1 ? '↑' : t < 1 ? '↓' : '→'} {((t - 1) * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Results */}
        <div>
          {result && (
            <>
              {/* Best Recommendation */}
              <div className="card animate-in" style={{ borderColor: 'var(--green-border)', borderWidth: 2 }}>
                <div className="flex-between" style={{ marginBottom: 12 }}>
                  <div>
                    <span className="text-xs">Best Recommendation</span>
                    <h2>{result.best.platform} at {result.best.recommended_slot}:00</h2>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 700 }}>{result.best.score}</div>
                    <Badge type={result.best.decision}>
                      {result.best.decision === 'SCHEDULE' ? 'Schedule' : 'Post Now'}
                    </Badge>
                  </div>
                </div>
                <div className="flex-row" style={{ gap: 16 }}>
                  <Badge type={result.best.confidence}>{result.best.confidence} Confidence</Badge>
                  {result.lift_percent > 0 && (
                    <span style={{ color: 'var(--green)', fontWeight: 600, fontSize: '0.85rem' }}>
                      +{result.lift_percent}% vs. posting now
                    </span>
                  )}
                </div>
              </div>

              {/* Score Breakdown */}
              <div className="card animate-slide" style={{ marginTop: 16, animationDelay: '0.15s' }}>
                <h3 style={{ marginBottom: 12 }}>Score Breakdown</h3>
                <table>
                  <thead>
                    <tr><th>Factor</th><th>Raw Value</th><th>Weight</th><th>Contribution</th></tr>
                  </thead>
                  <tbody>
                    {[
                      { name: 'Platform Activity', raw: result.best.breakdown.platform_activity_raw, w: '30%', contrib: result.best.breakdown.w_platform_contribution },
                      { name: 'Creator History', raw: result.best.breakdown.creator_history_raw, w: '40%', contrib: result.best.breakdown.w_history_contribution },
                      { name: 'Base Engagement', raw: result.best.breakdown.creator_base_raw, w: '15%', contrib: result.best.breakdown.w_base_contribution },
                      { name: 'Content-Type Fit', raw: result.best.breakdown.content_fit_raw, w: '15%', contrib: result.best.breakdown.w_fit_contribution },
                    ].map((row, i) => (
                      <tr key={i}>
                        <td>{row.name}</td>
                        <td>{row.raw?.toFixed(3)}</td>
                        <td>{row.w}</td>
                        <td style={{ fontWeight: 600 }}>{row.contrib?.toFixed(1)}</td>
                      </tr>
                    ))}
                    <tr style={{ fontWeight: 700, borderTop: '2px solid var(--border)' }}>
                      <td>Total</td><td /><td /><td>{result.best.score}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* All 48 Candidates */}
              {showCandidates && (
                <div className="card" style={{ marginTop: 16, maxHeight: 400, overflow: 'auto' }}>
                  <div className="card-header flex-between">
                    <h3>All 48 Candidates</h3>
                    <span className="text-xs">Ranked by score</span>
                  </div>
                  <table>
                    <thead>
                      <tr><th>#</th><th>Platform</th><th>Slot</th><th>Score</th></tr>
                    </thead>
                    <tbody>
                      {result.candidates.map((c, i) => (
                        <tr key={i} className="animate-in" style={{ animationDelay: `${i * 0.03}s` }}>
                          <td>{c.rank === 1 ? '★' : c.rank}</td>
                          <td><Badge type={c.platform}>{c.platform}</Badge></td>
                          <td>{c.slot}:00</td>
                          <td><ScoreBar score={c.score} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {!result && !loading && (
            <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--text-hint)' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>⚡</div>
              <p>Configure your submission and hit <strong>Run Optimizer</strong></p>
              <p style={{ fontSize: '0.8rem', marginTop: 8 }}>
                The engine will evaluate all 48 platform × time slot combinations
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
