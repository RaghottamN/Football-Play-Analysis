"""
FastAPI Routes
==============
NEW module — all REST API endpoints for the football analytics platform.

Endpoints:
  POST /api/analyze              — upload video → start analysis job
  GET  /api/status/{job_id}      — poll job progress
  GET  /api/results/{job_id}     — fetch full analysis results
  GET  /api/network/{job_id}     — passing network only
  GET  /api/pitch-control/{job_id} — pitch control data
  GET  /api/influence/{job_id}   — player influence rankings
  GET  /api/tactics/{job_id}     — tactical insights
  GET  /api/insights/{job_id}    — AI narrative insights
  GET  /api/export/{job_id}/pdf  — download PDF report
  GET  /api/health               — health check
"""

import json
import uuid
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from config import settings
from models.schemas import (
    JobStatusResponse, FullAnalysisResult, PassingNetworkResponse,
    PitchControlResponse, InfluenceResponse, TacticalInsightsResponse,
    AIInsightsResponse, HealthResponse, PISWeightsRequest,
)
from services.pipeline import AnalysisPipeline
from services.pdf_exporter import PDFExporter

router = APIRouter()

# In-memory job registry (use Redis/Celery for production scale)
_jobs: dict = {}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Check API and GPU status."""
    try:
        import torch
        cuda = torch.cuda.is_available()
    except ImportError:
        cuda = False
    return HealthResponse(
        status="ok",
        cuda=cuda,
        models_dir=str(Path(settings.MODELS_DIR).resolve()),
    )


# ── Video Analysis ────────────────────────────────────────────────────────────

@router.post("/analyze", tags=["analysis"])
async def analyze_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="MP4 video file (≤60 seconds)"),
    pis_pagerank:    float = Form(default=0.4),
    pis_betweenness: float = Form(default=0.3),
    pis_spatial:     float = Form(default=0.3),
):
    """
    Upload a football video clip and start the full analysis pipeline.

    Returns a `job_id` to poll for status and results.
    """
    # Validate file type
    if not video.filename.lower().endswith('.mp4'):
        raise HTTPException(status_code=400, detail="Only MP4 files are supported")

    # Validate file size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = await video.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
        )

    # Save upload
    job_id      = str(uuid.uuid4())
    upload_path = Path(settings.UPLOAD_DIR) / f"{job_id}.mp4"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    with open(upload_path, 'wb') as f:
        f.write(content)

    # Register job
    pipeline = AnalysisPipeline(job_id)
    _jobs[job_id] = pipeline

    # PIS weights
    pis_weights = {
        'pagerank':    pis_pagerank,
        'betweenness': pis_betweenness,
        'spatial':     pis_spatial,
    }

    # Start background analysis
    background_tasks.add_task(_run_pipeline, pipeline, str(upload_path), pis_weights)

    logger.info(f"Job {job_id} queued: {video.filename} ({len(content)//1024}KB)")
    return {"job_id": job_id, "status": "pending", "message": "Analysis started"}


async def _run_pipeline(pipeline: AnalysisPipeline, video_path: str, pis_weights: dict):
    """Background task wrapper for the analysis pipeline."""
    try:
        await pipeline.run(video_path, pis_weights)
    except Exception as e:
        logger.error(f"Pipeline background task failed: {e}")


# ── Status & Results ──────────────────────────────────────────────────────────

@router.get("/status/{job_id}", response_model=JobStatusResponse, tags=["analysis"])
async def get_status(job_id: str):
    """Poll the progress of an analysis job."""
    pipeline = _get_pipeline_or_404(job_id)
    status   = pipeline.get_status()
    return JobStatusResponse(
        job_id=job_id,
        status=status.get("status", "pending"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
    )


@router.get("/results/{job_id}", tags=["analysis"])
async def get_results(job_id: str):
    """Fetch the full analysis result for a completed job."""
    _get_pipeline_or_404(job_id)
    result_path = Path(settings.RESULTS_DIR) / job_id / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=202, detail="Analysis not yet complete")
    with open(result_path) as f:
        return json.load(f)


@router.get("/network/{job_id}", tags=["analysis"])
async def get_network(job_id: str):
    """Fetch passing network data (nodes, edges, centrality metrics)."""
    return _get_result_section(job_id, "passing_network")


@router.get("/pitch-control/{job_id}", tags=["analysis"])
async def get_pitch_control(job_id: str):
    """Fetch pitch control heatmap data (Spearman 2018 model output)."""
    return _get_result_section(job_id, "pitch_control")


@router.get("/pitch-control/{job_id}/frame/{frame_idx}", tags=["analysis"])
async def get_pitch_control_frame(job_id: str, frame_idx: int):
    """Fetch pitch control for a specific frame index."""
    pc_data = _get_result_section(job_id, "pitch_control")
    frames  = pc_data.get("frames", [])
    if frame_idx >= len(frames):
        raise HTTPException(status_code=404, detail=f"Frame {frame_idx} not found (max={len(frames)-1})")
    return frames[frame_idx]


@router.get("/influence/{job_id}", tags=["analysis"])
async def get_influence(job_id: str):
    """Fetch player influence rankings (PIS scores)."""
    return _get_result_section(job_id, "influence_rankings")


@router.get("/tactics/{job_id}", tags=["analysis"])
async def get_tactics(job_id: str):
    """Fetch tactical pattern insights."""
    return _get_result_section(job_id, "tactical_insights")


@router.get("/insights/{job_id}", tags=["analysis"])
async def get_ai_insights(job_id: str):
    """Fetch AI-generated narrative insights."""
    return _get_result_section(job_id, "ai_insights")


@router.get("/possession/{job_id}", tags=["analysis"])
async def get_possession(job_id: str):
    """Fetch possession statistics and event timeline."""
    data = {}
    data["possession_stats"] = _get_result_section(job_id, "possession_stats")
    data["event_summary"]    = _get_result_section(job_id, "event_summary")
    return data


# ── PDF Export ────────────────────────────────────────────────────────────────

@router.get("/export/{job_id}/pdf", tags=["export"])
async def export_pdf(job_id: str):
    """Generate and download a PDF report for a completed analysis."""
    result_path = Path(settings.RESULTS_DIR) / job_id / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")

    with open(result_path) as f:
        result_data = json.load(f)

    pdf_path = Path(settings.RESULTS_DIR) / job_id / "report.pdf"
    exporter = PDFExporter()
    exporter.generate(result_data, str(pdf_path))

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"football_analysis_{job_id[:8]}.pdf",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_pipeline_or_404(job_id: str) -> AnalysisPipeline:
    """Return pipeline for job_id or raise 404."""
    pipeline = _jobs.get(job_id)
    if pipeline is None:
        # Check if results exist on disk (from a previous server restart)
        result_dir = Path(settings.RESULTS_DIR) / job_id
        if result_dir.exists():
            pipeline = AnalysisPipeline(job_id)
            _jobs[job_id] = pipeline
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return pipeline


def _get_result_section(job_id: str, section: str):
    """Load a specific section from the result JSON."""
    _get_pipeline_or_404(job_id)
    result_path = Path(settings.RESULTS_DIR) / job_id / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=202, detail="Analysis not yet complete")
    with open(result_path) as f:
        data = json.load(f)
    if section not in data:
        raise HTTPException(status_code=404, detail=f"Section '{section}' not in results")
    return data[section]
