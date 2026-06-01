import Plot from 'react-plotly.js'

interface Props { data: any }

export function TacticsView({ data }: Props) {
  if (!data) return <Empty />

  const ft   = data.field_tilt        || { home: 50, away: 50 }
  const wing = data.wing_attacks       || {}
  const hp   = data.high_press         || {}
  const cp   = data.central_progression || {}
  const ovrlds = data.overloaded_zones  || []
  const sc   = data.space_creation     || {}
  const tri  = data.passing_triangles  || {}

  return (
    <div>
      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>

        {/* Field Tilt */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon green">⚖</span> Field Tilt (Territorial Dominance)
          </div>
          <Plot
            data={[{
              type: 'indicator', mode: 'gauge+number',
              value: ft.home,
              title: { text: 'Home % in Opp Half', font: { color: '#8b9ab8', size: 12 } },
              gauge: {
                axis: { range: [0, 100], tickfont: { color: '#8b9ab8' } },
                bar:  { color: 'var(--accent-blue)' },
                bgcolor: '#1a2235',
                threshold: { line: { color: 'var(--accent-green)', width: 2 }, value: 50 },
              },
              number: { suffix: '%', font: { color: 'var(--accent-blue)' } },
            }] as any}
            layout={{
              paper_bgcolor: 'transparent', margin: { t: 30, b: 10, l: 20, r: 20 },
              height: 200, font: { family: 'Inter' },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: '-0.5rem' }}>
            Away field tilt: <strong style={{ color: 'var(--accent-red)' }}>{ft.away?.toFixed(1)}%</strong>
          </div>
        </div>

        {/* Wing Attacks */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon blue">🏃</span> Attack Channel Distribution
          </div>
          <Plot
            data={[{
              type: 'pie',
              labels: ['Left Flank', 'Center', 'Right Flank'],
              values: [wing.left_flank_pct || 33, wing.center_pct || 33, wing.right_flank_pct || 33],
              marker: { colors: ['var(--accent-green)', 'var(--accent-blue)', 'var(--accent-gold)'] },
              textinfo: 'percent+label',
              textfont: { color: '#ffffff', size: 11 },
              hole: 0.4,
            }] as any}
            layout={{
              paper_bgcolor: 'transparent', margin: { t: 10, b: 10, l: 10, r: 10 },
              height: 220, showlegend: false, font: { family: 'Inter' },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '1.25rem' }}>
        {[
          { label: 'High Press %', value: `${hp.high_press_pct?.toFixed(1)}%`, icon: '⚡', color: 'var(--accent-red)' },
          { label: 'Progressive Passes', value: cp.progressive_passes || 0, icon: '➡', color: 'var(--accent-green)' },
          { label: 'Central Prog. %', value: `${cp.central_pct?.toFixed(1)}%`, icon: '🎯', color: 'var(--accent-blue)' },
          { label: 'Zone Overloads', value: ovrlds.length, icon: '📍', color: 'var(--accent-gold)' },
          { label: 'Passing Triangles (H)', value: tri.home || 0, icon: '△', color: 'var(--accent-green)' },
          { label: 'Passing Triangles (A)', value: tri.away || 0, icon: '△', color: 'var(--accent-red)' },
        ].map(m => (
          <div key={m.label} className="metric-badge">
            <div style={{ fontSize: '1.6rem', marginBottom: '0.3rem' }}>{m.icon}</div>
            <div className="metric-value" style={{ fontSize: '1.5rem', color: m.color }}>{m.value}</div>
            <div className="metric-label">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Overloaded Zones */}
      {ovrlds.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-icon gold">📍</span> Overloaded Zones
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Zone</th><th>Dominant Team</th><th>Avg Advantage</th><th>Home</th><th>Away</th></tr>
            </thead>
            <tbody>
              {ovrlds.map((o: any, i: number) => (
                <tr key={i}>
                  <td style={{ textTransform: 'capitalize' }}>{o.zone?.replace(/_/g, ' ')}</td>
                  <td><span style={{ color: o.dominant === 'home' ? 'var(--accent-blue)' : 'var(--accent-red)',
                                      fontWeight: 600 }}>
                    {o.dominant?.toUpperCase()}
                  </span></td>
                  <td>{o.advantage?.toFixed(1)}</td>
                  <td>{o.home_count}</td>
                  <td>{o.away_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Empty() {
  return <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>🧠 No tactical data available</div>
}
