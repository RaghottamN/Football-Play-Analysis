"""
Analysis Pipeline Orchestrator
================================
NEW module — not in any source repository.

Wires all services together into one sequential analysis pipeline:
  VideoProcessor → Tracker → TeamClassifier → EventDetector
  → PassingNetworkService → PitchControlService → InfluenceScorer
  → TacticalAnalyzer → AIInsightsGenerator

Used by the FastAPI background task.
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from config import settings
from services.video_processor import VideoProcessor
from services.tracker import PlayerBallTracker
from services.team_classifier import TeamClassifier
from services.event_detector import EventDetector
from services.passing_network import PassingNetworkService
from services.pitch_control_engine import PitchControlService
from services.tracking_utils import TrackingDataAdapter
from services.influence_scorer import InfluenceScorer
from services.tactical_analyzer import TacticalAnalyzer
from services.ai_insights import AIInsightsGenerator


class AnalysisPipeline:
    """
    Full end-to-end analysis pipeline.
    NEW class — orchestrates all services.
    """

    def __init__(self, job_id: str):
        self.job_id     = job_id
        self.result_dir = Path(settings.RESULTS_DIR) / job_id
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.status: Dict = {"status": "pending", "progress": 0, "message": ""}

    # ── Pipeline ──────────────────────────────────────────────────────────────

    async def run(self, video_path: str, pis_weights: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute the full analysis pipeline asynchronously.

        Args:
            video_path: path to uploaded MP4 file
            pis_weights: optional {'pagerank': float, 'betweenness': float, 'spatial': float}

        Returns:
            Full analysis result dict (also saved to results/{job_id}/result.json)
        """
        try:
            self._update_status("processing", 5, "Loading video...")
            video_proc = VideoProcessor(video_path)

            # ── Step 1: Homography ───────────────────────────────────────────
            self._update_status("processing", 10, "Estimating pitch homography...")
            await asyncio.get_event_loop().run_in_executor(
                None, video_proc.estimate_homography)

            # ── Step 2: Tracking ─────────────────────────────────────────────
            self._update_status("processing", 20, "Detecting and tracking players...")
            tracker = PlayerBallTracker()
            tracking_frames = await asyncio.get_event_loop().run_in_executor(
                None, lambda: tracker.process_video(video_proc, sample_rate=settings.TRACKING_FRAME_RATE)
            )

            # ── Step 3: Team Classification ──────────────────────────────────
            self._update_status("processing", 35, "Classifying teams by jersey color...")
            classifier   = TeamClassifier()
            # Collect raw frames for color analysis (fit uses first 60, assign covers all frames)
            raw_frames = [f for _, f in list(video_proc.frames(sample_rate=5))[:60]]
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: classifier.fit(raw_frames, tracking_frames[:60]))
            # assign() handles length mismatch with a dummy frame internally
            tracking_frames = await asyncio.get_event_loop().run_in_executor(
                None, lambda: classifier.assign(raw_frames, tracking_frames))

            # ── Step 4: Event Detection ──────────────────────────────────────
            self._update_status("processing", 45, "Detecting events (passes, shots, etc.)...")
            event_detector = EventDetector(fps=video_proc.fps)
            events_df = await asyncio.get_event_loop().run_in_executor(
                None, lambda: event_detector.detect_events(tracking_frames))

            possession_stats = event_detector.compute_possession_stats(
                events_df, video_proc.duration_sec)

            # ── Step 5: Passing Network ──────────────────────────────────────
            self._update_status("processing", 55, "Building passing networks...")
            network_service = PassingNetworkService()
            network_service.load(events_df, tracking_frames)
            network_data = await asyncio.get_event_loop().run_in_executor(
                None, network_service.to_api_response)

            # ── Step 6: Pitch Control ────────────────────────────────────────
            self._update_status("processing", 65, "Computing pitch control (Spearman model)...")
            adapter      = TrackingDataAdapter(fps=video_proc.fps)
            home_df, away_df = await asyncio.get_event_loop().run_in_executor(
                None, lambda: adapter.convert(tracking_frames))
            frame_dicts  = adapter.to_frame_dicts(home_df, away_df)

            # Sample every Nth frame for pitch control (expensive)
            pc_frames = frame_dicts[::settings.FRAME_SAMPLE_RATE]
            pc_service = PitchControlService(
                field_dimen=(settings.PITCH_LENGTH, settings.PITCH_WIDTH),
                n_grid_cells_x=settings.PC_N_GRID_CELLS_X,
            )
            pc_results = await asyncio.get_event_loop().run_in_executor(
                None, lambda: pc_service.compute_batch(pc_frames, max_workers=4))
            pc_summary = pc_service.aggregate_territorial_dominance(pc_results)

            # ── Step 7: Influence Scoring ────────────────────────────────────
            self._update_status("processing", 78, "Computing player influence scores...")
            w = pis_weights or {}
            influence_scorer = InfluenceScorer(
                w_pagerank    = w.get('pagerank',    settings.PIS_WEIGHT_PAGERANK),
                w_betweenness = w.get('betweenness', settings.PIS_WEIGHT_BETWEENNESS),
                w_spatial     = w.get('spatial',     settings.PIS_WEIGHT_SPATIAL),
            )
            spatial_home = InfluenceScorer.spatial_dominance_from_pc(
                pc_results, tracking_frames, team='home')
            spatial_away = InfluenceScorer.spatial_dominance_from_pc(
                pc_results, tracking_frames, team='away')

            influence_rankings = influence_scorer.compute_both_teams(
                network_data['home']['centrality'],
                network_data['away']['centrality'],
                spatial_home, spatial_away,
            )

            # ── Step 8: Tactical Analysis ────────────────────────────────────
            self._update_status("processing", 88, "Analyzing tactical patterns...")
            tactical_analyzer  = TacticalAnalyzer()
            tactical_insights  = await asyncio.get_event_loop().run_in_executor(
                None, lambda: tactical_analyzer.analyze(events_df, tracking_frames))

            # ── Step 9: AI Insights ──────────────────────────────────────────
            self._update_status("processing", 94, "Generating AI insights...")
            ai_gen     = AIInsightsGenerator()
            ai_insights = ai_gen.generate(
                influence_rankings, tactical_insights,
                pc_summary, possession_stats,
                network_data.get('summary', {}),
            )

            # ── Assemble Result ──────────────────────────────────────────────
            result = {
                'job_id':             self.job_id,
                'video_metadata':     video_proc.get_frame_metadata(),
                'possession_stats':   possession_stats,
                'passing_network':    network_data,
                'pitch_control': {
                    'frames':   pc_results[:10],  # first 10 frames for frontend animation
                    'summary':  pc_summary,
                },
                'influence_rankings': influence_rankings,
                'tactical_insights':  tactical_insights,
                'ai_insights':        ai_insights,
                'event_summary': {
                    'total_events': len(events_df),
                    'by_type':      events_df['event_type'].value_counts().to_dict() if not events_df.empty else {},
                },
            }

            # Save to disk
            result_path = self.result_dir / "result.json"
            with open(result_path, 'w') as f:
                json.dump(result, f, indent=2, default=str)

            self._update_status("completed", 100, "Analysis complete")
            logger.info(f"Job {self.job_id} completed successfully")
            return result

        except Exception as e:
            logger.exception(f"Pipeline failed for job {self.job_id}: {e}")
            self._update_status("failed", 0, str(e))
            raise

    def _update_status(self, status: str, progress: int, message: str):
        self.status = {"status": status, "progress": progress, "message": message}
        status_path = self.result_dir / "status.json"
        with open(status_path, 'w') as f:
            json.dump(self.status, f)
        logger.info(f"[{self.job_id}] {progress}% — {message}")

    def get_status(self) -> Dict:
        status_path = self.result_dir / "status.json"
        if status_path.exists():
            with open(status_path) as f:
                return json.load(f)
        return self.status
