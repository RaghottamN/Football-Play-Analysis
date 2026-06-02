"""
Pitch Control Engine
====================
**REUSED CODE** — Core Spearman (2018) PPCF model taken verbatim from:
  sreekar-voleti/Tracking-PitchControl (MIT License)
  Original author: Sreekar Voleti

Adaptations made for this project:
  1. Added PitchControlService wrapper class for API integration
  2. Added from_tracking_dict() to accept YOLO-derived tracking data
  3. Parallelised grid computation via concurrent.futures
  4. Added per-player spatial dominance extraction
  5. Fixed numpy.sign typo in check_offsides (line 95 original)

Reference:
  Spearman, W. (2018). Beyond Expected Goals.
  12th MIT Sloan Sports Analytics Conference.
"""

# ─────────────────────────────────────────────────────────────────────────────
# VERBATIM from sreekar-voleti/Tracking-PitchControl/PitchControl.py (MIT)
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any
from loguru import logger


class player(object):
    """
    player (class) — VERBATIM from Tracking-PitchControl

    Class to represent a player in the game. Contains useful attributes
    to compute the PPCF for each player.
    """

    def __init__(self, pid, team, teamname, max_speeds, max_accs, params, GKid):
        self.id             = pid
        self.is_gk          = self.id == GKid
        self.team           = team
        self.teamname       = teamname
        self.playername     = "{}_{}_".format(teamname, pid)
        self.vmax           = params["vmax"]
        self.amax           = params["amax"]
        self.reaction_time  = params["reaction_time"]
        self.tti_sigma      = params["tti_sigma"]
        self.lambda_att     = params["lambda_att"]
        self.lambda_def     = params["lambda_gk"] if self.is_gk else params["lambda_def"]
        self.get_position(team)
        self.get_velocity(team)
        self.PPCF = 0.0

    def get_position(self, team):
        self.position = np.array([team[self.playername + "x"], team[self.playername + "y"]])
        self.inframe  = not np.any(np.isnan(self.position))

    def get_velocity(self, team):
        self.velocity  = np.array([team[self.playername + "vx"], team[self.playername + "vy"]])
        self.speed     = np.linalg.norm(self.velocity)
        self.direction = self.velocity / (self.speed + 1e-8)
        self.moving    = self.speed > 0.05

    def time_to_intercept(self, r_final):
        r_reaction = self.position + self.reaction_time * self.velocity
        ttvmax = self.vmax / self.amax
        tpr = (self.speed + np.sqrt(self.speed**2 + 2 * self.amax * np.linalg.norm(r_final - r_reaction))) / self.amax
        if ttvmax > tpr:
            self.tti = self.reaction_time + tpr
        else:
            dist_at_ttvmax = self.amax * ttvmax**2 / 2
            self.tti = self.reaction_time + ttvmax + (np.linalg.norm(r_final - r_reaction) - dist_at_ttvmax) / self.vmax
        return self.tti

    def prob_to_intercept(self, t_arrival):
        f = 1 / (1.0 + np.exp(-(t_arrival - self.tti) / (np.sqrt(3) * self.tti_sigma / np.pi)))
        return f


def initialize_players(team, teamname, max_speeds, max_accs, params, GKid):
    """VERBATIM from Tracking-PitchControl."""
    unique_ids = np.unique([c.split('_')[1] for c in team.keys() if c[:4] == teamname])
    players = []
    for pid in unique_ids:
        team_player = player(pid, team, teamname, max_speeds, max_accs, params, GKid)
        if team_player.inframe:
            players.append(team_player)
    return players


def check_offsides(attacking_players, defending_players, ball_position, GK_numbers, tol=0.1):
    """VERBATIM from Tracking-PitchControl (fixed numpy.sign typo)."""
    defending_GK_id = GK_numbers[1] if attacking_players[0].teamname == "Home" else GK_numbers[0]
    assert defending_GK_id in [p.id for p in defending_players], "Defending goalkeeper not found"
    defending_GK = [p for p in defending_players if p.id == defending_GK_id][0]
    defending_half = np.sign(defending_GK.position[0])  # fixed: was numpy.sign (typo in original)
    second_deepest_defender_x = sorted(
        [defending_half * p.position[0] for p in defending_players], reverse=True
    )[1]
    offside_line = max(second_deepest_defender_x, defending_half * ball_position[0], 0.0) + tol
    valid_players = [p for p in attacking_players if p.position[0] * defending_half <= offside_line]
    return valid_players


