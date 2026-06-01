"""
Video Processor Service
=======================
NEW module — no equivalent in any source repository.

Responsibilities:
  1. Accept MP4 uploads (≤ 60 seconds)
  2. Extract frames using OpenCV
  3. Detect pitch boundary via green-channel HSV thresholding
  4. Estimate homography matrix (image px → pitch metres)
  5. Expose frame generator for downstream tracker
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Generator, Tuple, Optional, List, Dict
from loguru import logger

from config import settings


class VideoProcessor:
    """
    NEW class — handles all video-level operations.

    Attributes:
        video_path: path to MP4 file
        fps: detected frames-per-second
        total_frames: frame count
        frame_size: (width, height) in pixels
        homography: 3×3 matrix mapping pixel → pitch coordinates (metres)
    """

    # Standard football pitch corners in world coordinates [metres]
    # Origin at centre, x along length, y along width
    PITCH_WORLD_CORNERS = np.float32([
        [-settings.PITCH_LENGTH / 2, -settings.PITCH_WIDTH / 2],   # top-left
        [ settings.PITCH_LENGTH / 2, -settings.PITCH_WIDTH / 2],   # top-right
        [ settings.PITCH_LENGTH / 2,  settings.PITCH_WIDTH / 2],   # bottom-right
        [-settings.PITCH_LENGTH / 2,  settings.PITCH_WIDTH / 2],   # bottom-left
    ])

    def __init__(self, video_path: str):
        self.video_path   = Path(video_path)
        self.cap: Optional[cv2.VideoCapture] = None
        self.fps          = 25.0
        self.total_frames = 0
        self.frame_size   = (1920, 1080)
        self.homography: Optional[np.ndarray] = None
        self.duration_sec = 0.0
        self._load_metadata()

    def _load_metadata(self):
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        self.fps          = cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size   = (w, h)
        self.duration_sec = self.total_frames / self.fps
        cap.release()
        logger.info(f"Video: {self.video_path.name} | "
                    f"{w}×{h} | {self.fps:.1f} fps | "
                    f"{self.duration_sec:.1f}s | {self.total_frames} frames")

        if self.duration_sec > settings.MAX_VIDEO_DURATION_SEC:
            logger.warning(f"Video {self.duration_sec:.0f}s exceeds limit "
                           f"{settings.MAX_VIDEO_DURATION_SEC}s — will truncate")
            self.total_frames = int(settings.MAX_VIDEO_DURATION_SEC * self.fps)
            self.duration_sec = settings.MAX_VIDEO_DURATION_SEC

    # ── Frame Extraction ──────────────────────────────────────────────────────

    def frames(self, sample_rate: int = 1) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        Yield (frame_index, frame_bgr) for every `sample_rate`-th frame.
        Automatically releases the capture on exhaustion or exception.
        """
        cap = cv2.VideoCapture(str(self.video_path))
        try:
            frame_idx = 0
            while frame_idx < self.total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % sample_rate == 0:
                    yield frame_idx, frame
                frame_idx += 1
        finally:
            cap.release()

    def extract_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        """Extract a single frame by index."""
        cap = cv2.VideoCapture(str(self.video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None

    # ── Pitch Boundary Detection ──────────────────────────────────────────────

    def detect_pitch_boundary(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect the football pitch boundary using HSV green-channel thresholding.
        Returns a 4-point polygon in image coordinates or None if detection fails.

        Algorithm:
          1. Convert BGR → HSV
          2. Threshold green grass (H: 35-85, S: 40-255, V: 40-255)
          3. Morphological close to fill holes
          4. Find largest contour → approximate to quadrilateral
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        kernel = np.ones((20, 20), np.uint8)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        area    = cv2.contourArea(largest)
        frame_area = frame.shape[0] * frame.shape[1]

        if area < 0.25 * frame_area:   # pitch must cover ≥ 25% of frame
            return None

        peri   = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
        else:
            # Fallback: use bounding rectangle corners
            x, y, w, h = cv2.boundingRect(largest)
            return np.float32([[x, y], [x+w, y], [x+w, y+h], [x, y+h]])

    def estimate_homography(self, frame: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        """
        Estimate homography H mapping image pixel coordinates → pitch metres.

        Attempts automatic detection first; falls back to a proportional
        projection based on the largest detected green region.

        Sets self.homography and returns it.
        """
        if frame is None:
            # Use the first frame
            cap = cv2.VideoCapture(str(self.video_path))
            ret, frame = cap.read()
            cap.release()
            if not ret:
                logger.error("Cannot read first frame for homography estimation")
                return None

        pitch_corners_px = self.detect_pitch_boundary(frame)
        if pitch_corners_px is None:
            logger.warning("Pitch boundary not detected — using full-frame proportional projection")
            h, w = frame.shape[:2]
            pitch_corners_px = np.float32([[0, 0], [w, 0], [w, h], [0, h]])

        # Sort corners: top-left, top-right, bottom-right, bottom-left
        pitch_corners_px = self._sort_corners(pitch_corners_px)

        H, _ = cv2.findHomography(pitch_corners_px, self.PITCH_WORLD_CORNERS)
        self.homography = H
        logger.info("Homography estimated successfully")
        return H

    def pixel_to_pitch(self, pixel_coords: np.ndarray) -> np.ndarray:
        """
        Transform pixel coordinates to pitch metres using estimated homography.

        Args:
            pixel_coords: shape (N, 2) array of [px, py] pairs
        Returns:
            shape (N, 2) array of [x_m, y_m] pitch coordinates
        """
        if self.homography is None:
            raise RuntimeError("Call estimate_homography() first")

        pts = pixel_coords.reshape(-1, 1, 2).astype(np.float32)
        transformed = cv2.perspectiveTransform(pts, self.homography)
        return transformed.reshape(-1, 2)

    def pitch_to_pixel(self, pitch_coords: np.ndarray) -> np.ndarray:
        """Inverse of pixel_to_pitch using H⁻¹."""
        if self.homography is None:
            raise RuntimeError("Call estimate_homography() first")
        H_inv = np.linalg.inv(self.homography)
        pts   = pitch_coords.reshape(-1, 1, 2).astype(np.float32)
        return cv2.perspectiveTransform(pts, H_inv).reshape(-1, 2)

    # ── Frame Preprocessing ───────────────────────────────────────────────────

    def preprocess_frame(
        self,
        frame: np.ndarray,
        target_size: Tuple[int, int] = (1280, 720),
    ) -> Tuple[np.ndarray, float]:
        """
        Resize frame for YOLO inference, returning (resized_frame, scale_factor).
        Scale factor is used to map bounding boxes back to original resolution.
        """
        orig_h, orig_w = frame.shape[:2]
        scale = min(target_size[0] / orig_w, target_size[1] / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return resized, scale

    def get_frame_metadata(self) -> Dict:
        """Return serializable metadata about the loaded video."""
        return {
            "filename":     self.video_path.name,
            "fps":          round(self.fps, 2),
            "total_frames": self.total_frames,
            "duration_sec": round(self.duration_sec, 2),
            "width":        self.frame_size[0],
            "height":       self.frame_size[1],
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sort_corners(pts: np.ndarray) -> np.ndarray:
        """Sort 4 corner points: top-left, top-right, bottom-right, bottom-left."""
        pts   = pts[np.argsort(pts[:, 0])]           # sort by x
        left  = pts[:2][np.argsort(pts[:2, 1])]      # left two, sorted by y
        right = pts[2:][np.argsort(pts[2:, 1])]      # right two, sorted by y
        return np.array([left[0], right[0], right[1], left[1]], dtype=np.float32)
