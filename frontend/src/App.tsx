import { useState, useCallback } from 'react'
import { VideoUpload } from './components/VideoUpload'
import { Dashboard } from './components/Dashboard'
import './index.css'

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null)
  const [analysisComplete, setAnalysisComplete] = useState(false)

  const handleJobStarted = useCallback((id: string) => {
    setJobId(id)
    setAnalysisComplete(false)
  }, [])

  const handleAnalysisComplete = useCallback(() => {
    setAnalysisComplete(true)
  }, [])

  const handleReset = useCallback(() => {
    setJobId(null)
    setAnalysisComplete(false)
  }, [])

  return (
    <div className="app">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-logo">⚽ Football Analytics Platform</div>
        <span className="navbar-subtitle">
          Passing Networks · Pitch Control · Tactical Insights
        </span>
        {jobId && (
          <button className="btn btn-outline" onClick={handleReset} style={{ marginLeft: 'auto' }}>
            ↩ New Analysis
          </button>
        )}
      </nav>

      <main className="main-content">
        {!jobId ? (
          <VideoUpload onJobStarted={handleJobStarted} />
        ) : (
          <Dashboard
            jobId={jobId}
            onComplete={handleAnalysisComplete}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  )
}
