interface Props { data: any }

export function InsightsView({ data }: Props) {
  if (!data) return (
    <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
      🤖 No AI insights available
    </div>
  )

  const { key_insights = [], tactical_summary = '', player_highlights = [], match_narrative = '' } = data

  return (
    <div>
      {/* Key Insights */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="card-header">
          <span className="card-icon green">💡</span> Key Insights
        </div>
        <div className="insights-list">
          {key_insights.map((insight: string, i: number) => (
            <div key={i} className="insight-item" style={{ animationDelay: `${i * 0.07}s` }}>
              <div className="insight-dot" />
              <span>{insight}</span>
            </div>
          ))}
          {!key_insights.length && (
            <div style={{ color: 'var(--text-secondary)' }}>No insights generated</div>
          )}
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
        {/* Tactical Summary */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon blue">🧠</span> Tactical Summary
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.7 }}>
            {tactical_summary || 'Analysis pending.'}
          </p>
        </div>

        {/* Player Highlights */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon gold">🏆</span> Player Highlights
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {player_highlights.map((h: string, i: number) => (
              <div key={i} style={{
                padding: '0.65rem 0.875rem',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.83rem',
                fontFamily: 'monospace',
                color: 'var(--accent-green)',
                lineHeight: 1.55,
              }}>
                {h}
              </div>
            ))}
            {!player_highlights.length && (
              <div style={{ color: 'var(--text-secondary)' }}>No highlights generated</div>
            )}
          </div>
        </div>
      </div>

      {/* Match Narrative */}
      {match_narrative && (
        <div className="card">
          <div className="card-header">
            <span className="card-icon red">📝</span> Match Narrative
          </div>
          <p style={{
            color: 'var(--text-primary)',
            fontSize: '0.92rem',
            lineHeight: 1.8,
            fontStyle: 'italic',
            borderLeft: '3px solid var(--accent-green)',
            paddingLeft: '1rem',
          }}>
            "{match_narrative}"
          </p>
        </div>
      )}

      {/* Attribution */}
      <div className="card" style={{ marginTop: '1.25rem', padding: '1rem' }}>
        <div className="card-header" style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>
          <span className="card-icon blue">📚</span> Attribution & Methodology
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--text-primary)' }}>Pitch Control:</strong> Spearman, W. (2018). "Beyond Expected Goals." MIT Sloan Sports Analytics Conference. Reused from sreekar-voleti/Tracking-PitchControl (MIT).{' '}
          <strong style={{ color: 'var(--text-primary)' }}>Passing Network:</strong> Llana, Sergio & Shaw, Laurie — Friends-of-Tracking-Data-FoTD/passing-networks-in-python (MIT).{' '}
          <strong style={{ color: 'var(--text-primary)' }}>Tactical Metrics:</strong> Monteiro, Tiago — DataKnight1/football-match-intelligence (MIT).{' '}
          <strong style={{ color: 'var(--text-primary)' }}>Player Influence Score:</strong> Composite PIS = 0.4 × PageRank + 0.3 × Betweenness + 0.3 × Spatial Dominance (original contribution).
        </p>
      </div>
    </div>
  )
}
