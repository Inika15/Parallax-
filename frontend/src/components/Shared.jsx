export function Badge({ type, children }) {
  const classMap = {
    instagram: 'badge-ig', youtube: 'badge-yt', Instagram: 'badge-ig', YouTube: 'badge-yt',
    POST_NOW: 'badge-now', SCHEDULE: 'badge-schedule',
    HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low',
    cold: 'badge-cold',
  }
  return <span className={`badge ${classMap[type] || ''}`}>{children || type}</span>
}

export function StatCard({ label, value, sub, positive }) {
  return (
    <div className="stat-card animate-in">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className={`stat-sub ${positive === true ? 'stat-positive' : positive === false ? 'stat-negative' : ''}`}>{sub}</div>}
    </div>
  )
}

export function ScoreBar({ score, max = 100 }) {
  const pct = Math.min((score / max) * 100, 100)
  return (
    <div className="score-bar-wrap">
      <div className="score-bar">
        <div className="score-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="score-value">{score}</span>
    </div>
  )
}

export function PipelineFlow({ activeStep = -1 }) {
  const steps = ['Content Arrives', 'Validate', 'Score 48 Slots', 'Pick Best', 'Compare vs Now', 'Decide', 'Output JSON']
  return (
    <div className="pipeline">
      {steps.map((s, i) => (
        <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span className={`pipeline-step ${i === activeStep ? 'active' : ''}`}>{s}</span>
          {i < steps.length - 1 && <span className="pipeline-arrow">→</span>}
        </span>
      ))}
    </div>
  )
}
