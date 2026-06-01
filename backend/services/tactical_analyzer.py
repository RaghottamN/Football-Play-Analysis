"""
Tactical Analyzer Service
=========================
**REUSED CODE** — Core tactical metric functions taken verbatim from:
  DataKnight1/football-match-intelligence (MIT License)
  Original author: Tiago Monteiro (21-12-2025)

Reused functions (verbatim):
  - calculate_pitch_control_simplified()
  - calculate_pressing_intensity()
  - calculate_field_tilt()
  - calculate_ppda()
  - calculate_high_press_triggers()
  - calculate_penetration_index()
  - calculate_pass_availability()
  - find_player_encounters()

New additions:
  - TacticalAnalyzer service class
  - detect_tactical_patterns() — overload zones, triangles, wing attacks, etc.
"""

from typing import Tuple, Dict, List, Any, Optional
from scipy.spatial import distance
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# VERBATIM from football-match-intelligence/src/metrics/tactical.py (MIT)
# Original author: Tiago Monteiro
# ─────────────────────────────────────────────────────────────────────────────

def calculate_pitch_control_simplified(
    attacking_positions: np.ndarray,
    defending_positions: np.ndarray,
    pitch_length: float = 105,
    pitch_width: float = 68,
    grid_size: int = 20
) -> np.ndarray:
    """
    Calculate simplified pitch control using Voronoi-based approach.
    VERBATIM from football-match-intelligence (MIT).
    """
    x = np.linspace(-pitch_length / 2, pitch_length / 2, grid_size)
    y = np.linspace(-pitch_width / 2, pitch_width / 2, grid_size)
    X, Y = np.meshgrid(x, y)
    grid_points = np.column_stack([X.ravel(), Y.ravel()])

    attack_distances = distance.cdist(grid_points, attacking_positions)
    defend_distances = distance.cdist(grid_points, defending_positions)

    min_attack_dist = np.min(attack_distances, axis=1)
    min_defend_dist = np.min(defend_distances, axis=1)

    control = (min_attack_dist < min_defend_dist).astype(float)
    return control.reshape(X.shape)


def calculate_pressing_intensity(
    defending_positions: np.ndarray,
    ball_position: Tuple[float, float],
    radius: float = 10.0
) -> Dict[str, Any]:
    """
    Calculate pressing intensity around the ball.
    VERBATIM from football-match-intelligence (MIT).
    """
    ball_pos = np.array(ball_position)
    distances = np.linalg.norm(defending_positions - ball_pos, axis=1)
    pressers = distances <= radius
    return {
        'n_pressers':           int(np.sum(pressers)),
        'avg_distance':         float(np.mean(distances)),
        'min_distance':         float(np.min(distances)),
        'pressers_within_5m':   int(np.sum(distances <= 5.0)),
        'pressers_within_10m':  int(np.sum(distances <= 10.0)),
    }


def calculate_pass_availability(
    passer_position: Tuple[float, float],
    teammate_positions: np.ndarray,
    opponent_positions: np.ndarray,
    max_distance: float = 30.0
) -> pd.DataFrame:
    """
    Calculate passing options with interception risk.
    VERBATIM from football-match-intelligence (MIT).
    """
    passer_pos = np.array(passer_position)
    results = []
    for i, teammate_pos in enumerate(teammate_positions):
        pass_distance = np.linalg.norm(teammate_pos - passer_pos)
        if pass_distance > max_distance or pass_distance < 1.0:
            continue
        pass_vector   = teammate_pos - passer_pos
        pass_length   = np.linalg.norm(pass_vector)
        pass_direction = pass_vector / pass_length
        risk_count = 0
        min_opponent_dist = float('inf')
        for opp_pos in opponent_positions:
            to_opp     = opp_pos - passer_pos
            projection = np.dot(to_opp, pass_direction)
            if 0 < projection < pass_length:
                perp_dist = np.linalg.norm(to_opp - projection * pass_direction)
                if perp_dist < 5.0:
                    risk_count += 1
                min_opponent_dist = min(min_opponent_dist, perp_dist)
        results.append({
            'teammate_idx':        i,
            'distance':            float(pass_distance),
            'risk_count':          risk_count,
            'min_opponent_distance': float(min_opponent_dist) if min_opponent_dist != float('inf') else -1,
            'angle':               float(np.degrees(np.arctan2(pass_vector[1], pass_vector[0]))),
        })
    return pd.DataFrame(results)