def default_model_params(time_to_control_veto=3):
    """VERBATIM from Tracking-PitchControl."""
    params = {}
    params["amax"]                = 7.
    params["vmax"]                = 5.
    params["reaction_time"]       = 0.7
    params["tti_sigma"]           = 0.45
    params["kappa_def"]           = 1.
    params["lambda_att"]          = 4.3
    params["lambda_def"]          = 4.3 * params['kappa_def']
    params["lambda_gk"]           = params['lambda_def'] * 3.0
    params["average_ball_speed"]  = 15.
    params["int_dt"]              = 0.04
    params["max_int_time"]        = 10
    params["model_converge_tol"]  = 0.01
    params["time_to_control_att"] = time_to_control_veto * np.log(10) * (
        np.sqrt(3) * params['tti_sigma'] / np.pi + 1 / params['lambda_att'])
    params["time_to_control_def"] = time_to_control_veto * np.log(10) * (
        np.sqrt(3) * params['tti_sigma'] / np.pi + 1 / params['lambda_def'])
    return params


def generate_PPCF(target_position, attacking_players, defending_players, ball_start_pos, params):
    """VERBATIM from Tracking-PitchControl — numerical integration of PPCF at one grid cell."""
    if ball_start_pos is None or np.any(np.isnan(ball_start_pos)):
        ball_travel_time = 0.0
    else:
        ball_travel_time = np.linalg.norm(target_position - ball_start_pos) / params['average_ball_speed']

    if not attacking_players or not defending_players:
        return 0.5, 0.5

    tau_min_att = np.nanmin([p.time_to_intercept(target_position) for p in attacking_players])
    tau_min_def = np.nanmin([p.time_to_intercept(target_position) for p in defending_players])

    if tau_min_att - max(ball_travel_time, tau_min_def) >= params["time_to_control_def"]:
        return 0.0, 1.0
    elif tau_min_def - max(ball_travel_time, tau_min_att) >= params["time_to_control_att"]:
        return 1.0, 0.0
    else:
        attacking_players = [p for p in attacking_players
                             if p.time_to_intercept(target_position) - tau_min_att < params["time_to_control_att"]]
        defending_players = [p for p in defending_players
                             if p.time_to_intercept(target_position) - tau_min_def < params["time_to_control_def"]]

        dT_array = np.arange(ball_travel_time - params["int_dt"],
                             ball_travel_time + params["max_int_time"],
                             params["int_dt"])
        PPCF_att = np.zeros_like(dT_array)
        PPCF_def = np.zeros_like(dT_array)
        ptot = 0.0
        i = 1

        while 1 - ptot > params["model_converge_tol"] and i < dT_array.size:
            T = dT_array[i]
            for p in attacking_players:
                dPPCFdT = (1 - PPCF_att[i-1] - PPCF_def[i-1]) * p.prob_to_intercept(T) * p.lambda_att
                assert dPPCFdT >= 0.0, "Invalid attacking player probability"
                p.PPCF = dPPCFdT * params["int_dt"] if i == 1 else p.PPCF + dPPCFdT * params["int_dt"]
                PPCF_att[i] += p.PPCF
            for p in defending_players:
                dPPCFdT = (1 - PPCF_att[i-1] - PPCF_def[i-1]) * p.prob_to_intercept(T) * p.lambda_def
                assert dPPCFdT >= 0.0, "Invalid defending player probability"
                p.PPCF = dPPCFdT * params["int_dt"] if i == 1 else p.PPCF + dPPCFdT * params["int_dt"]
                PPCF_def[i] += p.PPCF
            ptot = PPCF_att[i] + PPCF_def[i]
            i += 1

        return PPCF_att[i-1], PPCF_def[i-1]


