import { NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'

export default function TopBar() {
  const [live, setLive] = useState(false)

  useEffect(() => {
    fetch('http://localhost:8000/api/health')
      .then(r => r.json())
      .then(() => setLive(true))
      .catch(() => setLive(false))
  }, [])

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-brand">PostOptima</div>
        <nav className="topbar-nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/optimize">Optimize</NavLink>
          <NavLink to="/creators">Creators</NavLink>
          <NavLink to="/schedule">Schedule</NavLink>
          <NavLink to="/analytics">Analytics</NavLink>
        </nav>
        <div className="topbar-status">
          <span className={`status-dot ${live ? 'live' : ''}`} />
          <span className="text-xs">{live ? 'System live' : 'Connecting...'}</span>
        </div>
      </div>
      <style>{`
        .topbar {
          position: sticky; top: 0; z-index: 50;
          background: var(--bg-card);
          border-bottom: 1px solid var(--border);
          box-shadow: var(--shadow-sm);
        }
        .topbar-inner {
          max-width: 1280px; margin: 0 auto;
          display: flex; align-items: center; justify-content: space-between;
          padding: 0 32px; height: 52px;
        }
        .topbar-brand {
          font-size: 1rem; font-weight: 700;
          letter-spacing: -0.02em;
        }
        .topbar-nav { display: flex; gap: 24px; }
        .topbar-nav a {
          font-size: 0.8rem; color: var(--text-muted);
          padding: 16px 0; border-bottom: 2px solid transparent;
          transition: all var(--transition);
        }
        .topbar-nav a:hover { color: var(--text-main); text-decoration: none; }
        .topbar-nav a.active { color: var(--text-main); border-bottom-color: var(--accent); }
        .topbar-status { display: flex; align-items: center; gap: 6px; }
        .status-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background: var(--border);
        }
        .status-dot.live {
          background: var(--green);
          animation: pulse 2s infinite;
        }
      `}</style>
    </header>
  )
}
