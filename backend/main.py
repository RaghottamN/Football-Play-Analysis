"""
Football Analytics Platform - FastAPI Main Application
======================================================
Entry point for the backend API server.
"""

import os
import uuid
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from api.routes import router
from config import settings


# ── Startup / Shutdown lifecycle ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    logger.info("🚀 Football Analytics Platform starting up...")
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.MODELS_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"   Upload dir  : {settings.UPLOAD_DIR}")
    logger.info(f"   Results dir : {settings.RESULTS_DIR}")
    logger.info(f"   CUDA        : {_cuda_status()}")

    # Pre-download YOLO model so it's cached before the first job
    await asyncio.get_event_loop().run_in_executor(None, _preload_yolo_model)

    yield
    logger.info("⛔ Football Analytics Platform shutting down...")


def _cuda_status() -> str:
    try:
        import torch
        return f"Yes ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else "No (CPU mode)"
    except Exception:
        return "Unknown"


def _preload_yolo_model():
    """Download & cache the YOLO model weights at startup (runs once in thread pool)."""
    try:
        from ultralytics import YOLO
        import logging
        # Suppress ultralytics download chatter
        logging.getLogger("ultralytics").setLevel(logging.ERROR)
        model_name = settings.YOLO_MODEL
        model_path = Path(settings.MODELS_DIR) / model_name
        target = str(model_path) if model_path.exists() else model_name
        YOLO(target)
        logger.info(f"   YOLO model  : {model_name} — ready ✅")
    except Exception as e:
        logger.warning(f"   YOLO pre-load skipped: {e}")


# ── Application factory ───────────────────────────────────────────────────────
app = FastAPI(
    title="Football Analytics Platform",
    description=(
        "Production-ready football video analytics: passing networks, "
        "pitch control maps, player influence metrics, and tactical insights."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS – allow the React dev server and any production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static results directory so frontend can fetch generated images/JSON
os.makedirs(settings.RESULTS_DIR, exist_ok=True)
app.mount("/results", StaticFiles(directory=settings.RESULTS_DIR), name="results")

# Include all API routes
app.include_router(router, prefix="/api")


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "⚽ Football Analytics Platform API",
        "docs": "/docs",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