def calculate_high_press_triggers(
    events_df: pd.DataFrame,
    pressure_events: Optional[pd.DataFrame] = None,
    height_threshold: float = 35.0
) -> pd.DataFrame:
    """
    Identify high press trigger events.
    VERBATIM from football-match-intelligence (MIT).
    """
    if pressure_events is None:
        pressure_events = events_df[events_df['event_type'] == 'on_ball_engagement'].copy()
    triggers = pressure_events[pressure_events['start_x'] > height_threshold].copy()
    return triggers


def calculate_ppda(
    defensive_actions: pd.DataFrame,
    opponent_passes: pd.DataFrame,
    attacking_third_x: float = 35.0
) -> float:
    """
    Calculate PPDA (Passes Allowed Per Defensive Action).
    VERBATIM from football-match-intelligence (MIT).
    """
    def_actions_attacking = defensive_actions[defensive_actions['start_x'] > attacking_third_x]
    passes_attacking      = opponent_passes[opponent_passes['start_x'] > attacking_third_x]
    n_defensive_actions   = len(def_actions_attacking)
    n_passes              = len(passes_attacking)
    if n_defensive_actions == 0:
        return float('inf')
    return n_passes / n_defensive_actions


def calculate_penetration_index(
    team_positions: np.ndarray,
    ball_position: Tuple[float, float],
    opponent_defensive_line: float
) -> float:
    """
    Calculate how penetrative team's position is.
    VERBATIM from football-match-intelligence (MIT).
    """
    ball_x = ball_position[0]
    players_ahead    = np.sum(team_positions[:, 0] > opponent_defensive_line)
    total_players    = len(team_positions)
    ball_penetration = max(0, (ball_x - opponent_defensive_line) / 52.5)
    player_penetration = players_ahead / total_players
    penetration_index = 0.6 * ball_penetration + 0.4 * player_penetration
    return float(np.clip(penetration_index, 0, 1))


def find_player_encounters(
    player1_df: pd.DataFrame,
    player2_df: pd.DataFrame,
    distance_threshold: float = 5.0
) -> pd.DataFrame:
    """
    Find frames where two players are within a distance threshold.
    VERBATIM from football-match-intelligence (MIT).
    """
    merged_df = pd.merge(player1_df, player2_df, on='frame', suffixes=('_p1', '_p2'))
    merged_df['distance'] = np.sqrt(
        (merged_df['x_p1'] - merged_df['x_p2'])**2 +
        (merged_df['y_p1'] - merged_df['y_p2'])**2
    )
    return merged_df[merged_df['distance'] <= distance_threshold].copy()


def calculate_field_tilt(
    tracking_df: pd.DataFrame,
    team_id: int,
    pitch_length: float = 105.0
) -> Dict[str, float]:
    """
    Calculate territory dominance (field tilt) for a team.
    VERBATIM from football-match-intelligence (MIT).
    """
    if tracking_df.empty:
        return {'percentage': 0.0, 'frames_in_opp_half': 0, 'total_frames': 0}
    team_data = tracking_df[tracking_df['team_id'] == team_id] if 'team_id' in tracking_df.columns else tracking_df
    if team_data.empty:
        return {'percentage': 0.0, 'frames_in_opp_half': 0, 'total_frames': 0}
    if 'frame' in team_data.columns and 'x' in team_data.columns:
        centroids = team_data.groupby('frame')['x'].mean()
        min_x     = team_data['x'].min()
        midline   = 0.0 if min_x < 0 else pitch_length / 2.0
        frames_in_opp_half = (centroids > midline).sum()
        total_frames       = len(centroids)
        percentage = (frames_in_opp_half / total_frames * 100) if total_frames > 0 else 0.0
        return {
            'percentage':         float(percentage),
            'frames_in_opp_half': int(frames_in_opp_half),
            'total_frames':       int(total_frames),
        }
    return {'percentage': 0.0, 'frames_in_opp_half': 0, 'total_frames': 0}


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Tactical pattern detection (not in original repos)
# ─────────────────────────────────────────────────────────────────────────────

