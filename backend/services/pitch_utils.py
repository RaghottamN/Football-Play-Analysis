"""
Pitch Zone Utilities
====================
REUSED CODE from:
  DataKnight1/football-match-intelligence (MIT License)
  Original author: Tiago Monteiro (21-12-2025)

Reused verbatim:
  - pitch_dimensions()
  - get_pitch_zone()

NEW additions:
  - zone_grid_labels() — full pitch zone map for heatmap annotation
  - compute_zone_stats() — per-zone possession/pressure aggregation
"""

from typing import Tuple, Union, Dict, List
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# VERBATIM from football-match-intelligence/src/utils/pitch.py (MIT)
# Original author: Tiago Monteiro
# ─────────────────────────────────────────────────────────────────────────────

def pitch_dimensions(pitch_type: str = "skillcorner") -> Tuple[float, float]:
    """
    Get pitch dimensions in meters.
    VERBATIM from football-match-intelligence (MIT).
    """
    dimensions = {
        "skillcorner": (105, 68),
        "standard":    (105, 68),
        "opta":        (100, 100),
        "wyscout":     (100, 100),
        "statsbomb":   (120, 80),
    }
    return dimensions.get(pitch_type, (105, 68))


def get_pitch_zone(
    x: Union[float, np.ndarray],
    y: Union[float, np.ndarray],
    pitch_length: float = 105,
    pitch_width: float  = 68,
) -> Union[str, np.ndarray]:
    """
    Determine pitch zone from coordinates (origin at centre circle).
    VERBATIM from football-match-intelligence/src/utils/pitch.py (MIT).

    Returns zone string like: "attacking_third_center_channel"
    """
    third         = pitch_length / 3
    channel_width = pitch_width  / 3

    if np.isscalar(x):
        long_zone = ("defensive_third" if x < -third else
                     "attacking_third" if x > third  else "middle_third")
        lat_zone  = ("left_channel"    if y < -channel_width else
                     "right_channel"   if y >  channel_width  else "center_channel")
        return f"{long_zone}_{lat_zone}"
    else:
        long_zone = np.where(x < -third, "defensive_third",
                    np.where(x >  third, "attacking_third", "middle_third"))
        lat_zone  = np.where(y < -channel_width, "left_channel",
                    np.where(y >  channel_width,  "right_channel",  "center_channel"))
        return np.char.add(np.char.add(long_zone, "_"), lat_zone)


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Zone statistics (not in original repos)
# ─────────────────────────────────────────────────────────────────────────────

ALL_ZONES = [
    "defensive_third_left_channel",   "defensive_third_center_channel",   "defensive_third_right_channel",
    "middle_third_left_channel",      "middle_third_center_channel",       "middle_third_right_channel",
    "attacking_third_left_channel",   "attacking_third_center_channel",    "attacking_third_right_channel",
]


def compute_zone_stats(
    player_positions: List[Dict],  # [{'x': float, 'y': float, 'team': str}, ...]
    pitch_length: float = 105.0,
    pitch_width:  float = 68.0,
) -> Dict[str, Dict]:
    """
    Compute per-zone player counts for both teams.
    NEW function — not in any source repository.

    Returns:
        {
          'defensive_third_left_channel': {'home': 1, 'away': 2},
          ...
        }
    """
    stats: Dict[str, Dict] = {z: {'home': 0, 'away': 0} for z in ALL_ZONES}

    for p in player_positions:
        x, y, team = p.get('x', 0.0), p.get('y', 0.0), p.get('team', 'home')
        zone = get_pitch_zone(x, y, pitch_length, pitch_width)
        if zone in stats:
            stats[zone][team] = stats[zone].get(team, 0) + 1

    return stats


def zone_overload_summary(zone_stats: Dict[str, Dict]) -> List[Dict]:
    """
    Summarise zones where one team has a numeric advantage ≥ 2.
    NEW function — not in any source repository.
    """
    overloads = []
    for zone, counts in zone_stats.items():
        home = counts.get('home', 0)
        away = counts.get('away', 0)
        diff = abs(home - away)
        if diff >= 2:
            overloads.append({
                'zone':      zone,
                'dominant':  'home' if home > away else 'away',
                'advantage': diff,
                'home_count': home,
                'away_count': away,
            })
    return sorted(overloads, key=lambda x: x['advantage'], reverse=True)
