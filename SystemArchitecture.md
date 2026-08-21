# System Architecture — Football Analytics Platform

> Last updated: 2026-08-21

This document describes how the platform is structured, how data moves through it, and how all the pieces relate. Read it alongside `docs/map.md` when making changes that span more than one service or route.

---

## 1. High-Level Overview

```
Client (Browser / curl)
        │
        │  HTTP
        ▼
┌─────────────────────┐
│   FastAPI Backend   │  main.py + api/routes.py
│   (port 8000)       │
└────────┬────────────┘
         │ background task
         ▼
┌─────────────────────┐
│  AnalysisPipeline   │  services/pipeline.py
│  (async orchestrator│
└──────┬──────────────┘
       │ calls in sequence
       ▼
┌──────────────────────────────────────────────────────┐
│                  Service Layer                        │
│                                                       │
│  event_detector.py      →  pass / possession events  │
│  passing_network.py     →  NetworkX graph + metrics  │
│  pitch_control_engine.py→  Spearman PPCF model       │
│  pitch_utils.py         →  zone classification       │
│  influence_scorer.py    →  PIS composite score       │
│  tactical_analyzer.py   →  pattern detection         │
│  ai_insights.py         →  NL narrative generation   │
│  pdf_exporter.py        →  ReportLab PDF             │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Filesystem Store   │  results/{job_id}/result.json
│  (results/ dir)     │  results/{job_id}/report.pdf
└─────────────────────┘
         ▲
         │  served as static files
┌─────────────────────┐
│  React Frontend     │  frontend/  (port 3000)
│  TypeScript + Vite  │
└─────────────────────┘
```

---

## 2. Request Lifecycle

### 2a. Upload and Job Creation (`POST /api/analyze`)

```
1. Client sends multipart/form-data: MP4 file + optional PIS weights
2. routes.py validates:
     - file extension (.mp4 only)
     - file size (≤ MAX_FILE_SIZE_MB, default 500 MB)
3. Video saved to  uploads/{job_id}.mp4
4. AnalysisPipeline(job_id) instantiated and registered in _jobs dict
5. pipeline.run() dispatched as a FastAPI BackgroundTask
6. {"job_id": "...", "status": "pending"} returned immediately
```

### 2b. Pipeline Execution (background)

```
AnalysisPipeline.run(video_path, pis_weights)
  │
  ├─ Stage 1: Event detection
  │    event_detector.py  →  pass events, possession sequences
  │
  ├─ Stage 2: Passing network
  │    passing_network.py →  NetworkX graph
  │                          Degree, Betweenness, Closeness,
  │                          Eigenvector Centrality + PageRank
  │
  ├─ Stage 3: Pitch control
  │    pitch_control_engine.py  →  Spearman PPCF per frame
  │    pitch_utils.py           →  zone labels per player
  │
  ├─ Stage 4: Player influence scoring
  │    influence_scorer.py  →  PIS = 0.4×PageRank
  │                              + 0.3×Betweenness
  │                              + 0.3×Spatial Dominance
  │
  ├─ Stage 5: Tactical analysis
  │    tactical_analyzer.py →  overloads, triangles, press
  │                             field tilt, PPDA, penetration
  │
  ├─ Stage 6: AI narrative
  │    ai_insights.py  →  NL summary from computed metrics
  │
  └─ Stage 7: Persist results
       writes results/{job_id}/result.json
       updates pipeline status → "completed"
```

### 2c. Result Retrieval

```
GET /api/status/{job_id}   →  poll pipeline.get_status()
GET /api/results/{job_id}  →  read results/{job_id}/result.json
GET /api/network/{job_id}  →  result["passing_network"]
GET /api/pitch-control/…   →  result["pitch_control"]
GET /api/influence/{job_id}→  result["influence_rankings"]
GET /api/tactics/{job_id}  →  result["tactical_insights"]
GET /api/insights/{job_id} →  result["ai_insights"]
GET /api/possession/{job_id}→ result["possession_stats"] + ["event_summary"]
GET /api/export/{job_id}/pdf→ PDFExporter.generate() → FileResponse
```

