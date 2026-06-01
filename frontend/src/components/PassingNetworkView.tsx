import Plot from 'react-plotly.js'

interface Props { data: any }

export function PassingNetworkView({ data }: Props) {
  if (!data) return <Empty msg="No passing network data" />

  const renderTeam = (team: string, teamData: any, color: string) => {
    const nodes = teamData?.nodes || []
    const edges = teamData?.edges || []

    if (!nodes.length) return (
      <div className="card">
        <div className="card-header">
          <span className="card-icon" style={{ background: `${color}22`, color }}>{team === 'home' ? '🔵' : '🔴'}</span>
          {team.charAt(0).toUpperCase() + team.slice(1)} Team Network
        </div>
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>
          No pass data detected for this team
        </div>
      </div>
    )

    const maxPasses   = Math.max(...nodes.map((n: any) => n.passes || 1), 1)
    const maxBetween  = Math.max(...nodes.map((n: any) => n.betweenness || 0.01), 0.01)

    // Build Plotly network traces
    const edgeX: number[] = [], edgeY: number[] = []
    edges.forEach((e: any) => {
      const src = nodes.find((n: any) => n.id === e.source)
      const dst = nodes.find((n: any) => n.id === e.target)
      if (src && dst) {
        edgeX.push(src.x, dst.x, null as any)
        edgeY.push(src.y, dst.y, null as any)
      }
    })

    return (
      <div className="card">
        <div className="card-header">
          <span className="card-icon" style={{ background: `${color}22`, color }}>
            {team === 'home' ? '🔵' : '🔴'}
          </span>
          {team.charAt(0).toUpperCase() + team.slice(1)} Team — Passing Network
        </div>
        <div className="plot-container">
          <Plot
            data={[
              // Edges
              {
                x: edgeX, y: edgeY,
                mode: 'lines',
                line: { color: `${color}55`, width: 1.5 },
                hoverinfo: 'none',
                showlegend: false,
              } as any,
              // Nodes
              {
                x:    nodes.map((n: any) => n.x),
                y:    nodes.map((n: any) => n.y),
                mode: 'markers+text',
                marker: {
                  size:  nodes.map((n: any) => 12 + (n.passes / maxPasses) * 28),
                  color: nodes.map((n: any) => n.betweenness / maxBetween),
                  colorscale: [[0, '#1a2235'], [0.5, color], [1, '#ffffff']],
                  line: { color: color, width: 2 },
                  showscale: true,
                  colorbar: { title: 'Betweenness', tickfont: { color: '#8b9ab8', size: 9 },
                               titlefont: { color: '#8b9ab8', size: 10 } },
                },
                text:     nodes.map((n: any) => n.label || n.id),
                textfont: { color: '#ffffff', size: 10 },
                textposition: 'top center',
                customdata: nodes.map((n: any) => [
                  n.passes, n.pagerank?.toFixed(3), n.betweenness?.toFixed(3)
                ]),
                hovertemplate: '<b>%{text}</b><br>Passes: %{customdata[0]}<br>PageRank: %{customdata[1]}<br>Betweenness: %{customdata[2]}<extra></extra>',
                name: 'Players',
              } as any,
            ]}
            layout={{
              paper_bgcolor: 'transparent',
              plot_bgcolor:  '#1a2235',
              margin: { t: 10, b: 40, l: 40, r: 60 },
              xaxis: { title: 'x (m)', color: '#8b9ab8', gridcolor: '#2a3550', zeroline: false },
              yaxis: { title: 'y (m)', color: '#8b9ab8', gridcolor: '#2a3550', zeroline: false,
                       scaleanchor: 'x', scaleratio: 1 },
              font: { family: 'Inter' },
              showlegend: false,
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: 360 }}
          />
        </div>

        {/* Centrality table */}
        {nodes.length > 0 && (
          <div style={{ marginTop: '1rem', overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Passes</th>
                  <th>PageRank</th>
                  <th>Betweenness</th>
                  <th>Degree</th>
                </tr>
              </thead>
              <tbody>
                {[...nodes].sort((a: any, b: any) => b.pagerank - a.pagerank).slice(0, 8).map((n: any) => (
                  <tr key={n.id}>
                    <td style={{ fontWeight: 600 }}>{n.label || n.id}</td>
                    <td>{n.passes}</td>
                    <td style={{ color }}>{n.pagerank?.toFixed(3)}</td>
                    <td>{n.betweenness?.toFixed(3)}</td>
                    <td>{n.degree?.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <div className="grid-2">
        {renderTeam('home', data.home, 'var(--accent-blue)')}
        {renderTeam('away', data.away, 'var(--accent-red)')}
      </div>

      {/* Summary */}
      <div className="card" style={{ marginTop: '1.25rem' }}>
        <div className="card-header">
          <span className="card-icon blue">📊</span> Network Summary
        </div>
        <div className="metric-grid">
          {[
            { v: data.summary?.home_total_passes || 0, l: 'Home Total Passes' },
            { v: data.summary?.away_total_passes || 0, l: 'Away Total Passes' },
            { v: data.summary?.home_players      || 0, l: 'Home Players Tracked' },
            { v: data.summary?.away_players      || 0, l: 'Away Players Tracked' },
          ].map(m => (
            <div key={m.l} className="metric-badge">
              <div className="metric-value">{m.v}</div>
              <div className="metric-label">{m.l}</div>
            </div>
          ))}
        </div>
        <p style={{ marginTop: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
          Node size = pass count · Node color = betweenness centrality · Edges = pass connections (min 1 pass)
        </p>
      </div>
    </div>
  )
}

function Empty({ msg }: { msg: string }) {
  return <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>🕸 {msg}</div>
}
