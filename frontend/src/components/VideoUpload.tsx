import { useState, useRef, DragEvent, ChangeEvent } from 'react'
import axios from 'axios'

interface Props {
  onJobStarted: (jobId: string) => void
}

export function VideoUpload({ onJobStarted }: Props) {
  const [dragging, setDragging]   = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError]         = useState('')
  const [pisWeights, setPisWeights] = useState({ pagerank: 0.4, betweenness: 0.3, spatial: 0.3 })
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.mp4')) {
      setError('Only MP4 files are supported.')
      return
    }
    if (file.size > 500 * 1024 * 1024) {
      setError('File exceeds 500 MB limit.')
      return
    }
    setError('')
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('video', file)
      fd.append('pis_pagerank',    String(pisWeights.pagerank))
      fd.append('pis_betweenness', String(pisWeights.betweenness))
      fd.append('pis_spatial',     String(pisWeights.spatial))

      const res = await axios.post('/api/analyze', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      onJobStarted(res.data.job_id)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed. Is the backend running?')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const totalW = pisWeights.pagerank + pisWeights.betweenness + pisWeights.spatial
  const weightsValid = Math.abs(totalW - 1.0) < 0.01

  return (
    <div style={{ maxWidth: 720, margin: '4rem auto' }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚽</div>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2.4rem', fontWeight: 800,
                     background: 'linear-gradient(135deg, var(--accent-green), var(--accent-blue))',
                     WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                     backgroundClip: 'text', marginBottom: '0.75rem' }}>
          Football Analytics Platform
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', lineHeight: 1.6 }}>
          Upload a 60-second football clip to generate passing networks, pitch control maps,
          player influence scores, and AI tactical insights.
        </p>
      </div>

      {/* Feature pills */}
      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center',
                    flexWrap: 'wrap', marginBottom: '2.5rem' }}>
        {['🏃 YOLO + ByteTrack', '🗺 Spearman Pitch Control', '🕸 NetworkX Passing Network',
          '🏆 Player Influence Score', '🤖 AI Tactical Insights', '📄 PDF Report'].map(f => (
          <span key={f} style={{ padding: '0.4rem 0.9rem', borderRadius: '100px',
                                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                                  fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{f}</span>
        ))}
      </div>

      {/* Upload Zone */}
      <div
        id="upload-zone"
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{ marginBottom: '1.5rem' }}
      >
        <input ref={fileRef} type="file" accept=".mp4" style={{ display: 'none' }}
               onChange={onFileChange} id="file-input" />
        {uploading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <div className="spinner" style={{ width: 48, height: 48 }} />
            <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>Uploading & starting analysis…</span>
          </div>
        ) : (
          <>
            <div className="upload-icon">📹</div>
            <div className="upload-title">Drop your MP4 video here</div>
            <div className="upload-subtitle">or click to browse · Max 60 seconds · Up to 500 MB</div>
          </>
        )}
      </div>

      {/* PIS Weights */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="card-header">
          <span className="card-icon gold">⚖</span>
          Player Influence Score Weights
          {!weightsValid && (
            <span style={{ marginLeft: 'auto', color: 'var(--accent-red)', fontSize: '0.8rem' }}>
              ⚠ Weights must sum to 1.0 (current: {totalW.toFixed(2)})
            </span>
          )}
        </div>
        {(['pagerank', 'betweenness', 'spatial'] as const).map(k => (
          <div key={k} style={{ marginBottom: '0.9rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
              <label style={{ fontSize: '0.85rem', textTransform: 'capitalize',
                              color: 'var(--text-secondary)' }}>
                {k === 'pagerank' ? 'PageRank' : k === 'betweenness' ? 'Betweenness Centrality' : 'Spatial Dominance'}
              </label>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-blue)' }}>
                {pisWeights[k].toFixed(2)}
              </span>
            </div>
            <input type="range" min={0} max={1} step={0.05}
                   value={pisWeights[k]}
                   onChange={e => setPisWeights(w => ({ ...w, [k]: parseFloat(e.target.value) }))}
                   style={{ width: '100%', accentColor: 'var(--accent-green)' }} />
          </div>
        ))}
      </div>

      {error && (
        <div style={{ padding: '0.875rem 1rem', background: 'rgba(233,69,96,0.12)',
                      border: '1px solid rgba(233,69,96,0.3)', borderRadius: 'var(--radius-md)',
                      color: 'var(--accent-red)', fontSize: '0.88rem', marginBottom: '1rem' }}>
          ⚠ {error}
        </div>
      )}
    </div>
  )
}