---

## 3. Component Map

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `main.py` | App factory, CORS middleware, static file mount, YOLO pre-load on startup |
| `config.py` | `Settings` (pydantic-settings); all config from env vars or `.env` |
| `api/routes.py` | All REST endpoints; thin handlers — validate, delegate, return |
| `models/schemas.py` | Pydantic request/response schemas |
| `services/pipeline.py` | Async orchestrator; sequences all service calls; holds job status |
| `services/event_detector.py` | Detects passes, receptions, and possession changes from tracking data |
| `services/passing_network.py` | Builds NetworkX graph; computes 5 centrality metrics + PageRank |
| `services/pitch_control_engine.py` | Spearman (2018) PPCF model — ported from Tracking-PitchControl |
| `services/pitch_utils.py` | `get_pitch_zone()` — classifies player positions into pitch zones |
| `services/influence_scorer.py` | Computes PIS composite score; supports configurable weights |
| `services/tactical_analyzer.py` | Detects 7 tactical patterns; wraps football-match-intelligence functions |
| `services/ai_insights.py` | Generates natural-language summaries from metric outputs |
| `services/pdf_exporter.py` | Builds full PDF report with ReportLab |

### Frontend (`frontend/`)

| File / Component | Responsibility |
|-----------------|---------------|
| `src/App.tsx` | Root component; routing |
| `components/VideoUpload.tsx` | File picker + `POST /api/analyze`; shows job_id |
| `components/PassingNetwork.tsx` | Interactive Plotly passing network graph |
| `components/PitchControl.tsx` | Per-frame pitch control heatmap animation |
| `components/InfluenceTable.tsx` | Ranked PIS table |
| `components/TacticalInsights.tsx` | Pattern cards from `/api/tactics` |
| `components/Timeline.tsx` | Event timeline from `/api/possession` |

---

## 4. Data Model (result.json)

The canonical output written to `results/{job_id}/result.json` has this top-level structure:

```json
{
  "job_id": "string",
  "passing_network": {
    "nodes": [{ "id": "player_id", "team": 0, "centrality": {...} }],
    "edges": [{ "source": "id", "target": "id", "weight": 3 }],
    "metrics": { "pagerank": {...}, "betweenness": {...}, ... }
  },
  "pitch_control": {
    "frames": [
      {
        "frame_idx": 0,
        "grid": [[0.0, ..., 1.0]],       // 32×50 float array
        "team_control": { "team_a": 0.54, "team_b": 0.46 }
      }
    ]
  },
  "influence_rankings": [
    { "player_id": "...", "team": 0, "pis": 0.72, "pagerank": 0.8, ... }
  ],
  "tactical_insights": {
    "overloaded_zones": { "detected": true, "confidence": 0.87 },
    "passing_triangles": { "detected": true, "confidence": 0.91 },
    ...
  },
  "ai_insights": { "summary": "Team A dominated ...", "key_players": [...] },
  "possession_stats": { "team_a_pct": 58.3, "team_b_pct": 41.7 },
  "event_summary": [{ "type": "pass", "player": "...", "frame": 12 }]
}
```

---

## 5. Configuration Architecture

All settings live in `config.py` as a `pydantic-settings` `BaseSettings` class. Every field can be overridden by an environment variable of the same name or via `.env`. The `Settings` instance is created once via `@lru_cache` and imported as `settings` throughout the codebase — no magic numbers anywhere else.

Key groupings:

| Group | Key Settings |
|-------|-------------|
| Directories | `UPLOAD_DIR`, `RESULTS_DIR`, `MODELS_DIR` |
| Video constraints | `MAX_VIDEO_DURATION_SEC`, `MAX_FILE_SIZE_MB`, `FRAME_SAMPLE_RATE` |
| YOLO | `YOLO_MODEL`, `YOLO_CONF_THRESHOLD`, `YOLO_IOU_THRESHOLD` |
| Tracking | `TRACKER_TYPE` |
| Pitch dimensions | `PITCH_LENGTH`, `PITCH_WIDTH` |
| Pitch control (Spearman) | `PC_N_GRID_CELLS_X/Y`, `PC_MAX_PLAYER_SPEED`, `PC_REACTION_TIME`, `PC_TTI_SIGMA`, `PC_KAPPA_DEF` |
| PIS weights | `PIS_WEIGHT_PAGERANK`, `PIS_WEIGHT_BETWEENNESS`, `PIS_WEIGHT_SPATIAL` |
| Team clustering | `N_TEAMS`, `KMEANS_CLUSTERS` |
| Server | `API_HOST`, `API_PORT`, `DEBUG` |