class TacticalAnalyzer:
    """
    High-level tactical pattern detection service.
    Wraps reused metric functions and adds pattern detection logic.
    NEW class — not in any source repository.
    """

    PITCH_LENGTH = 105.0
    PITCH_WIDTH  = 68.0
    ZONE_THIRDS  = PITCH_LENGTH / 3  # ~35m per third

    def analyze(
        self,
        events_df: pd.DataFrame,
        tracking_frames: List[Dict],
        home_team_id: int = 0,
        away_team_id: int = 1,
    ) -> Dict[str, Any]:
        """Run full tactical analysis and return structured insights."""
        insights: Dict[str, Any] = {}

        # Field tilt
        if not tracking_frames:
            insights['field_tilt'] = {'home': 50.0, 'away': 50.0}
        else:
            df = self._frames_to_df(tracking_frames)
            home_tilt = calculate_field_tilt(df, home_team_id, self.PITCH_LENGTH)
            away_tilt = calculate_field_tilt(df, away_team_id, self.PITCH_LENGTH)
            insights['field_tilt'] = {
                'home': round(home_tilt['percentage'], 1),
                'away': round(away_tilt['percentage'], 1),
            }

        # Zone overloads
        insights['overloaded_zones']   = self._detect_overloads(tracking_frames)
        # Passing triangles
        insights['passing_triangles']  = self._detect_triangles(events_df)
        # Wing attacks
        insights['wing_attacks']       = self._detect_wing_attacks(events_df)
        # Central progression
        insights['central_progression'] = self._detect_central_progression(events_df)
        # High press
        insights['high_press']         = self._detect_high_press(tracking_frames, events_df)
        # Space creation
        insights['space_creation']     = self._detect_space_creation(tracking_frames)

        return insights

    # ── Pattern Detectors ────────────────────────────────────────────────────

    def _detect_overloads(self, frames: List[Dict]) -> List[Dict]:
        """Detect zones where one team has numeric advantage ≥ 2."""
        zones = ['left_flank', 'center', 'right_flank']
        overloads = []
        for zone_idx, zone in enumerate(zones):
            home_counts, away_counts = [], []
            for frame in frames[:50]:  # sample first 50 frames
                home_pos = np.array([[p['x'], p['y']] for p in frame.get('home_players', [])])
                away_pos = np.array([[p['x'], p['y']] for p in frame.get('away_players', [])])
                if len(home_pos) == 0 or len(away_pos) == 0:
                    continue
                y_min = -self.PITCH_WIDTH / 2 + zone_idx * self.PITCH_WIDTH / 3
                y_max = y_min + self.PITCH_WIDTH / 3
                home_in_zone = np.sum((home_pos[:, 1] >= y_min) & (home_pos[:, 1] < y_max))
                away_in_zone = np.sum((away_pos[:, 1] >= y_min) & (away_pos[:, 1] < y_max))
                home_counts.append(home_in_zone)
                away_counts.append(away_in_zone)
            if home_counts and away_counts:
                avg_home = np.mean(home_counts)
                avg_away = np.mean(away_counts)
                if abs(avg_home - avg_away) >= 1.5:
                    overloads.append({
                        'zone':        zone,
                        'dominant':    'home' if avg_home > avg_away else 'away',
                        'advantage':   round(abs(avg_home - avg_away), 1),
                        'home_count':  round(float(avg_home), 1),
                        'away_count':  round(float(avg_away), 1),
                    })
        return overloads

    def _detect_triangles(self, events_df: pd.DataFrame) -> Dict[str, int]:
        """Count passing triangle occurrences (A→B→C→A sequences)."""
        if events_df.empty or 'from_player' not in events_df.columns:
            return {'home': 0, 'away': 0}
        triangles = {'home': 0, 'away': 0}
        for team in ['home', 'away']:
            team_passes = events_df[events_df['team'] == team] if 'team' in events_df.columns else events_df
            if 'from_player' in team_passes.columns and 'to_player' in team_passes.columns and len(team_passes) > 0:
                # Simple triangle detection: check for 3-pass cycles
                pass_pairs = set(zip(team_passes['from_player'].astype(str), team_passes['to_player'].astype(str)))
                count = 0
                for (a, b) in pass_pairs:
                    for (b2, c) in pass_pairs:
                        if b2 == b and (c, a) in pass_pairs and c != a:
                            count += 1
                triangles[team] = count // 3  # each triangle counted 3 times
        return triangles

    def _detect_wing_attacks(self, events_df: pd.DataFrame) -> Dict[str, float]:
        """Percentage of attacks through left/right flanks vs center."""
        if events_df.empty or 'start_x' not in events_df.columns:
            return {'left_flank_pct': 33.3, 'center_pct': 33.3, 'right_flank_pct': 33.3}
        passes = events_df[events_df['event_type'] == 'pass'] if 'event_type' in events_df.columns else events_df
        if passes.empty:
            return {'left_flank_pct': 33.3, 'center_pct': 33.3, 'right_flank_pct': 33.3}
        total  = len(passes)
        y_vals = passes['start_y'] if 'start_y' in passes.columns else pd.Series([0.0] * total)
        left   = int((y_vals < -self.PITCH_WIDTH / 3).sum())
        right  = int((y_vals >  self.PITCH_WIDTH / 3).sum())
        center = total - left - right
        return {
            'left_flank_pct':  round(left  / total * 100, 1) if total else 33.3,
            'center_pct':      round(center / total * 100, 1) if total else 33.3,
            'right_flank_pct': round(right  / total * 100, 1) if total else 33.3,
        }

    def _detect_central_progression(self, events_df: pd.DataFrame) -> Dict[str, Any]:
        """Detect progressive passes through the center channel."""
        if events_df.empty or 'start_x' not in events_df.columns:
            return {'progressive_passes': 0, 'central_pct': 0.0}
        passes = events_df.copy()
        if 'end_x' not in passes.columns:
            return {'progressive_passes': 0, 'central_pct': 0.0}
        passes['is_progressive'] = passes['end_x'] - passes['start_x'] > 10.0
        passes['is_central']     = (passes['start_y'].abs() < self.PITCH_WIDTH / 3) if 'start_y' in passes.columns else False
        progressive = passes['is_progressive'].sum()
        central_progressive = (passes['is_progressive'] & passes['is_central']).sum()
        return {
            'progressive_passes': int(progressive),
            'central_pct':        round(central_progressive / progressive * 100, 1) if progressive else 0.0,
        }

    def _detect_high_press(self, frames: List[Dict], events_df: pd.DataFrame) -> Dict[str, Any]:
        """Detect high press indicators from positional data."""
        high_press_frames = 0
        for frame in frames[:100]:
            away_pos = np.array([[p['x'], p['y']] for p in frame.get('away_players', [])])
            ball_pos = frame.get('ball', {})
            if len(away_pos) > 0 and ball_pos:
                ball = (ball_pos.get('x', 0), ball_pos.get('y', 0))
                pi   = calculate_pressing_intensity(away_pos, ball, radius=15.0)
                if pi['n_pressers'] >= 3 and ball[0] < -15:  # press in defensive half
                    high_press_frames += 1
        total = len(frames[:100])
        return {
            'high_press_pct':   round(high_press_frames / total * 100, 1) if total else 0.0,
            'high_press_frames': high_press_frames,
        }

    def _detect_space_creation(self, frames: List[Dict]) -> Dict[str, Any]:
        """Detect runs creating space behind defensive line."""
        space_events = 0
        for frame in frames[:100]:
            home_pos = np.array([[p['x'], p['y']] for p in frame.get('home_players', [])])
            away_pos = np.array([[p['x'], p['y']] for p in frame.get('away_players', [])])
            if len(home_pos) == 0 or len(away_pos) == 0:
                continue
            def_line = np.mean(away_pos[:, 0])  # avg x of defenders
            ahead    = np.sum(home_pos[:, 0] > def_line + 5)
            if ahead >= 2:
                space_events += 1
        total = len(frames[:100])
        return {
            'space_behind_defense_pct': round(space_events / total * 100, 1) if total else 0.0,
        }

    @staticmethod
    def _frames_to_df(frames: List[Dict]) -> pd.DataFrame:
        """Convert list of frame dicts to a flat DataFrame."""
        rows = []
        for i, frame in enumerate(frames):
            for p in frame.get('home_players', []):
                rows.append({'frame': i, 'team_id': 0, 'x': p.get('x', 0), 'y': p.get('y', 0)})
            for p in frame.get('away_players', []):
                rows.append({'frame': i, 'team_id': 1, 'x': p.get('x', 0), 'y': p.get('y', 0)})
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['frame', 'team_id', 'x', 'y'])
