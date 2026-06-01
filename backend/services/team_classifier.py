"""
Team Classifier Service
=======================
NEW module — no equivalent in any source repository.

Uses K-Means clustering on dominant jersey colors (HSV histogram)
to automatically separate players into Team A and Team B.

Algorithm:
  1. Crop player bounding box from frame
  2. Extract torso region (middle third, avoiding head/legs)
  3. Convert to HSV
  4. Compute H-channel histogram (jersey hue profile)
  5. K-Means cluster all players (k=3: team A, team B, goalkeeper/referee)
  6. Assign team labels by cluster
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.cluster import KMeans
from loguru import logger

from config import settings


class TeamClassifier:
    """
    NEW class — jersey color clustering for automatic team assignment.

    Usage:
        classifier = TeamClassifier()
        classifier.fit(frames_with_detections)   # train on first N frames
        labeled_frames = classifier.assign(all_frames)
    """

    def __init__(self, n_teams: int = 2, n_clusters: int = 3):
        self.n_teams    = n_teams
        self.n_clusters = n_clusters            # team A, team B, ref/GK
        self.kmeans: Optional[KMeans] = None
        self.team_label_map: Dict[int, str] = {}  # cluster_id → 'home'/'away'/'referee'
        self._fitted = False

    # ── Training ──────────────────────────────────────────────────────────────

    def fit(self, frames_bgr: List[np.ndarray], detection_frames: List[Dict]) -> None:
        """
        Fit K-Means on jersey color histograms from a sample of frames.

        Args:
            frames_bgr: list of raw BGR video frames
            detection_frames: list of frame dicts with 'persons' list (each with 'bbox')
        """
        features = []
        player_ids = []

        for frame_bgr, det_frame in zip(frames_bgr[:60], detection_frames[:60]):
            for person in det_frame.get('persons', []):
                feat = self._extract_jersey_feature(frame_bgr, person['bbox'])
                if feat is not None:
                    features.append(feat)
                    player_ids.append(person['track_id'])

        if len(features) < self.n_clusters:
            logger.warning("Too few player detections to cluster — using default assignment")
            self.team_label_map = {0: 'home', 1: 'away', 2: 'referee'}
            self._fitted = False
            return

        X = np.array(features, dtype=np.float64)  # sklearn KMeans requires float64
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        self.kmeans.fit(X)

        self._assign_team_labels(X)
        self._fitted = True
        logger.info(f"TeamClassifier fitted: {len(features)} player crops, "
                    f"{self.n_clusters} clusters → {self.team_label_map}")

    def assign(self, frames_bgr: List[np.ndarray], detection_frames: List[Dict]) -> List[Dict]:
        """
        Assign team labels to all detections in all frames.

        Returns updated detection_frames with 'home_players' and 'away_players' populated.
        """
        result_frames = []
        # Use a dummy black frame when we run out of raw frames (mock tracker may
        # produce more detection frames than we sampled raw frames for color)
        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        for i, det_frame in enumerate(detection_frames):
            frame_bgr = frames_bgr[i] if i < len(frames_bgr) else dummy_frame
            det_frame = dict(det_frame)  # shallow copy
            home_players, away_players = [], []

            for person in det_frame.get('persons', []):
                team = self._classify_player(frame_bgr, person)
                player_entry = {
                    'player_id': str(person['track_id']),
                    'track_id':  person['track_id'],
                    'x':         person['x'],
                    'y':         person['y'],
                    'bbox':      person['bbox'],
                    'team':      team,
                }
                if team == 'home':
                    home_players.append(player_entry)
                elif team == 'away':
                    away_players.append(player_entry)

            det_frame['home_players'] = home_players
            det_frame['away_players'] = away_players
            result_frames.append(det_frame)

        logger.info(f"Team assignment complete: {len(result_frames)} frames")
        return result_frames

    # ── Feature Extraction ────────────────────────────────────────────────────

    def _extract_jersey_feature(
        self,
        frame_bgr: np.ndarray,
        bbox: List[float],
        bins: int = 16,
    ) -> Optional[np.ndarray]:
        """
        Extract HSV H-channel histogram from the torso region of a bounding box.
        Returns feature vector of length `bins` or None if crop is invalid.
        """
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h_box = y2 - y1
        # Torso = middle third of bounding box (avoids head/legs)
        y_top    = y1 + h_box // 3
        y_bottom = y1 + 2 * h_box // 3

        # Clamp to frame bounds
        y_top    = max(0, min(y_top,    frame_bgr.shape[0] - 1))
        y_bottom = max(0, min(y_bottom, frame_bgr.shape[0]))
        x1       = max(0, x1)
        x2       = min(frame_bgr.shape[1], x2)

        crop = frame_bgr[y_top:y_bottom, x1:x2]
        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            return None

        hsv  = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # Only use H channel (hue = color identity regardless of lighting)
        hist = cv2.calcHist([hsv], [0], None, [bins], [0, 180])
        hist = hist.flatten()
        total = hist.sum()
        if total == 0:
            return None
        return (hist / total).astype(np.float64)  # normalize — must be float64 for sklearn KMeans

    def _classify_player(self, frame_bgr: np.ndarray, person: Dict) -> str:
        """Classify a single player detection into home/away/referee."""
        if not self._fitted or self.kmeans is None:
            # Fallback: alternate by track_id parity
            return 'home' if person['track_id'] % 2 == 0 else 'away'

        feat = self._extract_jersey_feature(frame_bgr, person['bbox'])
        if feat is None:
            return 'home'

        cluster = int(self.kmeans.predict(feat.reshape(1, -1).astype(np.float64))[0])
        return self.team_label_map.get(cluster, 'home')

    # ── Team Label Assignment ─────────────────────────────────────────────────

    def _assign_team_labels(self, X: np.ndarray) -> None:
        """
        Assign 'home' / 'away' / 'referee' to K-Means clusters.

        Heuristic:
          - The two largest clusters are Team A and Team B
          - The smallest cluster is referee/goalkeeper
          - Team with centroid closer to center hue is 'home' (arbitrary — can be overridden)
        """
        labels = self.kmeans.labels_
        counts = np.bincount(labels, minlength=self.n_clusters)
        sorted_by_size = np.argsort(counts)[::-1]  # descending size

        # Largest two clusters → teams, smallest → referee
        self.team_label_map = {}
        for rank, cluster_id in enumerate(sorted_by_size):
            if rank == 0:
                self.team_label_map[int(cluster_id)] = 'home'
            elif rank == 1:
                self.team_label_map[int(cluster_id)] = 'away'
            else:
                self.team_label_map[int(cluster_id)] = 'referee'

    def get_team_colors(self, frame_bgr: np.ndarray, detection_frames: List[Dict]) -> Dict[str, Tuple]:
        """
        Get representative BGR color for each team (for visualization).
        Returns: {'home': (B, G, R), 'away': (B, G, R)}
        """
        team_samples: Dict[str, List] = {'home': [], 'away': []}
        for det_frame in detection_frames[:20]:
            for person in det_frame.get('persons', []):
                team = self._classify_player(frame_bgr, person)
                if team in team_samples:
                    feat = self._extract_jersey_feature(frame_bgr, person['bbox'])
                    if feat is not None:
                        # Get dominant hue bin
                        dom_bin = int(np.argmax(feat))
                        team_samples[team].append(dom_bin * 180 // 16)

        colors: Dict[str, Tuple] = {}
        for team, hues in team_samples.items():
            if hues:
                avg_hue = int(np.mean(hues))
                # Convert HSV hue → BGR for display
                hsv_color = np.uint8([[[avg_hue, 200, 200]]])
                bgr = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)[0][0]
                colors[team] = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
            else:
                colors[team] = (0, 0, 255) if team == 'home' else (255, 0, 0)
        return colors
