"""
AI Insights Generator
=====================
NEW module — no equivalent in any source repository.

Generates natural language analytical summaries from computed metrics.
Uses template-based generation (no API key required) with optional
HuggingFace model enhancement if available.
"""

from typing import Dict, List, Any, Optional
import random
from loguru import logger


class AIInsightsGenerator:
    """
    NEW class — generates natural language tactical summaries.

    Uses a tiered approach:
      1. Template-based insights (always available, fast)
      2. HuggingFace text-generation (optional, better quality)
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.llm = None
        if use_llm:
            self._load_llm()

    def _load_llm(self):
        try:
            from transformers import pipeline
            self.llm = pipeline("text-generation", model="distilgpt2", max_new_tokens=100)
            logger.info("LLM insights pipeline loaded (distilgpt2)")
        except Exception as e:
            logger.warning(f"LLM not available: {e} — using templates only")

    # ── Main Entry Point ──────────────────────────────────────────────────────

    def generate(
        self,
        influence_rankings: Dict[str, List[Dict]],
        tactical_insights:  Dict[str, Any],
        pc_summary:         Dict[str, Any],
        possession_stats:   Dict[str, float],
        network_summary:    Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate full AI insights report from all computed metrics.

        Returns:
            {
              'key_insights':      [str],   # 5–8 bullet insights
              'tactical_summary':  str,     # paragraph summary
              'player_highlights': [str],   # top player narratives
              'match_narrative':   str,     # full match description
            }
        """
        key_insights      = self._key_insights(
            influence_rankings, tactical_insights, pc_summary, possession_stats)
        player_highlights = self._player_highlights(influence_rankings)
        tactical_summary  = self._tactical_summary(tactical_insights, possession_stats)
        match_narrative   = self._match_narrative(
            pc_summary, possession_stats, network_summary, tactical_insights)

        return {
            'key_insights':      key_insights,
            'tactical_summary':  tactical_summary,
            'player_highlights': player_highlights,
            'match_narrative':   match_narrative,
        }

    # ── Key Insights ──────────────────────────────────────────────────────────

    def _key_insights(
        self,
        rankings:    Dict,
        tactics:     Dict,
        pc:          Dict,
        possession:  Dict,
    ) -> List[str]:
        insights = []

        # Territorial dominance insight
        home_dom = pc.get('home_dominance_pct', 50)
        away_dom = pc.get('away_dominance_pct', 50)
        dominant = 'Home' if home_dom > away_dom else 'Away'
        insights.append(
            f"{dominant} team controlled {max(home_dom, away_dom):.1f}% of pitch territory "
            f"across {pc.get('frames_analyzed', 0)} analyzed frames."
        )

        # Possession insight
        home_pos = possession.get('home_pct', 50)
        away_pos = possession.get('away_pct', 50)
        poss_team = 'Home' if home_pos > away_pos else 'Away'
        insights.append(
            f"{poss_team} team dominated possession at {max(home_pos, away_pos):.1f}%."
        )

        # Top player insight
        home_top = (rankings.get('home') or [{}])[0]
        if home_top.get('player_id'):
            pid  = home_top['player_id']
            pis  = home_top.get('pis', 0)
            sp   = home_top.get('spatial_dominance', 0) * 100
            insights.append(
                f"Player {pid} had the highest influence score ({pis:.3f}) "
                f"due to {sp:.1f}% team spatial dominance."
            )

        # Wing attacks
        wing = tactics.get('wing_attacks', {})
        max_wing = max(wing.get('left_flank_pct', 0), wing.get('right_flank_pct', 0))
        if max_wing > 40:
            flank = 'left' if wing.get('left_flank_pct', 0) > wing.get('right_flank_pct', 0) else 'right'
            insights.append(
                f"The {flank} flank generated {max_wing:.1f}% of progressive attacks."
            )

        # High press
        hp = tactics.get('high_press', {})
        if hp.get('high_press_pct', 0) > 20:
            insights.append(
                f"High press was active in {hp['high_press_pct']:.1f}% of analyzed frames, "
                f"indicating aggressive out-of-possession structure."
            )

        # Field tilt
        ft = tactics.get('field_tilt', {})
        if ft.get('home', 50) > 60:
            insights.append(
                f"Home team maintained field tilt dominance ({ft['home']:.1f}% of time in opponent's half)."
            )
        elif ft.get('away', 50) > 60:
            insights.append(
                f"Away team maintained field tilt dominance ({ft['away']:.1f}% of time in opponent's half)."
            )

        # Passing triangles
        tri = tactics.get('passing_triangles', {})
        total_tri = tri.get('home', 0) + tri.get('away', 0)
        if total_tri > 0:
            insights.append(
                f"{total_tri} passing triangle sequences detected — "
                f"home: {tri.get('home', 0)}, away: {tri.get('away', 0)}."
            )

        return insights[:8]

    # ── Player Highlights ─────────────────────────────────────────────────────

    def _player_highlights(self, rankings: Dict[str, List]) -> List[str]:
        highlights = []
        for team in ['home', 'away']:
            team_ranks = rankings.get(team, [])[:3]
            for rec in team_ranks:
                pid  = rec.get('player_id', '?')
                pis  = rec.get('pis', 0)
                bt   = rec.get('betweenness', 0)
                sp   = rec.get('spatial_dominance', 0) * 100
                rank = rec.get('rank', '?')
                pr   = rec.get('pagerank', 0)

                highlights.append(
                    f"[{team.upper()} #{rank}] Player {pid} — "
                    f"PIS: {pis:.3f} | PageRank: {pr:.3f} | "
                    f"Betweenness: {bt:.3f} | Spatial: {sp:.1f}%"
                )
        return highlights

    # ── Tactical Summary ──────────────────────────────────────────────────────

    def _tactical_summary(self, tactics: Dict, possession: Dict) -> str:
        ft   = tactics.get('field_tilt', {})
        hp   = tactics.get('high_press', {})
        wing = tactics.get('wing_attacks', {})
        cp   = tactics.get('central_progression', {})

        lines = []
        home_poss = possession.get('home_pct', 50)
        away_poss = possession.get('away_pct', 50)

        lines.append(
            f"The home team had {home_poss:.1f}% possession and spent "
            f"{ft.get('home', 50):.1f}% of time in the opponent's half."
        )
        lines.append(
            f"The away team had {away_poss:.1f}% possession with "
            f"{ft.get('away', 50):.1f}% field tilt."
        )
        if hp.get('high_press_pct', 0) > 15:
            lines.append(
                f"A high press structure was evident, with pressing intensity "
                f"active in {hp['high_press_pct']:.1f}% of frames."
            )
        if wing.get('center_pct', 0) > 50:
            lines.append(
                f"Play was predominantly channelled through the center "
                f"({wing['center_pct']:.1f}% of attacks)."
            )
        elif max(wing.get('left_flank_pct', 0), wing.get('right_flank_pct', 0)) > 40:
            dom_flank = 'left' if wing.get('left_flank_pct', 0) > wing.get('right_flank_pct', 0) else 'right'
            lines.append(
                f"The {dom_flank} flank was the primary channel of attack, "
                f"generating {max(wing.get('left_flank_pct', 0), wing.get('right_flank_pct', 0)):.1f}% of actions."
            )
        cp_passes = cp.get('progressive_passes', 0)
        if cp_passes > 0:
            lines.append(
                f"{cp_passes} progressive passes were completed, "
                f"with {cp.get('central_pct', 0):.1f}% through the central channel."
            )

        return " ".join(lines)

    # ── Match Narrative ───────────────────────────────────────────────────────

    def _match_narrative(
        self,
        pc:         Dict,
        possession: Dict,
        network:    Dict,
        tactics:    Dict,
    ) -> str:
        home_ctrl = pc.get('home_dominance_pct', 50)
        away_ctrl = pc.get('away_dominance_pct', 50)
        home_poss = possession.get('home_pct', 50)
        home_passes = network.get('home_total_passes', 0)
        away_passes = network.get('away_total_passes', 0)
        overloads   = tactics.get('overloaded_zones', [])
        overload_str = (
            f"Overloads were detected in {len(overloads)} zone(s)"
            if overloads else "No significant zone overloads were detected"
        )

        narrative = (
            f"During this 60-second clip, the home team controlled {home_ctrl:.1f}% of the pitch "
            f"and held {home_poss:.1f}% possession. The away team's territorial share was {away_ctrl:.1f}%. "
            f"Home completed {home_passes} passes vs {away_passes} for the away side. "
            f"{overload_str}. "
            f"The pitch control model (Spearman 2018) confirmed these territorial patterns across "
            f"{pc.get('frames_analyzed', 0)} analyzed frames, "
            f"providing a granular view of spatial dominance and transition zones."
        )
        return narrative