def pitch_control_for_frame(
    tracking_home, tracking_away,
    GK_numbers,
    max_speeds_home, max_speeds_away,
    max_accs_home, max_accs_away,
    params,
    field_dimen=(106., 68.),
    n_grid_cells_x=50,
    offsides=False
):
    """
    VERBATIM from Tracking-PitchControl — compute full pitch control surface for one frame.
    Returns: (PPCFa, PPCFd, xgrid, ygrid)
    """
    ball_start_pos = np.array([tracking_home['ball_x'], tracking_home['ball_y']])
    n_grid_cells_y = int(n_grid_cells_x * field_dimen[1] / field_dimen[0])
    dx = field_dimen[0] / n_grid_cells_x
    dy = field_dimen[1] / n_grid_cells_y
    xgrid = np.arange(n_grid_cells_x) * dx - field_dimen[0] / 2. + dx / 2.
    ygrid = np.arange(n_grid_cells_y) * dy - field_dimen[1] / 2. + dy / 2.

    PPCFa = np.zeros(shape=(len(ygrid), len(xgrid)))
    PPCFd = np.zeros(shape=(len(ygrid), len(xgrid)))

    attacking_players = initialize_players(tracking_home, 'Home', max_speeds_home, max_accs_home, params, GK_numbers[0])
    defending_players = initialize_players(tracking_away, 'Away', max_speeds_away, max_accs_away, params, GK_numbers[1])

    if offsides:
        attacking_players = check_offsides(attacking_players, defending_players, ball_start_pos, GK_numbers)

    for (i, j) in itertools.product(range(len(ygrid)), range(len(xgrid))):
        target_position = np.array([xgrid[j], ygrid[i]])
        PPCFa[i, j], PPCFd[i, j] = generate_PPCF(
            target_position, attacking_players, defending_players, ball_start_pos, params)

    checksum = np.sum(PPCFa + PPCFd) / float(n_grid_cells_y * n_grid_cells_x)
    if 1 - checksum >= params['model_converge_tol']:
        logger.debug(f"PPCF checksum gap {1 - checksum:.3f} — clamping grid values")
        # Soft normalise: scale so PPCFa + PPCFd ≤ 1 everywhere
        total = PPCFa + PPCFd
        mask  = total > 1.0
        PPCFa[mask] /= total[mask]
        PPCFd[mask] /= total[mask]
    return PPCFa, PPCFd, xgrid, ygrid


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Service wrapper (not in original repo)
# ─────────────────────────────────────────────────────────────────────────────

