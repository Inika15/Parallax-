import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import TopBar from './components/TopBar'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import Optimize from './pages/Optimize'
import Creators from './pages/Creators'
import CreatorProfile from './pages/CreatorProfile'
import Schedule from './pages/Schedule'

function App() {
  const [onboarded, setOnboarded] = useState(
    localStorage.getItem('postoptima_onboarded') === 'true'
  )

  if (!onboarded) {
    return <Onboarding onComplete={() => setOnboarded(true)} />
  }

  return (
    <div>
      <TopBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/optimize" element={<Optimize />} />
        <Route path="/creators" element={<Creators />} />
        <Route path="/creators/:id" element={<CreatorProfile />} />
        <Route path="/schedule" element={<Schedule />} />
      </Routes>
    </div>
  )
}

export default App
