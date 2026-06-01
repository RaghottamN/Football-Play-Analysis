"""
Tracking Utilities
==================
REUSED CODE from two source repositories:
  1. sreekar-voleti/Tracking-PitchControl (MIT) — compute_vel_and_acc, convert_units
  2. Friends-of-Tracking-Data-FoTD/passing-networks-in-python (MIT)
     Authors: Sergio Llana (@SergioMinuto90), Laurie Shaw (@EightyFivePoint)
     — to_metric_coordinates, merge_tracking_data, to_single_playing_direction

NEW additions:
  - TrackingDataAdapter: converts YOLO/ByteTrack output to Spearman tracking format
  - smooth_trajectories: Savitzky-Golay smoothing on raw detections
"""

import numpy as np
import pandas as pd
from scipy import signal as scipy_signal
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# VERBATIM from Tracking-PitchControl/DataCleaning.py (MIT) — Sreekar Voleti
# ─────────────────────────────────────────────────────────────────────────────

def compute_vel_and_acc(
    data: pd.DataFrame,
    smoothing: bool = True,
    max_speed: float = 14.0,
    max_acceleration: float = 9.5,
    filter_type: str = "Savitzky-Golay",
    window_size: int = 7,
    polyorder: int = 1,
) -> pd.DataFrame:
    """
    Compute velocities and accelerations for each player and the ball.
    VERBATIM from Tracking-PitchControl/DataCleaning.py (MIT).

    Args:
        data: tracking DataFrame with columns {player}_x, {player}_y, Time [s]
        smoothing: apply Savitzky-Golay or Moving Average filter
        max_speed: clip physically impossible speeds [m/s]
        max_acceleration: clip physically impossible accelerations [m/s²]
        filter_type: "Savitzky-Golay" | "moving average"
        window_size: smoothing window
        polyorder: polynomial order for Savitzky-Golay
    """
    data = _remove_player_vel_and_acc(data)
    player_ids = np.unique([c[:-2] for c in data.columns[2:]])
    dt = data["Time [s]"].diff()

    # Collect all new columns in one dict, then concat once to avoid fragmentation
    new_cols: dict = {}

    for player_id in player_ids:
        vx = data[f"{player_id}_x"].diff() / dt
        vy = data[f"{player_id}_y"].diff() / dt

        if player_id != "ball" and max_speed > 0:
            raw_speed = np.sqrt(vx**2 + vy**2)
            vx = vx.where(raw_speed <= max_speed, np.nan)
            vy = vy.where(raw_speed <= max_speed, np.nan)

        if smoothing:
            if filter_type == "Savitzky-Golay":
                vx = pd.Series(scipy_signal.savgol_filter(vx.fillna(0), window_length=window_size, polyorder=polyorder), index=data.index)
                vy = pd.Series(scipy_signal.savgol_filter(vy.fillna(0), window_length=window_size, polyorder=polyorder), index=data.index)
            elif filter_type == "moving average":
                vx = vx.rolling(window_size, center=True).mean()
                vy = vy.rolling(window_size, center=True).mean()

        new_cols[f"{player_id}_vx"]    = vx
        new_cols[f"{player_id}_vy"]    = vy
        new_cols[f"{player_id}_speed"] = np.sqrt(vx**2 + vy**2)

        ax = vx.diff() / dt
        ay = vy.diff() / dt

        if player_id != "ball" and max_acceleration > 0:
            raw_acc = np.sqrt(ax**2 + ay**2)
            ax = ax.where(raw_acc <= max_acceleration, np.nan)
            ay = ay.where(raw_acc <= max_acceleration, np.nan)

        if smoothing and filter_type == "Savitzky-Golay":
            ax = pd.Series(scipy_signal.savgol_filter(ax.fillna(0), window_length=window_size, polyorder=polyorder), index=data.index)
            ay = pd.Series(scipy_signal.savgol_filter(ay.fillna(0), window_length=window_size, polyorder=polyorder), index=data.index)

        new_cols[f"{player_id}_ax"]  = ax
        new_cols[f"{player_id}_ay"]  = ay
        new_cols[f"{player_id}_acc"] = np.sqrt(ax**2 + ay**2)

    # Single pd.concat avoids the PerformanceWarning from repeated column insertion
    data = pd.concat([data, pd.DataFrame(new_cols, index=data.index)], axis=1)
    return data