---

## 6. External Repositories and Integration

The platform is built on top of four open-source repos cloned to `external_repos/`. See `docs/repository_analysis.md` for the full reusability matrix.

| Repo | License | What was reused |
|------|---------|----------------|
| [Tracking-PitchControl](https://github.com/sreekar-voleti/Tracking-PitchControl) | MIT | Spearman PPCF model → `pitch_control_engine.py` (verbatim) |
| [football-match-intelligence](https://github.com/DataKnight1/football-match-intelligence) | MIT | 7 tactical functions → `tactical_analyzer.py`; `get_pitch_zone()` → `pitch_utils.py` |
| [passing-networks-in-python](https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python) | MIT | `PassingNetworkBuilder` ABC → `passing_network.py`; possession logic → `event_detector.py` |
| [football_analytics](https://github.com/eddwebster/football_analytics) | MIT | Reference only — metric formulas; no direct code reuse |

---

## 7. Job State Machine

```
                ┌─────────┐
  POST /analyze │ pending │
  ──────────────►         │
                └────┬────┘
                     │ pipeline.run() starts
                     ▼
                ┌────────────┐
                │ processing │  progress: 0 → 100
                └─────┬──────┘
                      │
              ┌───────┴────────┐
              ▼                ▼
        ┌──────────┐     ┌────────┐
        │completed │     │ failed │
        └──────────┘     └────────┘
```

Jobs are held in-memory in `_jobs: dict` in `routes.py`. On server restart, a job's results survive on disk and `_get_pipeline_or_404` will lazily re-register it from `results/{job_id}/` if the directory exists. For production scale, replace the in-memory registry with Redis + Celery (noted in the code).

---

## 8. Deployment

### Local (development)

```
Backend:   uvicorn main:app --reload --host 0.0.0.0 --port 8000
Frontend:  npm run dev  (Vite dev server, port 5173 → proxied to 3000)
```

### Docker

`docker-compose.yml` defines two services:

| Service | Dockerfile | Port | Notes |
|---------|-----------|------|-------|
| `backend` | `backend/Dockerfile` | 8000 | Python 3.10, installs requirements.txt |
| `frontend` | `frontend/Dockerfile` | 3000 | nginx serves built React app |

CORS in `main.py` allows `localhost:3000` and `localhost:5173` (Vite). The React app calls the API at `http://localhost:8000`.

### GPU

CUDA is detected at startup and logged. The YOLO model and pitch control engine will use the GPU automatically if `torch.cuda.is_available()` returns `True`. CPU fallback is transparent — just slower on large clips.

---

## 9. Key Design Decisions

**Async pipeline with BackgroundTasks** — the API returns a `job_id` immediately so clients don't time out on long video clips. Clients poll `/api/status/{job_id}`.

**Filesystem as the result store** — results are written to `results/{job_id}/result.json` rather than a database, keeping the stack simple and stateless. The results directory is also mounted as a static files path so the frontend can fetch generated images directly.

**Config via pydantic-settings** — a single `Settings` class, loaded once, drives all tunable parameters. No magic numbers in service code.

**Layered service architecture** — routes only validate and delegate; all computation lives in `services/`. This keeps routes thin and services independently testable.

**PIS weights are per-job** — the `pis_*` form fields on `POST /api/analyze` let callers override the default weights without touching config, useful for experimentation.

**Verbatim external code with attribution** — Spearman's PPCF implementation and the tactical metric functions are used verbatim with original author attribution in file headers, per the MIT licences. This avoids reinventing well-validated algorithms.
