import { NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'

export default function TopBar({ session, onLogout }) {
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
        <div className="topbar-right">
          <div className="topbar-status">
            <span className={`status-dot ${live ? 'live' : ''}`} />
            <span className="text-xs">{live ? 'Live' : '...'}</span>
          </div>
          {session && (
            <div className="topbar-user">
              <div className="topbar-avatar">{session.name?.charAt(0)?.toUpperCase() || '?'}</div>
              <span className="text-xs">{session.name}</span>
              <button className="topbar-logout" onClick={onLogout} title="Sign out">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>
          )}
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
        .topbar-right { display: flex; align-items: center; gap: 16px; }
        .topbar-status { display: flex; align-items: center; gap: 6px; }
        .status-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background: var(--border);
        }
        .status-dot.live {
          background: var(--green);
          animation: pulse 2s infinite;
        }
        .topbar-user {
          display: flex; align-items: center; gap: 8px;
          padding: 4px 8px; border-radius: var(--radius);
          background: var(--bg-surface);
        }
        .topbar-avatar {
          width: 24px; height: 24px; border-radius: 50%;
          background: var(--accent); color: white;
          display: flex; align-items: center; justify-content: center;
          font-size: 0.65rem; font-weight: 700;
        }
        .topbar-logout {
          background: none; border: none; cursor: pointer; padding: 4px;
          color: var(--text-muted); display: flex;
        }
        .topbar-logout:hover { color: var(--red); }
      `}</style>
    </header>
  )
}
