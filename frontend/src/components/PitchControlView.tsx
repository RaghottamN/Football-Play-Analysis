import Plot from 'react-plotly.js'

interface Props { data: any }

export function PitchControlView({ data }: Props) {
  if (!data || !data.frames?.length) {
    return <EmptyState msg="No pitch control data available" />
  }

  const summary = data.summary || {}
  const frames  = data.frames  || []
  const frame0  = frames[0]

  const homeMax = Math.max(...(frame0?.ppcf_home?.flat() || [0.5]))
  const totalFrames = frames.length

  return (
    <div>
      {/* Summary metrics */}
      <div className="metric-grid" style={{ marginBottom: '1.25rem' }}>
        {[
          { v: `${summary.home_dominance_pct?.toFixed(1)}%`, l: 'Home Control', color: 'var(--accent-blue)' },
          { v: `${summary.away_dominance_pct?.toFixed(1)}%`, l: 'Away Control', color: 'var(--accent-red)' },
          { v: String(summary.frames_analyzed || totalFrames), l: 'Frames Analyzed', color: 'var(--accent-green)' },
        ].map(m => (
          <div key={m.l} className="metric-badge">
            <div className="metric-value" style={{ color: m.color }}>{m.v}</div>
            <div className="metric-label">{m.l}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        {/* Pitch control heatmap */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon green">🗺</span>
            Pitch Control — Frame 0 (Home Team)
          </div>
          {frame0?.ppcf_home && (
            <div className="plot-container">
              <Plot
                data={[{
                  z:    frame0.ppcf_home,
                  x:    frame0.xgrid,
                  y:    frame0.ygrid,
                  type: 'heatmap',
                  colorscale: [
                    [0,   'rgba(233,69,96,0.9)'],
                    [0.5, 'rgba(20,20,40,0.3)'],
                    [1,   'rgba(0,230,118,0.9)'],
                  ],
                  zmin: 0, zmax: 1,
                  showscale: true,
                  colorbar: {
                    tickfont: { color: '#8b9ab8', size: 10 },
                    title: { text: 'Control', font: { color: '#8b9ab8' } },
                  },
                }]}
                layout={{
                  paper_bgcolor: 'transparent',
                  plot_bgcolor:  '#1a2235',
                  margin: { t: 10, b: 40, l: 40, r: 10 },
                  xaxis: { title: 'x (m)', color: '#8b9ab8', gridcolor: '#2a3550', zeroline: false },
                  yaxis: { title: 'y (m)', color: '#8b9ab8', gridcolor: '#2a3550', zeroline: false },
                  shapes: [
                    { type: 'rect', x0: -52.5, y0: -34, x1: 52.5, y1: 34,
                      line: { color: 'rgba(255,255,255,0.3)', width: 1 }, fillcolor: 'transparent' },
                    { type: 'line', x0: 0, y0: -34, x1: 0, y1: 34,
                      line: { color: 'rgba(255,255,255,0.2)', width: 1 } },
                  ],
                  font: { family: 'Inter, sans-serif' },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%', height: 300 }}
              />
            </div>
          )}
        </div>

        {/* Per-frame control percentages */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon blue">📈</span>
            Control % Over Time
          </div>
          <Plot
            data={[
              {
                x:    frames.map((_: any, i: number) => i),
                y:    frames.map((f: any) => f.home_control_pct),
                name: 'Home',
                type: 'scatter', mode: 'lines',
                line: { color: 'var(--accent-blue)', width: 2 },
                fill: 'tozeroy',
                fillcolor: 'rgba(61,158,255,0.1)',
              },
              {
                x:    frames.map((_: any, i: number) => i),
                y:    frames.map((f: any) => f.away_control_pct),
                name: 'Away',
                type: 'scatter', mode: 'lines',
                line: { color: 'var(--accent-red)', width: 2 },
                fill: 'tozeroy',
                fillcolor: 'rgba(233,69,96,0.1)',
              },
            ]}
            layout={{
              paper_bgcolor: 'transparent',
              plot_bgcolor: '#1a2235',
              margin: { t: 10, b: 40, l: 50, r: 10 },
              xaxis: { title: 'Frame', color: '#8b9ab8', gridcolor: '#2a3550' },
              yaxis: { title: 'Control %', color: '#8b9ab8', gridcolor: '#2a3550', range: [0, 100] },
              legend: { font: { color: '#8b9ab8' }, bgcolor: 'transparent' },
              font: { family: 'Inter' },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: 300 }}
          />
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.25rem', padding: '1rem' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', lineHeight: 1.6 }}>
          <strong style={{ color: 'var(--text-primary)' }}>Model:</strong> Spearman (2018) Beyond Expected Goals.
          PPCF = P(Attacking team controls cell) computed via numerical integration of player arrival
          probabilities over a {frames[0]?.xgrid?.length ?? 50}×{frames[0]?.ygrid?.length ?? 32} grid.
          Green = home dominance, red = away dominance.
        </p>
      </div>
    </div>
  )
}

function EmptyState({ msg }: { msg: string }) {
  return (
    <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
      🗺 {msg}
    </div>
  )
}