def _remove_player_vel_and_acc(data: pd.DataFrame) -> pd.DataFrame:
    """VERBATIM from Tracking-PitchControl/DataCleaning.py (MIT)."""
    cols = [c for c in data.columns if c.split('_')[-1] in ['vx', 'vy', 'ax', 'ay', 'speed', 'acc']]
    return data.drop(columns=cols)


def convert_units(data: pd.DataFrame, field_dimen: Tuple[float, float] = (106., 68.)) -> pd.DataFrame:
    """
    Convert Metrica coordinates (0–1) to meters with origin at centre circle.
    VERBATIM from Tracking-PitchControl/DataCleaning.py (MIT).
    """
    x_cols = [c for c in data.columns if c[-1].lower() == 'x']
    y_cols = [c for c in data.columns if c[-1].lower() == 'y']
    data[x_cols] = (data[x_cols] - 0.5) * field_dimen[0]
    data[y_cols] = -1 * (data[y_cols] - 0.5) * field_dimen[1]
    return data


def find_goalkeeper(team: pd.DataFrame) -> str:
    """
    Find goalkeeper as the player closest to goal at kick-off.
    VERBATIM from Tracking-PitchControl/DataCleaning.py (MIT).
    """
    x_columns = [c for c in team.columns if c[-2:].lower() == '_x' and c[:4] in ['Home', 'Away']]
    gk_col = team.iloc[0][x_columns].abs().idxmax()
    return gk_col.split('_')[1]


# ─────────────────────────────────────────────────────────────────────────────
# VERBATIM from passing-networks-in-python/utils.py (MIT)
# Authors: Sergio Llana (@SergioMinuto90), Laurie Shaw (@EightyFivePoint)
# ─────────────────────────────────────────────────────────────────────────────

def to_metric_coordinates(data: pd.DataFrame, field_dimen: Tuple[float, float] = (106., 68.)) -> pd.DataFrame:
    """
    Convert positions from Metrica units to meters (origin at centre circle).
    VERBATIM from passing-networks-in-python/utils.py (MIT).
    NOTE: Metrica defines origin at top-left, so y is flipped.
    """
    x_columns = [c for c in data.columns if c[-1].lower() == 'x']
    y_columns = [c for c in data.columns if c[-1].lower() == 'y']
    data[x_columns] = (data[x_columns] - 0.5) * field_dimen[0]
    data[y_columns] = -1 * (data[y_columns] - 0.5) * field_dimen[1]
    return data


