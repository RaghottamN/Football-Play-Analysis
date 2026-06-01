"""
Player Influence Scorer
=======================
NEW module — no equivalent in any source repository.

Computes the composite Player Influence Score (PIS):

  PIS = w_pr × PageRank + w_bt × Betweenness + w_sp × Spatial_Dominance

Default weights (configurable via API):
  w_pr = 0.4,  w_bt = 0.3,  w_sp = 0.3

All component scores are normalised to [0, 1] before combination.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from loguru import logger

from config import settings


class InfluenceScorer:
    """
    NEW class — computes Player Influence Score (PIS).

    Combines:
      - Network metrics (PageRank, Betweenness) from PassingNetworkService
      - Spatial Dominance from PitchControlService
    """

    def __init__(
        self,
        w_pagerank:    float = settings.PIS_WEIGHT_PAGERANK,
        w_betweenness: float = settings.PIS_WEIGHT_BETWEENNESS,
        w_spatial:     float = settings.PIS_WEIGHT_SPATIAL,
    ):
        assert abs(w_pagerank + w_betweenness + w_spatial - 1.0) < 1e-6, \
            "Weights must sum to 1.0"
        self.w_pr = w_pagerank
        self.w_bt = w_betweenness
        self.w_sp = w_spatial

    # ── Main Scoring ──────────────────────────────────────────────────────────

    def compute(
        self,
        centrality: Dict[str, Dict[str, float]],
        spatial_dominance: Dict[str, float],
        team: str = 'home',
    ) -> List[Dict]:
        """
        Compute PIS for all players on a team.

        Args:
            centrality: output of compute_centrality_metrics() — all metric dicts
            spatial_dominance: {player_id: float (0–1)} — fraction of pitch dominated
            team: 'home' or 'away'

        Returns:
            List of player influence records, sorted descending by PIS:
            [{
              'player_id':          str,
              'team':               str,
              'pagerank':           float,
              'betweenness':        float,
              'spatial_dominance':  float,
              'pis':                float,
              'rank':               int,
            }]
        """
        pagerank    = centrality.get('pagerank',               {})
        betweenness = centrality.get('betweenness_centrality', {})

        all_players = set(pagerank) | set(betweenness) | set(spatial_dominance)
        if not all_players:
            return []

        # Normalise each component to [0, 1]
        pr_norm  = self._normalise(pagerank)
        bt_norm  = self._normalise(betweenness)
        sp_norm  = self._normalise(spatial_dominance)

        records = []
        for pid in all_players:
            pr  = pr_norm.get(pid, 0.0)
            bt  = bt_norm.get(pid, 0.0)
            sp  = sp_norm.get(pid, 0.0)
            pis = round(self.w_pr * pr + self.w_bt * bt + self.w_sp * sp, 4)

            records.append({
                'player_id':         str(pid),
                'team':              team,
                'pagerank':          round(pagerank.get(pid, 0.0), 4),
                'betweenness':       round(betweenness.get(pid, 0.0), 4),
                'spatial_dominance': round(spatial_dominance.get(pid, 0.0), 4),
                'pagerank_norm':     round(pr, 4),
                'betweenness_norm':  round(bt, 4),
                'spatial_norm':      round(sp, 4),
                'pis':               pis,
            })

        records.sort(key=lambda x: x['pis'], reverse=True)
        for rank, rec in enumerate(records, start=1):
            rec['rank'] = rank

        return records

    def compute_both_teams(
        self,
        centrality_home: Dict,
        centrality_away: Dict,
        spatial_home: Dict[str, float],
        spatial_away: Dict[str, float],
    ) -> Dict[str, List[Dict]]:
        """Compute PIS for both teams and return combined result."""
        return {
            'home': self.compute(centrality_home, spatial_home, team='home'),
            'away': self.compute(centrality_away, spatial_away, team='away'),
        }

    # ── Spatial Dominance from Pitch Control ──────────────────────────────────

    @staticmethod
    def spatial_dominance_from_pc(
        pitch_control_frames: List[Dict],
        tracking_frames: List[Dict],
        team: str = 'home',
    ) -> Dict[str, float]:
        """
        Estimate per-player spatial dominance from pitch control data.
        NEW function — not in any source repository.

        Heuristic: player dominates cells within their Voronoi region
        when the team's PPCF > 0.5 in that region.

        Returns: {player_id: spatial_dominance_fraction}
        """
        if not pitch_control_frames or not tracking_frames:
            return {}

        player_scores: Dict[str, float] = {}
        player_counts: Dict[str, int]   = {}
        ppcf_key = 'ppcf_home' if team == 'home' else 'ppcf_away'
        player_team_key = 'home_players' if team == 'home' else 'away_players'

        for pc_result, track_frame in zip(pitch_control_frames, tracking_frames):
            if ppcf_key not in pc_result:
                continue

            ppcf = np.array(pc_result[ppcf_key])
            xgrid = np.array(pc_result.get('xgrid', []))
            ygrid = np.array(pc_result.get('ygrid', []))

            if len(xgrid) == 0 or len(ygrid) == 0:
                continue

            players = track_frame.get(player_team_key, [])
            if not players:
                continue

            # For each player, count grid cells dominated and within Voronoi region
            player_positions = np.array([[p.get('x', 0), p.get('y', 0)] for p in players])
            player_ids       = [str(p.get('player_id', p.get('track_id', i)))
                                for i, p in enumerate(players)]

            # Build Voronoi grid assignment
            for (i, y) in enumerate(ygrid):
                for (j, x) in enumerate(xgrid):
                    cell = np.array([x, y])
                    dists = np.linalg.norm(player_positions - cell, axis=1)
                    nearest_idx = int(np.argmin(dists))
                    pid = player_ids[nearest_idx]

                    if pid not in player_scores:
                        player_scores[pid] = 0.0
                        player_counts[pid] = 0

                    player_counts[pid] += 1
                    if ppcf[i, j] > 0.5:
                        player_scores[pid] += float(ppcf[i, j])

        # Normalise: fraction of cells dominated (weighted by PPCF)
        total_cells = sum(player_counts.values()) or 1
        result = {
            pid: round(player_scores.get(pid, 0) / total_cells, 4)
            for pid in player_counts
        }
        return result

    # ── Insight Generation ────────────────────────────────────────────────────

    def generate_insights(
        self,
        rankings: List[Dict],
        team: str = 'home',
    ) -> List[str]:
        """
        Generate natural language insight sentences for top players.
        NEW function — not in any source repository.
        """
        insights = []
        if not rankings:
            return ["No player data available for this team."]

        top3 = rankings[:3]
        for rec in top3:
            pid  = rec['player_id']
            pis  = rec['pis']
            pr   = rec['pagerank']
            bt   = rec['betweenness']
            sp   = rec['spatial_dominance']
            rank = rec['rank']

            # Determine dominant contribution
            contributions = {'PageRank': pr, 'Betweenness': bt, 'Spatial': sp}
            dominant = max(contributions, key=contributions.get)

            if rank == 1:
                insights.append(
                    f"Player {pid} had the highest influence score ({pis:.3f}) "
                    f"with strongest contribution from {dominant} centrality, "
                    f"controlling {sp * 100:.1f}% of team-dominated territory."
                )
            else:
                insights.append(
                    f"Player {pid} (rank #{rank}, PIS={pis:.3f}) "
                    f"showed elevated {dominant.lower()} — "
                    f"a key link in the team's build-up pattern."
                )

        return insights

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(values: Dict[str, float]) -> Dict[str, float]:
        """Min-max normalise a dict of floats to [0, 1]."""
        if not values:
            return {}
        v = list(values.values())
        mn, mx = min(v), max(v)
        rng = mx - mn
        if rng < 1e-9:
            return {k: 0.5 for k in values}
        return {k: (val - mn) / rng for k, val in values.items()}
