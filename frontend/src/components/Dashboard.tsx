import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { PitchControlView } from './PitchControlView'
import { PassingNetworkView } from './PassingNetworkView'
import { InfluenceView } from './InfluenceView'
import { TacticsView } from './TacticsView'
import { InsightsView } from './InsightsView'

interface Props {
  jobId: string
  onComplete: () => void
  onReset: () => void
}

interface Status {
  status: string
  progress: number
  message: string
}

const TABS = [
  { id: 'overview',      label: '📊 Overview' },
  { id: 'network',       label: '🕸 Passing Network' },
  { id: 'pitch-control', label: '🗺 Pitch Control' },
  { id: 'influence',     label: '🏆 Influence' },
  { id: 'tactics',       label: '🧠 Tactics' },
  { id: 'insights',      label: '🤖 AI Insights' },
]

export function Dashboard({ jobId, onComplete, onReset }: Props) {
  const [status, setStatus]     = useState<Status>({ status: 'pending', progress: 0, message: 'Queued…' })
  const [results, setResults]   = useState<any>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError]       = useState('')

  const pollStatus = useCallback(async () => {
    try {
      const res = await axios.get(`/api/status/${jobId}`)
      setStatus(res.data)
      if (res.data.status === 'completed') {
        onComplete()
        const rRes = await axios.get(`/api/results/${jobId}`)
        setResults(rRes.data)
      } else if (res.data.status === 'failed') {
        setError(res.data.message)
      }
    } catch (e: any) {
      setError(e.message)
    }
  }, [jobId, onComplete])

  useEffect(() => {
    pollStatus()
    const interval = setInterval(() => {
      if (status.status !== 'completed' && status.status !== 'failed') {
        pollStatus()
      }
    }, 2500)
    return () => clearInterval(interval)
  }, [pollStatus, status.status])

  const statusColor: Record<string, string> = {
    pending:    'var(--accent-gold)',
    processing: 'var(--accent-blue)',
    completed:  'var(--accent-green)',
    failed:     'var(--accent-red)',
  }

  return (
    <div>
      {/* Status Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
              JOB ID
            </div>
            <code style={{ fontSize: '0.85rem', color: 'var(--accent-blue)' }}>{jobId}</code>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <span className={`status-pill ${status.status}`}>
              <span className={`status-dot ${status.status === 'processing' ? 'pulse' : ''}`} />
              {status.status.toUpperCase()}
            </span>
          </div>
          {status.status === 'completed' && (
            <a href={`/api/export/${jobId}/pdf`} download className="btn btn-outline" style={{ textDecoration: 'none' }}>
              📄 Download PDF
            </a>
          )}
        </div>

        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            <span>{status.message}</span>
            <span style={{ color: statusColor[status.status], fontWeight: 600 }}>
              {status.progress}%
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${status.progress}%` }} />
          </div>
        </div>

        {error && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(233,69,96,0.1)',
                        borderRadius: 'var(--radius-sm)', color: 'var(--accent-red)', fontSize: '0.85rem' }}>
            ⚠ {error}
          </div>
        )}
      </div>

      {/* Tabs */}
      {results && (
        <>
          <div className="tabs">
            {TABS.map(t => (
              <button key={t.id} id={`tab-${t.id}`}
                      className={`tab ${activeTab === t.id ? 'active' : ''}`}
                      onClick={() => setActiveTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>

          {activeTab === 'overview'      && <OverviewPanel results={results} />}
          {activeTab === 'network'       && <PassingNetworkView data={results.passing_network} />}
          {activeTab === 'pitch-control' && <PitchControlView data={results.pitch_control} />}
          {activeTab === 'influence'     && <InfluenceView data={results.influence_rankings} />}
          {activeTab === 'tactics'       && <TacticsView data={results.tactical_insights} />}
          {activeTab === 'insights'      && <InsightsView data={results.ai_insights} />}
        </>
      )}

      {/* Loading state */}
      {!results && status.status !== 'failed' && (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
          <div className="spinner" style={{ width: 48, height: 48, margin: '0 auto 1.5rem' }} />
          <p>Analysis in progress — results will appear when complete</p>
        </div>
      )}
    </div>
  )
}

function OverviewPanel({ results }: { results: any }) {
  const meta  = results.video_metadata  || {}
  const poss  = results.possession_stats || {}
  const pc    = results.pitch_control?.summary || {}
  const net   = results.passing_network?.summary || {}
  const evts  = results.event_summary || {}

  return (
    <div>
      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
        {/* Video Info */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon blue">📹</span> Video Info
          </div>
          <div className="metric-grid">
            {[
              { v: `${meta.duration_sec?.toFixed(1)}s`, l: 'Duration' },
              { v: `${meta.fps?.toFixed(0)} fps`,        l: 'Frame Rate' },
              { v: `${meta.total_frames}`,               l: 'Total Frames' },
              { v: `${meta.width}×${meta.height}`,       l: 'Resolution' },
            ].map(m => (
              <div key={m.l} className="metric-badge">
                <div className="metric-value">{m.v}</div>
                <div className="metric-label">{m.l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Possession */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon green">⚽</span> Possession
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--accent-blue)' }}>
              🔵 Home {poss.home_pct?.toFixed(1)}%
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--accent-red)' }}>
              🔴 Away {poss.away_pct?.toFixed(1)}%
            </span>
          </div>
          <div className="possession-bar">
            <div className="possession-home" style={{ width: `${poss.home_pct}%` }} />
            <div className="possession-away" style={{ width: `${poss.away_pct}%` }} />
          </div>
          <div className="metric-grid" style={{ marginTop: '1rem' }}>
            {[
              { v: `${pc.home_dominance_pct?.toFixed(1)}%`, l: 'Home Pitch Control' },
              { v: `${pc.away_dominance_pct?.toFixed(1)}%`, l: 'Away Pitch Control' },
            ].map(m => (
              <div key={m.l} className="metric-badge">
                <div className="metric-value" style={{ fontSize: '1.4rem' }}>{m.v}</div>
                <div className="metric-label">{m.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Event Summary */}
      <div className="card">
        <div className="card-header">
          <span className="card-icon gold">📋</span> Event Summary
        </div>
        <div className="metric-grid">
          <div className="metric-badge">
            <div className="metric-value">{evts.total_events || 0}</div>
            <div className="metric-label">Total Events</div>
          </div>
          {Object.entries(evts.by_type || {}).map(([type, count]) => (
            <div key={type} className="metric-badge">
              <div className="metric-value">{count as number}</div>
              <div className="metric-label">{type.replace(/_/g, ' ')}</div>
            </div>
          ))}
          <div className="metric-badge">
            <div className="metric-value">{net.home_total_passes || 0}</div>
            <div className="metric-label">Home Passes</div>
          </div>
          <div className="metric-badge">
            <div className="metric-value">{net.away_total_passes || 0}</div>
            <div className="metric-label">Away Passes</div>
          </div>
        </div>
      </div>
    </div>
  )
}
