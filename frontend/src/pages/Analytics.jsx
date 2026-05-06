import { useState, useEffect } from 'react'
import { fetchCreators, fetchAnalyticsScorecard, fetchAnalyticsHeatmap, fetchAnalyticsPlatformBreakdown, fetchAnalyticsContentHistory, fetchAnalyticsTimingAudit, fetchAnalyticsOptimizerImpact } from '../api'
import { Badge, ScoreBar, StatCard } from '../components/Shared'

export default function Analytics() {
  const [creators, setCreators] = useState([])
  const [selectedCreator, setSelectedCreator] = useState(null)
  const [scorecard, setScorecard] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [breakdown, setBreakdown] = useState(null)
  const [contentHistory, setContentHistory] = useState([])
  const [timingAudit, setTimingAudit] = useState(null)
  const [impact, setImpact] = useState(null)
  const [sortField, setSortField] = useState('score')
  const [sortDir, setSortDir] = useState('desc')

  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchCreators().then(c => { setCreators(c || []); if (c?.length) setSelectedCreator(c[0].creator_id); setLoading(false) }) }, [])

  useEffect(() => {
    if (!selectedCreator) return
    fetchAnalyticsScorecard(selectedCreator).then(setScorecard)
    fetchAnalyticsHeatmap(selectedCreator).then(setHeatmap)
    fetchAnalyticsPlatformBreakdown(selectedCreator).then(setBreakdown)
    fetchAnalyticsContentHistory(selectedCreator).then(d => setContentHistory(d || []))
    fetchAnalyticsTimingAudit(selectedCreator).then(setTimingAudit)
    fetchAnalyticsOptimizerImpact(selectedCreator).then(setImpact)
  }, [selectedCreator])

  const formatHour = h => { const ap = h < 12 ? 'AM' : 'PM'; return `${h === 0 ? 12 : h > 12 ? h - 12 : h} ${ap}` }

  const sortedHistory = [...contentHistory].sort((a, b) => {
    const va = a[sortField] ?? 0, vb = b[sortField] ?? 0
    return sortDir === 'desc' ? vb - va : va - vb
  })

  const toggleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortField(field); setSortDir('desc') }
  }

  if (loading) return (
    <div className="page" style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: '1.5rem', color: 'var(--text-hint)', animation: 'pulse 1.5s infinite' }}>⏳ Loading analytics...</div>
    </div>
  )

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <h1>Analytics</h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>Deep-dive into your performance data</p>
        </div>
        <select className="form-select" style={{ width: 220 }} value={selectedCreator || ''}
          onChange={e => setSelectedCreator(e.target.value)}>
          {creators.map(c => <option key={c.creator_id} value={c.creator_id}>Creator #{c.creator_id}</option>)}
        </select>
      </div>

      {/* ═══ PANEL 1: Creator Scorecard ═══ */}
      {scorecard && (
        <div className="grid-4" style={{ marginBottom: 20 }}>
          <StatCard label="Base Engagement" value={`${scorecard.base_engagement}x`}
            sub={scorecard.engagement_label}
            positive={scorecard.base_engagement > 1.10 ? true : scorecard.base_engagement < 0.80 ? false : undefined} />
          <StatCard label="Global Avg" value={scorecard.global_avg_engagement} sub="Historical average" />
          <StatCard label="Best Platform" value={scorecard.best_platform}
            sub={`Best type: ${scorecard.best_content_type}`} />
          <StatCard label="Submissions" value={scorecard.total_submissions}
            sub={`Cooldown: ${scorecard.cooldown_hours}h`} />
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* ═══ PANEL 2: Engagement Heatmap ═══ */}
        <div className="card">
          <div className="card-header flex-between">
            <h3>Engagement Heatmap</h3>
            {heatmap?.personal_peak && (
              <span className="text-xs" style={{ color: 'var(--green)' }}>
                Peak: {heatmap.personal_peak.platform} @ {heatmap.personal_peak.hour}:00
              </span>
            )}
          </div>
          {heatmap?.heatmap && (
            <div className="heatmap">
              <div className="heatmap-hours">
                <div />
                {Array.from({ length: 24 }, (_, i) => <div key={i} className="heatmap-hour">{i}</div>)}
              </div>
              {Object.entries(heatmap.heatmap).map(([platform, slots]) => (
                <div key={platform} className="heatmap-row">
                  <div className="heatmap-label">{platform}</div>
                  {slots.map((s, i) => {
                    const intensity = heatmap.global_max > heatmap.global_min
                      ? (s.score - heatmap.global_min) / (heatmap.global_max - heatmap.global_min) : 0.5
                    const isPeak = heatmap.personal_peak?.platform === platform && heatmap.personal_peak?.hour === s.hour
                    return (
                      <div key={i} className="heatmap-cell" title={`${platform} ${s.hour}:00 — ${s.score} ${s.is_peak ? '(Peak hours)' : ''}`}
                        style={{
                          background: `rgba(15, 110, 86, ${Math.max(0.08, intensity * 0.9)})`,
                          border: isPeak ? '2px solid var(--green)' : s.is_peak ? '1px solid var(--amber-border)' : 'none',
                        }} />
                    )
                  })}
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: '0.6rem', color: 'var(--text-hint)' }}>
                <span>Low ({heatmap.global_min})</span>
                <span>High ({heatmap.global_max})</span>
              </div>
            </div>
          )}
        </div>

        {/* ═══ PANEL 3: Platform Breakdown ═══ */}
        {breakdown && (
          <div className="card">
            <div className="card-header">
              <h3>Platform Breakdown</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: 4 }}>
                {breakdown.affinity_text}
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {Object.values(breakdown.breakdown).map(b => {
                const isWinner = b.avg_engagement === Math.max(...Object.values(breakdown.breakdown).map(x => x.avg_engagement))
                return (
                  <div key={`${b.platform}_${b.content_type}`} style={{
                    padding: 14, borderRadius: 'var(--radius)', border: isWinner ? '2px solid var(--green-border)' : '1px solid var(--border)',
                    background: isWinner ? 'var(--green-bg)' : 'var(--bg-surface)',
                  }}>
                    <div className="flex-between" style={{ marginBottom: 6 }}>
                      <Badge type={b.platform}>{b.platform}</Badge>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{b.content_type}</span>
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{b.avg_engagement}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Peak: {b.peak_engagement} @ {formatHour(b.best_slot)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* ═══ PANEL 4: Content Performance History ═══ */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header flex-between">
          <h3>Content Performance History</h3>
          <span className="text-xs">{contentHistory.length} items</span>
        </div>
        <div className="table-wrap" style={{ maxHeight: 360, overflow: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>ID</th><th>Type</th><th>Submitted</th><th>Sensitivity</th>
                <th>Platform</th><th>Slot</th><th>Decision</th>
                <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('score')}>Score {sortField === 'score' ? (sortDir === 'desc' ? '↓' : '↑') : ''}</th>
                <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('gain_pct')}>Gain {sortField === 'gain_pct' ? (sortDir === 'desc' ? '↓' : '↑') : ''}</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {sortedHistory.map((r, i) => (
                <tr key={r.content_id} className="animate-in" style={{ animationDelay: `${i * 0.03}s` }}>
                  <td style={{ fontWeight: 600 }}>#{r.content_id}</td>
                  <td>{r.content_type} {r.is_hook_score && <span title="High share potential" style={{ fontSize: '0.7rem' }}>🔥</span>}</td>
                  <td>{formatHour(r.submitted_hour)}</td>
                  <td><Badge type={r.time_sensitivity === 'High' ? 'HIGH' : r.time_sensitivity === 'Low' ? 'LOW' : 'MEDIUM'}>{r.time_sensitivity}</Badge></td>
                  <td>{r.platform ? <Badge type={r.platform}>{r.platform}</Badge> : '—'}</td>
                  <td>{r.recommended_slot != null ? `${r.recommended_slot}:00` : '—'}</td>
                  <td><Badge type={r.decision}>{r.decision === 'SCHEDULE' ? 'Schedule' : r.decision === 'POST_NOW' ? 'Post Now' : r.decision}</Badge></td>
                  <td>{r.score != null ? <ScoreBar score={r.score} /> : '—'}</td>
                  <td style={{ color: r.gain_pct > 30 ? 'var(--green)' : r.gain_pct > 10 ? 'var(--amber)' : 'var(--text-muted)', fontWeight: 600 }}>
                    {r.gain_pct > 0 ? `+${r.gain_pct}%` : `${r.gain_pct}%`}
                  </td>
                  <td>{r.confidence ? <Badge type={r.confidence}>{r.confidence}</Badge> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* ═══ PANEL 5: Submission Timing Audit ═══ */}
        {timingAudit && (
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Submission Timing Audit</h3>
            <div className="flex-between" style={{ marginBottom: 8 }}>
              <span className="text-muted" style={{ fontSize: '0.8rem' }}>Avg submission hour</span>
              <strong>{formatHour(Math.round(timingAudit.avg_submission_hour))}</strong>
            </div>
            <div className="flex-between" style={{ marginBottom: 8 }}>
              <span className="text-muted" style={{ fontSize: '0.8rem' }}>Personal peak hour</span>
              <strong style={{ color: 'var(--green)' }}>{formatHour(timingAudit.personal_peak_hour)}</strong>
            </div>
            <div className="flex-between" style={{ marginBottom: 8 }}>
              <span className="text-muted" style={{ fontSize: '0.8rem' }}>Gap</span>
              <strong style={{ color: timingAudit.gap_hours > 3 ? 'var(--red)' : 'var(--text-main)' }}>{timingAudit.gap_hours} hours</strong>
            </div>
            <div className="flex-between" style={{ marginBottom: 12 }}>
              <span className="text-muted" style={{ fontSize: '0.8rem' }}>Submissions in peak window</span>
              <strong>{timingAudit.peak_window_pct}%</strong>
            </div>

            {/* Hour distribution bar chart */}
            <div style={{ marginTop: 12 }}>
              <div className="text-xs" style={{ marginBottom: 6 }}>Submission Distribution vs Engagement Curve</div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 1, height: 80 }}>
                {timingAudit.hour_distribution.map((count, h) => {
                  const maxCount = Math.max(...timingAudit.hour_distribution, 1)
                  const maxEng = Math.max(...timingAudit.engagement_curve, 1)
                  const barH = (count / maxCount) * 100
                  const engH = (timingAudit.engagement_curve[h] / maxEng) * 100
                  const isPeak = h >= 18 && h <= 22
                  return (
                    <div key={h} style={{ flex: 1, position: 'relative', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}
                      title={`${h}:00 — ${count} submissions, engagement: ${timingAudit.engagement_curve[h]}`}>
                      {/* Engagement line dot */}
                      <div style={{
                        position: 'absolute', bottom: `${engH}%`, left: '50%', transform: 'translate(-50%, 50%)',
                        width: 4, height: 4, borderRadius: '50%', background: 'var(--green)', zIndex: 2,
                      }} />
                      {/* Submission bar */}
                      <div style={{
                        width: '100%', height: `${barH}%`, minHeight: count > 0 ? 3 : 0,
                        background: isPeak ? 'rgba(15,110,86,0.3)' : 'var(--border)', borderRadius: '2px 2px 0 0',
                      }} />
                    </div>
                  )
                })}
              </div>
              <div style={{ display: 'flex', gap: 1, marginTop: 2 }}>
                {Array.from({ length: 24 }, (_, i) => (
                  <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: '0.5rem', color: 'var(--text-hint)' }}>
                    {i % 6 === 0 ? i : ''}
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                <span>█ Submissions</span>
                <span style={{ color: 'var(--green)' }}>● Engagement</span>
                <span style={{ background: 'rgba(15,110,86,0.2)', padding: '0 4px' }}>Peak window</span>
              </div>
            </div>

            {timingAudit.avg_potential_gain > 20 && (
              <div style={{ marginTop: 12, padding: 10, background: 'var(--amber-bg)', borderRadius: 'var(--radius)', border: '1px solid var(--amber-border)', fontSize: '0.8rem' }}>
                On average, the optimizer found a <strong>+{timingAudit.avg_potential_gain}%</strong> better slot than when you submitted. Consider batching and scheduling.
              </div>
            )}
          </div>
        )}

        {/* ═══ PANEL 6: Optimizer Impact ═══ */}
        {impact && (
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Optimizer Impact</h3>

            {/* Hero number */}
            <div style={{ textAlign: 'center', padding: '16px 0', marginBottom: 16, background: 'var(--green-bg)', borderRadius: 'var(--radius)' }}>
              <div className="text-xs">Average Score Uplift</div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--green)' }}>+{impact.avg_score_uplift}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>points per recommendation</div>
            </div>

            <div style={{ fontSize: '0.8rem' }}>
              <div className="flex-between" style={{ marginBottom: 8 }}>
                <span className="text-muted">Best score ever</span>
                <strong>{impact.best_score}</strong>
              </div>
              <div className="flex-between" style={{ marginBottom: 8 }}>
                <span className="text-muted">Worst score</span>
                <strong style={{ color: 'var(--red)' }}>{impact.worst_score}</strong>
              </div>
              <div className="flex-between" style={{ marginBottom: 8 }}>
                <span className="text-muted">Score gap</span>
                <strong>{impact.score_gap} pts</strong>
              </div>
              <div className="flex-between" style={{ marginBottom: 8 }}>
                <span className="text-muted">Max single gain</span>
                <strong style={{ color: 'var(--green)' }}>+{impact.max_single_gain}%</strong>
              </div>
              <div className="flex-between" style={{ marginBottom: 8 }}>
                <span className="text-muted">Schedule rate</span>
                <strong>{impact.schedule_rate_pct}%</strong>
              </div>
            </div>

            {/* Confidence donut (CSS) */}
            <div style={{ marginTop: 16 }}>
              <div className="text-xs" style={{ marginBottom: 8 }}>Confidence Breakdown</div>
              <div style={{ display: 'flex', gap: 8 }}>
                {[
                  { key: 'HIGH', color: 'var(--green)', bg: 'var(--green-bg)' },
                  { key: 'MEDIUM', color: 'var(--amber)', bg: 'var(--amber-bg)' },
                  { key: 'LOW', color: 'var(--red)', bg: 'var(--red-bg)' },
                ].map(({ key, color, bg }) => {
                  const count = impact.confidence_breakdown[key] || 0
                  const pct = impact.total_recommendations > 0 ? (count / impact.total_recommendations * 100) : 0
                  return (
                    <div key={key} style={{ flex: 1, textAlign: 'center', padding: 10, background: bg, borderRadius: 'var(--radius)' }}>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color }}>{count}</div>
                      <div style={{ fontSize: '0.6rem', color }}>{key} ({pct.toFixed(0)}%)</div>
                    </div>
                  )
                })}
              </div>
            </div>

            {impact.best_recommendation && (
              <div style={{ marginTop: 12, padding: 10, background: 'var(--bg-surface)', borderRadius: 'var(--radius)', fontSize: '0.8rem' }}>
                Best recommendation: <strong>{impact.best_recommendation.platform}</strong> at <strong>{impact.best_recommendation.slot}:00</strong> for content #{impact.best_recommendation.content_id}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