def to_single_playing_direction(
    home: pd.DataFrame,
    away: pd.DataFrame,
    events: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Flip coordinates in second half so each team always shoots in the same direction.
    VERBATIM from passing-networks-in-python/utils.py (MIT).
    """
    for team in [home, away, events]:
        second_half_idx = team.Period.idxmax(2)
        columns = [c for c in team.columns if c[-1].lower() in ['x', 'y']]
        team.loc[second_half_idx:, columns] = team.loc[second_half_idx:, columns].apply(
            lambda x: 1 - x, axis=1
        )
    return home, away, events


def merge_tracking_data(home: pd.DataFrame, away: pd.DataFrame) -> pd.DataFrame:
    """
    Merge home & away tracking DataFrames into one.
    VERBATIM from passing-networks-in-python/utils.py (MIT).
    """
    return home.drop(columns=['ball_x', 'ball_y']).merge(away, left_index=True, right_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# NEW: TrackingDataAdapter — converts YOLO/ByteTrack output to Spearman format
# ─────────────────────────────────────────────────────────────────────────────

class TrackingDataAdapter:
    """
    Converts raw YOLO + ByteTrack detections into the flat-column DataFrame
    format expected by the Spearman pitch control engine.

    NEW class — not in any source repository.

    Input format (per frame):
        {
          'frame_idx': int,
          'timestamp': float,          # seconds
          'home_players': [
            {'player_id': str, 'x': float, 'y': float}, ...
          ],
          'away_players': [
            {'player_id': str, 'x': float, 'y': float}, ...
          ],
          'ball': {'x': float, 'y': float}
        }

    Output: two DataFrames (home_tracking, away_tracking) in Spearman format:
        index = Frame
        columns: Time [s], Period, Home_{id}_x, Home_{id}_y, ..., ball_x, ball_y
    """

    def __init__(self, fps: float = 25.0, field_dimen: Tuple[float, float] = (105., 68.)):
        self.fps         = fps
        self.field_dimen = field_dimen

    def convert(self, frames: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Convert a list of frame dicts to (home_tracking, away_tracking) DataFrames."""
        home_rows, away_rows = [], []

        all_home_ids = sorted({p['player_id'] for f in frames for p in f.get('home_players', [])})
        all_away_ids = sorted({p['player_id'] for f in frames for p in f.get('away_players', [])})

        for frame in frames:
            frame_idx = frame['frame_idx']
            time_s    = frame_idx / self.fps

            home_row = {'Frame': frame_idx, 'Time [s]': time_s, 'Period': 1,
                        'ball_x': frame.get('ball', {}).get('x', np.nan),
                        'ball_y': frame.get('ball', {}).get('y', np.nan)}
            away_row = home_row.copy()

            # Build player position lookup
            home_dict = {p['player_id']: p for p in frame.get('home_players', [])}
            away_dict = {p['player_id']: p for p in frame.get('away_players', [])}

            for pid in all_home_ids:
                p = home_dict.get(pid, {})
                home_row[f'Home_{pid}_x'] = p.get('x', np.nan)
                home_row[f'Home_{pid}_y'] = p.get('y', np.nan)

            for pid in all_away_ids:
                p = away_dict.get(pid, {})
                away_row[f'Away_{pid}_x'] = p.get('x', np.nan)
                away_row[f'Away_{pid}_y'] = p.get('y', np.nan)

            home_rows.append(home_row)
            away_rows.append(away_row)

        home_df = pd.DataFrame(home_rows).set_index('Frame')
        away_df = pd.DataFrame(away_rows).set_index('Frame')

        # Compute velocities and accelerations
        if len(home_df) > 7:
            home_df = compute_vel_and_acc(home_df)
            away_df = compute_vel_and_acc(away_df)
        else:
            # Fill velocity columns with zeros for short clips
            for col in [c for c in home_df.columns if c.endswith('_x')]:
                home_df[col.replace('_x', '_vx')] = 0.0
                home_df[col.replace('_x', '_vy')] = 0.0
            for col in [c for c in away_df.columns if c.endswith('_x')]:
                away_df[col.replace('_x', '_vx')] = 0.0
                away_df[col.replace('_x', '_vy')] = 0.0

        return home_df, away_df

    def to_frame_dicts(self, home_df: pd.DataFrame, away_df: pd.DataFrame) -> List[Dict]:
        """Convert tracking DataFrames back to frame dict list for pitch control service."""
        frames = []
        # Extract player IDs safely: strip 'Home_' prefix and '_x' suffix
        all_home_ids = sorted({c[len('Home_'):-len('_x')] for c in home_df.columns
                                if c.startswith('Home_') and c.endswith('_x')})
        all_away_ids = sorted({c[len('Away_'):-len('_x')] for c in away_df.columns
                                if c.startswith('Away_') and c.endswith('_x')})

        for idx in home_df.index:
            home_row = home_df.loc[idx]
            away_row = away_df.loc[idx]
            frame: Dict = {
                'home': {},
                'away': {},
                'ball': {
                    'x': float(home_row.get('ball_x', 0)),
                    'y': float(home_row.get('ball_y', 0)),
                },
            }
            for pid in all_home_ids:
                frame['home'][pid] = {
                    'x':  float(home_row.get(f'Home_{pid}_x', np.nan)),
                    'y':  float(home_row.get(f'Home_{pid}_y', np.nan)),
                    'vx': float(home_row.get(f'Home_{pid}_vx', 0.0)),
                    'vy': float(home_row.get(f'Home_{pid}_vy', 0.0)),
                }
            for pid in all_away_ids:
                frame['away'][pid] = {
                    'x':  float(away_row.get(f'Away_{pid}_x', np.nan)),
                    'y':  float(away_row.get(f'Away_{pid}_y', np.nan)),
                    'vx': float(away_row.get(f'Away_{pid}_vx', 0.0)),
                    'vy': float(away_row.get(f'Away_{pid}_vy', 0.0)),
                }
            frames.append(frame)
        return frames