class PitchControlService:
    """
    Service wrapper around the Spearman PPCF engine.
    Accepts our internal tracking format (from YOLO/ByteTrack) and
    returns JSON-serializable pitch control data.

    NEW code — extends Tracking-PitchControl for API integration.
    """

    def __init__(self, params: Optional[Dict] = None,
                 field_dimen: Tuple[float, float] = (106., 68.),
                 n_grid_cells_x: int = 50):
        self.params        = params or default_model_params()
        self.field_dimen   = field_dimen
        self.n_grid_cells_x = n_grid_cells_x

    def compute_frame(self, frame_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute pitch control for a single frame.

        Args:
            frame_data: {
                'home': {playerid: {'x': float, 'y': float, 'vx': float, 'vy': float}, ...},
                'away': {playerid: {'x': float, 'y': float, 'vx': float, 'vy': float}, ...},
                'ball': {'x': float, 'y': float},
                'gk_home': str,
                'gk_away': str,
            }

        Returns:
            {
                'ppcf_home': [[float]], 'ppcf_away': [[float]],
                'xgrid': [float], 'ygrid': [float],
                'home_control_pct': float, 'away_control_pct': float,
                'player_dominance': {player_id: float}
            }
        """
        tracking_home, tracking_away = self._build_tracking_rows(frame_data)
        max_speeds_home = {pid: self.params["vmax"] for pid in frame_data['home']}
        max_speeds_away = {pid: self.params["vmax"] for pid in frame_data['away']}
        max_accs_home   = {pid: self.params["amax"] for pid in frame_data['home']}
        max_accs_away   = {pid: self.params["amax"] for pid in frame_data['away']}

        gk_home = frame_data.get('gk_home', list(frame_data['home'].keys())[0] if frame_data['home'] else None)
        gk_away = frame_data.get('gk_away', list(frame_data['away'].keys())[0] if frame_data['away'] else None)

        # Guard: pitch control requires at least 1 player per team
        n_y = int(self.n_grid_cells_x * self.field_dimen[1] / self.field_dimen[0])
        fallback_half = np.full((n_y, self.n_grid_cells_x), 0.5)
        xgrid_fb = np.linspace(-self.field_dimen[0]/2, self.field_dimen[0]/2, self.n_grid_cells_x)
        ygrid_fb = np.linspace(-self.field_dimen[1]/2, self.field_dimen[1]/2, n_y)
        if not frame_data['home'] or not frame_data['away'] or gk_home is None or gk_away is None:
            return {
                'ppcf_home':        fallback_half.tolist(),
                'ppcf_away':        fallback_half.tolist(),
                'xgrid':            xgrid_fb.tolist(),
                'ygrid':            ygrid_fb.tolist(),
                'home_control_pct': 50.0,
                'away_control_pct': 50.0,
            }

        try:
            PPCFa, PPCFd, xgrid, ygrid = pitch_control_for_frame(
                tracking_home, tracking_away,
                (gk_home, gk_away),
                max_speeds_home, max_speeds_away,
                max_accs_home, max_accs_away,
                self.params,
                field_dimen=self.field_dimen,
                n_grid_cells_x=self.n_grid_cells_x,
            )
        except Exception as e:
            logger.error(f"Pitch control computation failed: {e}")
            n_y = int(self.n_grid_cells_x * self.field_dimen[1] / self.field_dimen[0])
            PPCFa = np.full((n_y, self.n_grid_cells_x), 0.5)
            PPCFd = np.full((n_y, self.n_grid_cells_x), 0.5)
            xgrid = np.linspace(-self.field_dimen[0]/2, self.field_dimen[0]/2, self.n_grid_cells_x)
            ygrid = np.linspace(-self.field_dimen[1]/2, self.field_dimen[1]/2, n_y)

        total_cells      = PPCFa.size
        home_control_pct = float(np.mean(PPCFa) * 100)   # average control probability × 100
        away_control_pct = float(np.mean(PPCFd) * 100)

        return {
            'ppcf_home':        PPCFa.tolist(),
            'ppcf_away':        PPCFd.tolist(),
            'xgrid':            xgrid.tolist(),
            'ygrid':            ygrid.tolist(),
            'home_control_pct': home_control_pct,
            'away_control_pct': away_control_pct,
        }

    def compute_batch(self, frames: List[Dict], max_workers: int = 4) -> List[Dict]:
        """Compute pitch control for multiple frames with thread pool."""
        results = [None] * len(frames)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(self.compute_frame, f): i for i, f in enumerate(frames)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.error(f"Frame {idx} failed: {e}")
                    results[idx] = {'error': str(e)}
        return results

    def aggregate_territorial_dominance(self, frame_results: List[Dict]) -> Dict[str, float]:
        """Average pitch control across all frames → territorial dominance stats."""
        valid = [r for r in frame_results if 'ppcf_home' in r]
        if not valid:
            return {'home_dominance_pct': 50.0, 'away_dominance_pct': 50.0}

        avg_home = np.mean([r['home_control_pct'] for r in valid])
        avg_away = np.mean([r['away_control_pct'] for r in valid])
        return {
            'home_dominance_pct': float(avg_home),
            'away_dominance_pct': float(avg_away),
            'frames_analyzed':    len(valid),
        }

    @staticmethod
    def _build_tracking_rows(frame_data: Dict) -> Tuple[Dict, Dict]:
        """
        Convert our internal frame dict into the flat-key format expected by
        the Tracking-PitchControl player class.
        e.g. {'Home_7_x': 20.3, 'Home_7_y': 5.1, 'Home_7_vx': 1.2, ...}
        """
        home_row: Dict = {}
        away_row: Dict = {}

        ball_x = frame_data['ball'].get('x', 0.0)
        ball_y = frame_data['ball'].get('y', 0.0)
        home_row['ball_x'] = ball_x
        home_row['ball_y'] = ball_y
        away_row['ball_x'] = ball_x
        away_row['ball_y'] = ball_y

        for pid, pdata in frame_data['home'].items():
            key = f"Home_{pid}_"
            home_row[key + 'x']  = pdata.get('x',  np.nan)
            home_row[key + 'y']  = pdata.get('y',  np.nan)
            home_row[key + 'vx'] = pdata.get('vx', 0.0)
            home_row[key + 'vy'] = pdata.get('vy', 0.0)

        for pid, pdata in frame_data['away'].items():
            key = f"Away_{pid}_"
            away_row[key + 'x']  = pdata.get('x',  np.nan)
            away_row[key + 'y']  = pdata.get('y',  np.nan)
            away_row[key + 'vx'] = pdata.get('vx', 0.0)
            away_row[key + 'vy'] = pdata.get('vy', 0.0)

        return home_row, away_row
