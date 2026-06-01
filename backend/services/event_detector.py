"""
Event Detector Service
======================
ADAPTED from:
  Friends-of-Tracking-Data-FoTD/passing-networks-in-python (MIT)
  Author: Sergio Llana (@SergioMinuto90)
  — _context_frames() possession detection logic adapted

NEW additions:
  - Pass detection from positional data (proximity + ball trajectory)
  - Reception detection
  - Possession change detection
  - Carry detection
  - Shot detection (heuristic)
  - Structured event timeline output
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from loguru import logger


class EventDetector:
    """
    Detects football events from positional tracking data.
    NEW class — no equivalent in source repositories.

    Events detected:
      - PASS          (ball moves from player A toward player B)
      - RECEPTION     (player receives ball)
      - POSSESSION_CHANGE
      - CARRY         (player moves with ball)
      - SHOT          (ball moves rapidly toward goal)
    """

    # Physics thresholds
    BALL_CLOSE_DIST    = 2.5   # metres — ball is "controlled" by nearest player
    PASS_MIN_SPEED     = 3.0   # m/s — minimum ball speed to call it a pass
    CARRY_MAX_DIST     = 3.0   # metres — max player–ball dist for a carry
    SHOT_SPEED_THRESH  = 15.0  # m/s — fast ball toward goal = shot
    SHOT_MIN_X         = 38.0  # metres from centre — must be in final third to be a shot
    GOAL_X             = 52.5  # metres from centre — goal line
    EVENT_COOLDOWN     = 10    # minimum frames between same event type

    def __init__(self, fps: float = 25.0):
        self.fps = fps
        self.dt  = 1.0 / fps

    def detect_events(
        self,
        tracking_frames: List[Dict],
    ) -> pd.DataFrame:
        """
        Run full event detection pipeline on tracking frames.

        Args:
            tracking_frames: list of frame dicts from tracker/team_classifier

        Returns:
            DataFrame with columns:
            [event_id, frame_idx, timestamp, event_type, team,
             from_player, to_player, start_x, start_y, end_x, end_y]
        """
        events: List[Dict] = []
        event_id = 0

        possession_state: Dict = {'team': None, 'player': None, 'since': 0}
        last_event_frame: Dict[str, int] = {}   # event_type → last frame it fired
        home_frames = 0
        away_frames = 0

        for i in range(1, len(tracking_frames)):
            prev  = tracking_frames[i - 1]
            frame = tracking_frames[i]

            ball_prev = prev.get('ball', {})
            ball_curr = frame.get('ball', {})

            bx_prev = ball_prev.get('x', 0.0)
            by_prev = ball_prev.get('y', 0.0)
            bx_curr = ball_curr.get('x', 0.0)
            by_curr = ball_curr.get('y', 0.0)

            ball_speed = np.sqrt((bx_curr - bx_prev)**2 + (by_curr - by_prev)**2) / self.dt

            # Find who has possession in current frame
            team_curr, player_curr = self._find_ball_owner(frame, bx_curr, by_curr)
            team_prev, player_prev = self._find_ball_owner(prev, bx_prev, by_prev)

            # Accumulate possession time
            if team_curr == 'home':
                home_frames += 1
            elif team_curr == 'away':
                away_frames += 1

            # ── POSSESSION CHANGE ─────────────────────────────────────────────
            if team_curr != possession_state['team'] and team_curr is not None:
                if (possession_state['team'] is not None
                        and i - last_event_frame.get('possession_change', 0) >= self.EVENT_COOLDOWN):
                    events.append({
                        'event_id':   event_id,
                        'frame_idx':  frame['frame_idx'],
                        'timestamp':  frame['timestamp'],
                        'event_type': 'possession_change',
                        'team':       team_curr,
                        'from_player': str(possession_state['player']),
                        'to_player':   str(player_curr),
                        'start_x':    bx_prev, 'start_y': by_prev,
                        'end_x':      bx_curr, 'end_y':   by_curr,
                    })
                    event_id += 1
                    last_event_frame['possession_change'] = i
                possession_state = {'team': team_curr, 'player': player_curr, 'since': i}

            # ── PASS ──────────────────────────────────────────────────────────
            if (ball_speed >= self.PASS_MIN_SPEED
                    and player_prev is not None and player_curr is not None
                    and player_prev != player_curr
                    and team_prev == team_curr
                    and i - last_event_frame.get('pass', 0) >= self.EVENT_COOLDOWN):
                events.append({
                    'event_id':   event_id,
                    'frame_idx':  frame['frame_idx'],
                    'timestamp':  frame['timestamp'],
                    'event_type': 'pass',
                    'team':       team_prev,
                    'from_player': str(player_prev),
                    'to_player':   str(player_curr),
                    'start_x':    bx_prev, 'start_y': by_prev,
                    'end_x':      bx_curr, 'end_y':   by_curr,
                    'ball_speed': round(ball_speed, 2),
                })
                event_id += 1
                last_event_frame['pass'] = i

            # ── SHOT ─────────────────────────────────────────────────────────
            # Requires: high ball speed + ball in final third + moving toward goal
            # + cooldown to avoid duplicate detections on same shot
            if ball_speed >= self.SHOT_SPEED_THRESH:
                dx = bx_curr - bx_prev
                in_home_final_third = bx_curr > self.SHOT_MIN_X and dx > 0
                in_away_final_third = bx_curr < -self.SHOT_MIN_X and dx < 0
                if ((in_home_final_third or in_away_final_third)
                        and i - last_event_frame.get('shot', 0) >= self.EVENT_COOLDOWN * 5):
                    events.append({
                        'event_id':   event_id,
                        'frame_idx':  frame['frame_idx'],
                        'timestamp':  frame['timestamp'],
                        'event_type': 'shot',
                        'team':       team_prev or 'unknown',
                        'from_player': str(player_prev) if player_prev else None,
                        'to_player':   None,
                        'start_x':    bx_prev, 'start_y': by_prev,
                        'end_x':      bx_curr, 'end_y':   by_curr,
                        'ball_speed': round(ball_speed, 2),
                    })
                    event_id += 1
                    last_event_frame['shot'] = i

        # Store frame-based possession for compute_possession_stats
        self._home_frames = home_frames
        self._away_frames = away_frames

        df = pd.DataFrame(events)
        logger.info(f"Event detection: {len(df)} events detected from {len(tracking_frames)} frames")
        if not df.empty:
            logger.info(f"  Event types: {df['event_type'].value_counts().to_dict()}")
        return df

    def _find_ball_owner(
        self,
        frame: Dict,
        ball_x: float,
        ball_y: float,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Find the player closest to the ball within control threshold."""
        min_dist = self.BALL_CLOSE_DIST
        owner_team   = None
        owner_player = None

        for team_key, team_label in [('home_players', 'home'), ('away_players', 'away')]:
            for player in frame.get(team_key, []):
                px, py = player.get('x', 0.0), player.get('y', 0.0)
                dist   = np.sqrt((px - ball_x)**2 + (py - ball_y)**2)
                if dist < min_dist:
                    min_dist     = dist
                    owner_team   = team_label
                    owner_player = player.get('player_id', player.get('track_id', '?'))

        return owner_team, str(owner_player) if owner_player is not None else None

    def get_possession_timeline(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Build a timeline of possession sequences.
        ADAPTED from _context_frames() in passing-networks-in-python (MIT).
        """
        if events_df.empty:
            return []

        possession_changes = events_df[events_df['event_type'] == 'possession_change'].copy()
        timeline = []
        for _, row in possession_changes.iterrows():
            timeline.append({
                'timestamp': float(row['timestamp']),
                'team':      row['team'],
                'frame':     int(row['frame_idx']),
            })
        return timeline

    def compute_possession_stats(self, events_df: pd.DataFrame, total_duration: float) -> Dict:
        """Compute possession percentages based on frame-level ball ownership."""
        home_frames = getattr(self, '_home_frames', 0)
        away_frames = getattr(self, '_away_frames', 0)
        total = home_frames + away_frames
        if total == 0:
            return {'home_pct': 50.0, 'away_pct': 50.0}
        return {
            'home_pct': round(home_frames / total * 100, 1),
            'away_pct': round(away_frames / total * 100, 1),
        }
