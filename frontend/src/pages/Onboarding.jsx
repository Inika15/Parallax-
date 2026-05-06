import { useState } from 'react'

const STEPS = [
  {
    title: 'Welcome to PostOptima',
    subtitle: 'Let\'s personalize your experience. A few quick questions first.',
    type: 'welcome',
  },
  {
    title: 'What describes you best?',
    subtitle: 'This helps us tailor recommendations to your level.',
    type: 'select-one',
    key: 'experience',
    options: [
      { id: 'beginner', icon: '🌱', label: 'Just Starting', desc: 'New to content creation' },
      { id: 'growing', icon: '📈', label: 'Growing Creator', desc: 'Building an audience' },
      { id: 'established', icon: '⭐', label: 'Established', desc: '10K+ followers' },
      { id: 'professional', icon: '🏆', label: 'Professional', desc: 'Full-time creator' },
    ],
  },
  {
    title: 'What type of content do you create?',
    subtitle: 'Select all that apply.',
    type: 'multi-select',
    key: 'contentTypes',
    options: [
      { id: 'short', icon: '🎬', label: 'Short-form', desc: 'Reels, Shorts, TikToks' },
      { id: 'long', icon: '🎥', label: 'Long-form', desc: 'Videos, Vlogs, Tutorials' },
      { id: 'image', icon: '📸', label: 'Images', desc: 'Photos, Carousels' },
      { id: 'story', icon: '💬', label: 'Stories', desc: 'Ephemeral content' },
    ],
  },
  {
    title: 'Where do you post?',
    subtitle: 'Select your active platforms.',
    type: 'platforms',
    key: 'platforms',
    options: [
      { id: 'instagram', icon: '📷', label: 'Instagram', color: '#E1306C' },
      { id: 'youtube', icon: '▶️', label: 'YouTube', color: '#FF0000' },
      { id: 'tiktok', icon: '🎵', label: 'TikTok', color: '#000000' },
      { id: 'twitter', icon: '𝕏', label: 'X / Twitter', color: '#1DA1F2' },
      { id: 'facebook', icon: '📘', label: 'Facebook', color: '#1877F2' },
      { id: 'linkedin', icon: '💼', label: 'LinkedIn', color: '#0A66C2' },
    ],
  },
  {
    title: 'What\'s your primary goal?',
    subtitle: 'We\'ll optimize around what matters most to you.',
    type: 'select-one',
    key: 'goal',
    options: [
      { id: 'engagement', icon: '💬', label: 'Max Engagement', desc: 'Likes, comments, shares' },
      { id: 'growth', icon: '🚀', label: 'Audience Growth', desc: 'Reach new followers' },
      { id: 'consistency', icon: '📅', label: 'Consistent Posting', desc: 'Never miss a slot' },
      { id: 'monetize', icon: '💰', label: 'Monetization', desc: 'Revenue-optimized timing' },
    ],
  },
]

export default function Onboarding({ onComplete }) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({
    experience: null,
    contentTypes: [],
    platforms: [],
    goal: null,
  })

  const current = STEPS[step]

  const selectOne = (key, value) => {
    setAnswers(a => ({ ...a, [key]: value }))
  }

  const toggleMulti = (key, value) => {
    setAnswers(a => {
      const arr = a[key] || []
      return {
        ...a,
        [key]: arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value],
      }
    })
  }

  const canContinue = () => {
    if (current.type === 'welcome') return true
    if (current.type === 'select-one') return answers[current.key] !== null
    if (current.type === 'multi-select') return (answers[current.key] || []).length > 0
    if (current.type === 'platforms') return (answers[current.key] || []).length > 0
    return true
  }

  const next = () => {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1)
    } else {
      localStorage.setItem('postoptima_profile', JSON.stringify(answers))
      localStorage.setItem('postoptima_onboarded', 'true')
      onComplete(answers)
    }
  }

  return (
    <div className="onboarding-wrap">
      <div className="onboarding-card animate-fade" key={step}>
        {/* Step indicator */}
        <div className="step-indicator">
          {STEPS.map((_, i) => (
            <div key={i} className={`step-dot ${i === step ? 'active' : i < step ? 'done' : ''}`} />
          ))}
        </div>

        <h1>{current.title}</h1>
        <p className="subtitle">{current.subtitle}</p>

        {/* Welcome step */}
        {current.type === 'welcome' && (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '3rem', marginBottom: 16 }}>📊</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.6 }}>
              PostOptima analyzes <strong>4,800+ engagement data points</strong> to find the
              perfect time and platform for every post. Let's get you set up in 30 seconds.
            </p>
          </div>
        )}

        {/* Single select */}
        {current.type === 'select-one' && (
          <div className="option-grid">
            {current.options.map(opt => (
              <button
                key={opt.id}
                className={`option-btn ${answers[current.key] === opt.id ? 'selected' : ''}`}
                onClick={() => selectOne(current.key, opt.id)}
              >
                <span className="option-icon">{opt.icon}</span>
                <strong>{opt.label}</strong>
                <div style={{ fontSize: '0.7rem', marginTop: 4, opacity: 0.7 }}>{opt.desc}</div>
              </button>
            ))}
          </div>
        )}

        {/* Multi select */}
        {current.type === 'multi-select' && (
          <div className="option-grid">
            {current.options.map(opt => (
              <button
                key={opt.id}
                className={`option-btn ${(answers[current.key] || []).includes(opt.id) ? 'selected' : ''}`}
                onClick={() => toggleMulti(current.key, opt.id)}
              >
                <span className="option-icon">{opt.icon}</span>
                <strong>{opt.label}</strong>
                <div style={{ fontSize: '0.7rem', marginTop: 4, opacity: 0.7 }}>{opt.desc}</div>
              </button>
            ))}
          </div>
        )}

        {/* Platform select */}
        {current.type === 'platforms' && (
          <div className="platform-checks">
            {current.options.map(opt => (
              <button
                key={opt.id}
                className={`platform-check ${(answers[current.key] || []).includes(opt.id) ? 'checked' : ''}`}
                onClick={() => toggleMulti(current.key, opt.id)}
              >
                <span>{opt.icon}</span>
                <span>{opt.label}</span>
              </button>
            ))}
          </div>
        )}

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
          {step > 0 ? (
            <button className="btn btn-outline btn-sm" onClick={() => setStep(s => s - 1)}>
              ← Back
            </button>
          ) : <div />}
          <button
            className="btn"
            onClick={next}
            disabled={!canContinue()}
            style={{ opacity: canContinue() ? 1 : 0.4 }}
          >
            {step === STEPS.length - 1 ? 'Launch PostOptima →' : 'Continue →'}
          </button>
        </div>
      </div>
    </div>
  )
}
