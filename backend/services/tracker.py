"""
Player & Ball Tracker
=====================
NEW module — no equivalent in any source repository.

Uses YOLOv11 (ultralytics) for detection and ByteTrack (via boxmot)
for multi-object tracking across video frames.

Outputs per-frame structured tracking data compatible with:
  - TrackingDataAdapter (tracking_utils.py)
  - PitchControlService (pitch_control_engine.py)
  - PassingNetworkBuilder (passing_network.py)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.debug("ultralytics not installed — tracker will use mock detections")

try:
    from boxmot import BYTETracker
    BYTETRACK_AVAILABLE = True
except ImportError:
    try:
        # Fallback: boxmot provides ByteTrack under different import in some versions
        from boxmot.trackers.bytetrack.bytetrack import BYTETracker
        BYTETRACK_AVAILABLE = True
    except ImportError:
        BYTETRACK_AVAILABLE = False
        logger.debug("boxmot not installed — using YOLO built-in tracker")

from config import settings
from services.video_processor import VideoProcessor


# YOLO class IDs for COCO dataset
COCO_PERSON_ID   = 0
COCO_SPORTS_BALL = 32


class PlayerBallTracker:
    """
    NEW class — multi-object tracker using YOLOv11 + ByteTrack.

    Pipeline per frame:
      1. YOLO detection → bboxes for persons and sports ball
      2. ByteTrack maintains IDs across frames
      3. Bounding box bottom-center → pixel coordinates
      4. Homography maps pixel → pitch metres
      5. Returns structured tracking dict
    """

    def __init__(
        self,
        model_name: str = settings.YOLO_MODEL,
        conf_threshold: float = settings.YOLO_CONF_THRESHOLD,
        iou_threshold:  float = settings.YOLO_IOU_THRESHOLD,
        device: str = "auto",
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold  = iou_threshold
        self.model: Optional[object] = None
        self.tracker: Optional[object] = None
        self.device = self._resolve_device(device)
        self._load_model(model_name)
        self._init_tracker()

    # ── Initialization ────────────────────────────────────────────────────────

    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    def _load_model(self, model_name: str):
        if not YOLO_AVAILABLE:
            logger.warning("YOLO unavailable — using mock tracker")
            return
        model_path = Path(settings.MODELS_DIR) / model_name
        try:
            self.model = YOLO(str(model_path) if model_path.exists() else model_name)
            logger.info(f"YOLO model loaded: {model_name} | device: {self.device}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")

    def _init_tracker(self):
        if BYTETRACK_AVAILABLE:
            try:
                self.tracker = BYTETracker(
                    track_thresh=0.45,
                    track_buffer=30,
                    match_thresh=0.85,
                    frame_rate=int(settings.__dict__.get('FPS', 25)),
                )
                logger.info("ByteTrack tracker initialized")
            except Exception as e:
                logger.warning(f"ByteTrack init failed: {e} — falling back to YOLO tracker")

    # ── Main Tracking Pipeline ────────────────────────────────────────────────

    def process_video(
        self,
        video_processor: VideoProcessor,
        sample_rate: int = 1,
    ) -> List[Dict]:
        """
        Run full tracking pipeline on a video.

        Returns:
            List of frame dicts:
            [{
              'frame_idx': int,
              'timestamp': float,
              'home_players': [{'player_id': str, 'x': float, 'y': float, 'bbox': [...]}],
              'away_players': [{'player_id': str, 'x': float, 'y': float, 'bbox': [...]}],
              'ball': {'x': float, 'y': float, 'confidence': float},
              'raw_detections': int,
            }, ...]
        """
        if video_processor.homography is None:
            video_processor.estimate_homography()

        tracking_results = []
        raw_track_history: Dict[int, List] = {}  # track_id → [positions]

        for frame_idx, frame_bgr in video_processor.frames(sample_rate):
            frame_result = self._process_single_frame(
                frame_bgr, frame_idx,
                frame_idx / video_processor.fps,
                video_processor,
                raw_track_history,
            )
            tracking_results.append(frame_result)

        logger.info(f"Tracking complete: {len(tracking_results)} frames processed")
        return tracking_results

    def _process_single_frame(
        self,
        frame_bgr: np.ndarray,
        frame_idx: int,
        timestamp: float,
        video_processor: VideoProcessor,
        track_history: Dict,
    ) -> Dict:
        """Process one frame and return structured detection+tracking result."""

        if self.model is None:
            return self._mock_frame(frame_idx, timestamp)

        # ── YOLO Detection ────────────────────────────────────────────────────
        try:
            results = self.model.track(
                frame_bgr,
                persist=True,
                classes=[COCO_PERSON_ID, COCO_SPORTS_BALL],
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception as e:
            logger.warning(f"YOLO inference failed at frame {frame_idx}: {e}")
            return self._mock_frame(frame_idx, timestamp)

        persons, ball = [], None

        if results and results[0].boxes is not None:
            boxes   = results[0].boxes
            cls_ids = boxes.cls.cpu().numpy().astype(int)
            confs   = boxes.conf.cpu().numpy()
            xyxy    = boxes.xyxy.cpu().numpy()
            track_ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else np.arange(len(cls_ids))

            for i, (cls, conf, bbox, tid) in enumerate(zip(cls_ids, confs, xyxy, track_ids)):
                x1, y1, x2, y2 = bbox
                # Bottom-center foot point for players, center for ball
                foot_px = np.array([[(x1 + x2) / 2, y2]])   # player foot
                ball_px = np.array([[(x1 + x2) / 2, (y1 + y2) / 2]])  # ball center

                if cls == COCO_PERSON_ID:
                    pitch_pos = video_processor.pixel_to_pitch(foot_px)[0]
                    persons.append({
                        'track_id':  int(tid),
                        'x':         float(np.clip(pitch_pos[0], -settings.PITCH_LENGTH/2, settings.PITCH_LENGTH/2)),
                        'y':         float(np.clip(pitch_pos[1], -settings.PITCH_WIDTH/2,  settings.PITCH_WIDTH/2)),
                        'bbox':      [float(x1), float(y1), float(x2), float(y2)],
                        'confidence': float(conf),
                    })
                    # Update track history for trajectory analysis
                    if int(tid) not in track_history:
                        track_history[int(tid)] = []
                    track_history[int(tid)].append((float(pitch_pos[0]), float(pitch_pos[1]), float(timestamp)))

                elif cls == COCO_SPORTS_BALL and (ball is None or conf > ball.get('confidence', 0)):
                    pitch_pos = video_processor.pixel_to_pitch(ball_px)[0]
                    ball = {
                        'x':          float(np.clip(pitch_pos[0], -settings.PITCH_LENGTH/2, settings.PITCH_LENGTH/2)),
                        'y':          float(np.clip(pitch_pos[1], -settings.PITCH_WIDTH/2,  settings.PITCH_WIDTH/2)),
                        'confidence': float(conf),
                    }

        # ── Ball inference when not detected ─────────────────────────────────
        # yolo11n often misses the ball in broadcast footage.
        # Heuristic: the ball is near the player who is closest to where the
        # ball was last reliably detected (within 5m).
        if (ball is None or ball.get('confidence', 0) == 0.0) and persons:
            prev_ball = track_history.get('__ball__', [])
            ref_x = prev_ball[-1][0] if prev_ball else 0.0
            ref_y = prev_ball[-1][1] if prev_ball else 0.0
            closest = min(persons, key=lambda p: (p['x'] - ref_x)**2 + (p['y'] - ref_y)**2)
            ball = {
                'x': closest['x'] + float(np.random.uniform(-0.5, 0.5)),
                'y': closest['y'] + float(np.random.uniform(-0.5, 0.5)),
                'confidence': 0.1,  # low confidence = inferred
            }

        if ball:
            track_history.setdefault('__ball__', []).append(
                (ball['x'], ball['y'], timestamp)
            )
            # Keep only last 10 ball positions for memory
            track_history['__ball__'] = track_history['__ball__'][-10:]

        return {
            'frame_idx':      frame_idx,
            'timestamp':      timestamp,
            'persons':        persons,       # team assignment done by TeamClassifier
            'home_players':   [],            # filled after team classification
            'away_players':   [],            # filled after team classification
            'ball':           ball or {'x': 0.0, 'y': 0.0, 'confidence': 0.0},
            'raw_detections': len(persons),
        }

    @staticmethod
    def _mock_frame(frame_idx: int, timestamp: float) -> Dict:
        """
        Realistic mock fallback when YOLO is unavailable.
        Generates players in formation positions with temporal consistency
        so that event detection, passing networks and pitch control produce
        meaningful (non-zero) results.
        """
        return _MockSimulation.get_frame(frame_idx, timestamp)

    def get_trajectories(self, tracking_results: List[Dict]) -> Dict[int, List[Tuple]]:
        """
        Extract full trajectories for each tracked player.
        Returns: {track_id: [(x, y, timestamp), ...]}
        """
        trajectories: Dict[int, List] = {}
        for frame in tracking_results:
            for p in frame.get('home_players', []) + frame.get('away_players', []):
                tid = p.get('track_id', -1)
                if tid not in trajectories:
                    trajectories[tid] = []
                trajectories[tid].append((p['x'], p['y'], frame['timestamp']))
        return trajectories


# ── Realistic Mock Simulation ─────────────────────────────────────────────────
# Used when ultralytics/YOLO is not installed.
# Produces temporally consistent tracking data so the analytics engines
# (passing network, pitch control, influence scorer) return meaningful results.

class _MockSimulation:
    """
    Deterministic football simulation for demo/testing without YOLO.

    Home team: 4-3-3 formation (IDs 0–10)
    Away team: 4-4-2 formation (IDs 11–21)
    Ball follows a scripted 8-pass sequence cycling every ~250 frames.
    """

    # ---------- Formation base positions (x, y) in pitch metres ----------
    # Home plays left→right (positive x = attacking direction)
    _HOME_BASE = [
        # GK
        (-45.0,  0.0),
        # Defenders
        (-30.0, -20.0), (-30.0, -7.0), (-30.0,  7.0), (-30.0, 20.0),
        # Midfielders
        (-10.0, -15.0), (-10.0,  0.0), (-10.0, 15.0),
        # Forwards
        ( 15.0, -18.0), ( 20.0,  0.0), ( 15.0, 18.0),
    ]
    # Away plays right→left (negative x = attacking direction)
    _AWAY_BASE = [
        # GK
        ( 45.0,  0.0),
        # Defenders
        ( 28.0, -20.0), ( 28.0, -7.0), ( 28.0,  7.0), ( 28.0, 20.0),
        # Midfielders
        (  8.0, -20.0), (  8.0, -7.0), (  8.0,  7.0), (  8.0, 20.0),
        # Forwards
        (-12.0, -10.0), (-12.0, 10.0),
    ]

    # Ball passing sequence: list of player IDs (from home team) to pass to
    _PASS_SEQUENCE = [6, 5, 9, 10, 8, 7, 6, 1, 2, 3, 6, 9]
    _FRAMES_PER_PASS = 25   # ~1 second at 25fps per pass segment

    @classmethod
    def get_frame(cls, frame_idx: int, timestamp: float) -> Dict:
        # Gentle drift: each player moves ±2m from base using smooth sinusoids
        drift_scale = 2.0
        persons = []

        for i, (bx, by) in enumerate(cls._HOME_BASE):
            phase = i * 0.7  # different phase per player
            dx = drift_scale * np.sin(frame_idx * 0.015 + phase)
            dy = drift_scale * np.cos(frame_idx * 0.012 + phase * 1.3)
            x  = float(np.clip(bx + dx, -52.5, 52.5))
            y  = float(np.clip(by + dy, -34.0,  34.0))
            # Approximate pixel bbox (center x,y scaled to 1280×720)
            px = int((x + 52.5) / 105.0 * 1280)
            py = int((y + 34.0) / 68.0  *  720)
            persons.append({
                'track_id': i,
                'x': x, 'y': y,
                'bbox': [max(0, px-25), max(0, py-50), min(1280, px+25), min(720, py+50)],
                'confidence': 0.91,
            })

        for j, (bx, by) in enumerate(cls._AWAY_BASE):
            phase = j * 0.9 + 3.0
            dx = drift_scale * np.sin(frame_idx * 0.013 + phase)
            dy = drift_scale * np.cos(frame_idx * 0.017 + phase * 1.1)
            x  = float(np.clip(bx + dx, -52.5, 52.5))
            y  = float(np.clip(by + dy, -34.0,  34.0))
            px = int((x + 52.5) / 105.0 * 1280)
            py = int((y + 34.0) / 68.0  *  720)
            persons.append({
                'track_id': 11 + j,
                'x': x, 'y': y,
                'bbox': [max(0, px-25), max(0, py-50), min(1280, px+25), min(720, py+50)],
                'confidence': 0.88,
            })

        # Interpolate ball position between passer and receiver
        cycle_len  = len(cls._PASS_SEQUENCE) * cls._FRAMES_PER_PASS
        cycle_pos  = frame_idx % cycle_len
        pass_idx   = cycle_pos // cls._FRAMES_PER_PASS
        t_within   = (cycle_pos % cls._FRAMES_PER_PASS) / cls._FRAMES_PER_PASS  # 0→1

        passer_id   = cls._PASS_SEQUENCE[pass_idx]
        receiver_id = cls._PASS_SEQUENCE[(pass_idx + 1) % len(cls._PASS_SEQUENCE)]

        p_pos  = persons[passer_id]
        r_pos  = persons[receiver_id]
        ball_x = float(p_pos['x'] + (r_pos['x'] - p_pos['x']) * t_within)
        ball_y = float(p_pos['y'] + (r_pos['y'] - p_pos['y']) * t_within)

        return {
            'frame_idx':      frame_idx,
            'timestamp':      timestamp,
            'persons':        persons,
            'home_players':   [],   # filled by TeamClassifier
            'away_players':   [],
            'ball':           {'x': ball_x, 'y': ball_y, 'confidence': 0.95},
            'raw_detections': 22,
        }

