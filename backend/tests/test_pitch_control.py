"""
Unit Tests — Pitch Control Engine
===================================
Tests for the reused Spearman PPCF model and new service wrapper.
"""

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.pitch_control_engine import (
    default_model_params, player, generate_PPCF,
    PitchControlService,
)


class TestDefaultModelParams:
    def test_returns_dict(self):
        params = default_model_params()
        assert isinstance(params, dict)

    def test_required_keys(self):
        params = default_model_params()
        required = ['amax', 'vmax', 'reaction_time', 'tti_sigma', 'lambda_att', 'lambda_def']
        for key in required:
            assert key in params, f"Missing key: {key}"

    def test_vmax_positive(self):
        params = default_model_params()
        assert params['vmax'] > 0

    def test_lambda_gk_greater_than_def(self):
        params = default_model_params()
        assert params['lambda_gk'] > params['lambda_def']


class TestPlayer:
    def setup_method(self):
        self.params = default_model_params()
        self.team_row = {
            'Home_7_x': 10.0, 'Home_7_y': 5.0,
            'Home_7_vx': 2.0, 'Home_7_vy': 0.0,
        }

    def test_player_creation(self):
        p = player('7', self.team_row, 'Home', {}, {}, self.params, 'GK1')
        assert p.id == '7'
        assert p.teamname == 'Home'
        assert p.inframe

    def test_time_to_intercept_positive(self):
        p = player('7', self.team_row, 'Home', {}, {}, self.params, 'GK1')
        r_final = np.array([15.0, 5.0])
        tti = p.time_to_intercept(r_final)
        assert tti > 0

    def test_prob_to_intercept_range(self):
        p = player('7', self.team_row, 'Home', {}, {}, self.params, 'GK1')
        r_final = np.array([15.0, 5.0])
        p.time_to_intercept(r_final)
        prob = p.prob_to_intercept(p.tti)
        assert 0 <= prob <= 1

    def test_gk_flag(self):
        p_gk   = player('GK1', self.team_row | {'Home_GK1_x': -50.0, 'Home_GK1_y': 0.0,
                                                  'Home_GK1_vx': 0.0, 'Home_GK1_vy': 0.0},
                         'Home', {}, {}, self.params, 'GK1')
        assert p_gk.lambda_def == self.params['lambda_gk']


class TestPitchControlService:
    def _make_frame_data(self):
        return {
            'home': {'7': {'x': 10.0, 'y': 5.0, 'vx': 1.0, 'vy': 0.0},
                     '9': {'x': 20.0, 'y': -10.0, 'vx': 0.5, 'vy': 0.5}},
            'away': {'4': {'x': -10.0, 'y': -5.0, 'vx': -1.0, 'vy': 0.0},
                     '6': {'x': -20.0, 'y': 10.0, 'vx': -0.5, 'vy': -0.5}},
            'ball': {'x': 5.0, 'y': 2.0},
            'gk_home': '7',
            'gk_away': '4',
        }

    def test_service_instantiation(self):
        svc = PitchControlService()
        assert svc.params is not None

    def test_build_tracking_rows(self):
        frame_data = self._make_frame_data()
        home_row, away_row = PitchControlService._build_tracking_rows(frame_data)
        assert 'Home_7_x' in home_row
        assert 'ball_x'   in home_row
        assert home_row['ball_x'] == 5.0

    def test_aggregate_territorial_dominance(self):
        svc     = PitchControlService()
        results = [
            {'ppcf_home': [[0.8, 0.6], [0.4, 0.3]], 'ppcf_away': [[0.2, 0.4], [0.6, 0.7]],
             'home_control_pct': 60.0, 'away_control_pct': 40.0},
            {'ppcf_home': [[0.5, 0.5], [0.5, 0.5]], 'ppcf_away': [[0.5, 0.5], [0.5, 0.5]],
             'home_control_pct': 50.0, 'away_control_pct': 50.0},
        ]
        summary = svc.aggregate_territorial_dominance(results)
        assert 'home_dominance_pct' in summary
        assert 'away_dominance_pct' in summary
        assert abs(summary['home_dominance_pct'] - 55.0) < 1e-6
