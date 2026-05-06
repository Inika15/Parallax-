import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchCreators } from '../api'
import { Badge, ScoreBar } from '../components/Shared'

export default function Creators() {
  const [creators, setCreators] = useState([])
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  useEffect(() => { fetchCreators().then(setCreators) }, [])

  const filtered = creators.filter(c =>
    c.creator_id.includes(search) || search === ''
  )

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 24 }}>
        <div>
          <h1>Creators</h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            {creators.length} creators with personalized DNA profiles
          </p>
        </div>
        <input
          className="form-input"
          placeholder="Search by ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: 200 }}
        />
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Creator</th>
              <th>Base Engagement</th>
              <th>Posts</th>
              <th>Avg Score</th>
              <th>Data Richness</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={c.creator_id}
                  className="animate-in"
                  style={{ animationDelay: `${i * 0.03}s`, cursor: 'pointer' }}
                  onClick={() => navigate(`/creators/${c.creator_id}`)}>
                <td>
                  <div className="flex-row">
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%',
                      background: 'var(--bg-surface)', border: '1px solid var(--border)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.75rem', fontWeight: 600,
                    }}>
                      {c.creator_id}
                    </div>
                    <span style={{ fontWeight: 600 }}>Creator #{c.creator_id}</span>
                  </div>
                </td>
                <td>{c.base_engagement}x</td>
                <td>{c.total_posts}</td>
                <td><ScoreBar score={c.avg_score} /></td>
                <td>
                  <div className="score-bar-wrap">
                    <div className="score-bar" style={{ height: 4 }}>
                      <div className="score-bar-fill"
                        style={{
                          width: `${c.data_richness * 100}%`,
                          background: c.data_richness >= 0.7 ? 'var(--green)' : c.data_richness >= 0.3 ? 'var(--amber)' : 'var(--red)',
                        }} />
                    </div>
                    <span style={{ fontSize: '0.75rem' }}>{(c.data_richness * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td>
                  {c.is_cold_start ? <Badge type="cold">Cold-Start</Badge> : <Badge type="HIGH">Active</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
