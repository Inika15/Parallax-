import { useState } from 'react'

const USERS = Array.from({ length: 50 }, (_, i) => ({
  id: String(i + 1),
  email: `creator${i + 1}@postoptima.io`,
}))

export default function AuthLogin({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [creatorId, setCreatorId] = useState('1')
  const [error, setError] = useState('')
  const [shake, setShake] = useState(false)

  const doShake = () => { setShake(true); setTimeout(() => setShake(false), 500) }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError('Please fill in all fields')
      doShake()
      return
    }

    if (mode === 'signup' && !name) {
      setError('Please enter your name')
      doShake()
      return
    }

    // Check existing users in localStorage
    const users = JSON.parse(localStorage.getItem('postoptima_users') || '{}')

    if (mode === 'signup') {
      if (users[email]) {
        setError('Account already exists. Please log in.')
        doShake()
        return
      }
      users[email] = { name, password, creatorId, createdAt: Date.now() }
      localStorage.setItem('postoptima_users', JSON.stringify(users))
    } else {
      const user = users[email]
      if (!user) {
        setError('No account found. Please sign up first.')
        doShake()
        return
      }
      if (user.password !== password) {
        setError('Invalid password')
        doShake()
        return
      }
    }

    // Login successful
    const user = JSON.parse(localStorage.getItem('postoptima_users') || '{}')[email]
    const session = {
      email,
      name: user?.name || email.split('@')[0],
      creatorId: user?.creatorId || '1',
      loggedInAt: Date.now(),
    }
    localStorage.setItem('postoptima_session', JSON.stringify(session))
    onLogin(session)
  }

  return (
    <div className="auth-page">
      <div className="auth-bg">
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />
        <div className="auth-orb auth-orb-3" />
      </div>

      <div className={`auth-card ${shake ? 'shake' : ''}`}>
        <div className="auth-logo">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
          </svg>
          <span>PostOptima</span>
        </div>

        <h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
        <p className="auth-sub">
          {mode === 'login'
            ? 'Sign in to access your analytics dashboard'
            : 'Join PostOptima and optimize your content strategy'}
        </p>

        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <div className="form-group">
              <label>Full Name</label>
              <input className="form-input" type="text" placeholder="Sanjana" value={name}
                onChange={e => setName(e.target.value)} autoComplete="name" />
            </div>
          )}

          <div className="form-group">
            <label>Email</label>
            <input className="form-input" type="email" placeholder="you@example.com" value={email}
              onChange={e => setEmail(e.target.value)} autoComplete="email" />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input className="form-input" type="password" placeholder="••••••••" value={password}
              onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
          </div>

          {mode === 'signup' && (
            <div className="form-group">
              <label>Link to Creator Profile (ID 1–50)</label>
              <select className="form-select" value={creatorId} onChange={e => setCreatorId(e.target.value)}>
                {USERS.map(u => (
                  <option key={u.id} value={u.id}>Creator #{u.id} — {u.email}</option>
                ))}
              </select>
            </div>
          )}

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-submit">
            {mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="auth-switch">
          {mode === 'login' ? (
            <span>Don't have an account? <button className="link-btn" onClick={() => { setMode('signup'); setError('') }}>Sign up</button></span>
          ) : (
            <span>Already have an account? <button className="link-btn" onClick={() => { setMode('login'); setError('') }}>Sign in</button></span>
          )}
        </div>

        <div className="auth-demo">
          <button className="link-btn" onClick={() => {
            const session = { email: 'demo@postoptima.io', name: 'Demo User', creatorId: '1', loggedInAt: Date.now() }
            localStorage.setItem('postoptima_session', JSON.stringify(session))
            onLogin(session)
          }}>
            Skip — use demo account →
          </button>
        </div>
      </div>
    </div>
  )
}
