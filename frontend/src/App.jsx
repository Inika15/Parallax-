import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import TopBar from './components/TopBar'
import AuthLogin from './pages/AuthLogin'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import Optimize from './pages/Optimize'
import Creators from './pages/Creators'
import CreatorProfile from './pages/CreatorProfile'
import Schedule from './pages/Schedule'
import Analytics from './pages/Analytics'

function App() {
  const [session, setSession] = useState(() => {
    try { return JSON.parse(localStorage.getItem('postoptima_session')) } catch { return null }
  })
  const [onboarded, setOnboarded] = useState(
    localStorage.getItem('postoptima_onboarded') === 'true'
  )

  // Gate 1: Auth
  if (!session) {
    return <AuthLogin onLogin={(s) => setSession(s)} />
  }

  // Gate 2: Onboarding
  if (!onboarded) {
    return <Onboarding onComplete={() => setOnboarded(true)} />
  }

  const handleLogout = () => {
    localStorage.removeItem('postoptima_session')
    setSession(null)
  }

  return (
    <div>
      <TopBar session={session} onLogout={handleLogout} />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/optimize" element={<Optimize />} />
        <Route path="/creators" element={<Creators />} />
        <Route path="/creators/:id" element={<CreatorProfile />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </div>
  )
}

export default App
