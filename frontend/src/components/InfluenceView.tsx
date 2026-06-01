import Plot from 'react-plotly.js'

interface Props { data: any }

export function InfluenceView({ data }: Props) {
  if (!data) return <Empty />

  const rankBadgeClass = (r: number) =>
    r === 1 ? 'rank-badge gold' : r === 2 ? 'rank-badge silver' : r === 3 ? 'rank-badge bronze' : 'rank-badge other'

  const renderTeam = (team: string, players: any[], color: string) => {
    if (!players?.length) return null
    return (
      <div className="card">
        <div className="card-header">
          <span className="card-icon" style={{ background: `${color}22`, color }}>
            {team === 'home' ? '🔵' : '🔴'}
          </span>
          {team.charAt(0).toUpperCase() + team.slice(1)} — Player Influence Rankings
        </div>

        {/* Bar chart */}
        <div className="plot-container" style={{ marginBottom: '1rem' }}>
          <Plot
            data={[
              {
                x:    players.slice(0, 10).map((p: any) => `P${p.player_id}`),
                y:    players.slice(0, 10).map((p: any) => p.pis),
                name: 'PIS',
                type: 'bar',
                marker: {
                  color: players.slice(0, 10).map((p: any) => p.pis),
                  colorscale: [[0, '#1a2235'], [1, color]],
                  line: { color: color, width: 1 },
                },
              } as any,
            ]}
            layout={{
              paper_bgcolor: 'transparent',
              plot_bgcolor:  '#1a2235',
              margin: { t: 10, b: 40, l: 50, r: 10 },
              xaxis: { color: '#8b9ab8', gridcolor: '#2a3550' },
              yaxis: { color: '#8b9ab8', gridcolor: '#2a3550', title: 'PIS Score', range: [0, 1] },
              font:  { family: 'Inter' },
              showlegend: false,
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: 220 }}
          />
        </div>

        {/* Stacked component chart */}
        <div className="plot-container" style={{ marginBottom: '1rem' }}>
          <Plot
            data={[
              {
                x:    players.slice(0, 8).map((p: any) => `P${p.player_id}`),
                y:    players.slice(0, 8).map((p: any) => p.pagerank_norm || p.pagerank),
                name: 'PageRank (norm)',
                type: 'bar', marker: { color: 'rgba(0,230,118,0.7)' },
              } as any,
              {
                x:    players.slice(0, 8).map((p: any) => `P${p.player_id}`),
                y:    players.slice(0, 8).map((p: any) => p.betweenness_norm || p.betweenness),
                name: 'Betweenness (norm)',
                type: 'bar', marker: { color: 'rgba(61,158,255,0.7)' },
              } as any,
              {
                x:    players.slice(0, 8).map((p: any) => `P${p.player_id}`),
                y:    players.slice(0, 8).map((p: any) => p.spatial_norm || p.spatial_dominance),
                name: 'Spatial (norm)',
                type: 'bar', marker: { color: 'rgba(255,215,0,0.7)' },
              } as any,
            ]}
            layout={{
              barmode: 'stack',
              paper_bgcolor: 'transparent',
              plot_bgcolor: '#1a2235',
              margin: { t: 10, b: 40, l: 50, r: 10 },
              xaxis: { color: '#8b9ab8' },
              yaxis: { color: '#8b9ab8', title: 'Normalized Score', gridcolor: '#2a3550' },
              legend: { font: { color: '#8b9ab8', size: 10 }, bgcolor: 'transparent' },
              font: { family: 'Inter' },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: 220 }}
          />
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Player</th>
                <th>PIS</th>
                <th>PageRank</th>
                <th>Betweenness</th>
                <th>Spatial %</th>
              </tr>
            </thead>
            <tbody>
              {players.slice(0, 11).map((p: any) => (
                <tr key={p.player_id}>
                  <td><span className={rankBadgeClass(p.rank)}>{p.rank}</span></td>
                  <td style={{ fontWeight: 600 }}>Player {p.player_id}</td>
                  <td style={{ color, fontWeight: 700 }}>{p.pis?.toFixed(3)}</td>
                  <td>{p.pagerank?.toFixed(3)}</td>
                  <td>{p.betweenness?.toFixed(3)}</td>
                  <td>{((p.spatial_dominance || 0) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: '1.25rem', padding: '1rem 1.25rem' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.6 }}>
          <strong style={{ color: 'var(--text-primary)' }}>PIS Formula:</strong>{' '}
          PIS = 0.4 × PageRank + 0.3 × Betweenness Centrality + 0.3 × Spatial Dominance.
          All components normalized to [0, 1]. Weights are configurable at upload time.
        </p>
      </div>
      <div className="grid-2">
        {renderTeam('home', data.home, 'var(--accent-blue)')}
        {renderTeam('away', data.away, 'var(--accent-red)')}
      </div>
    </div>
  )
}

function Empty() {
  return <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>🏆 No influence data available</div>
}
