# How to Use — Football Analytics Platform

This guide walks you through setup, running the project, calling every API endpoint, configuring the platform, running tests, and exporting results. Read this before touching the code.

---

## 1. Prerequisites

| Requirement | Minimum version | Notes |
|-------------|----------------|-------|
| Python | 3.10+ | |
| Node.js | 18+ | Frontend only |
| Docker + Docker Compose | Any recent stable | For containerised run |
| CUDA-capable GPU | Optional | CPU fallback works, slower |

---

## 2. Setup

### 2a. Local Development

```bash
# Clone (if you haven't already)
git clone <repo-url>
cd Football-Play-Analysis

# ── Backend ──────────────────────────────────────────────────
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy the example env file and fill in any secrets/overrides
cp .env.example .env            # edit .env as needed

# Start the API server (auto-reloads on file changes)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# ── Frontend (new terminal) ───────────────────────────────────
cd frontend
npm install
npm run dev
```

### 2b. Docker (recommended for production or a clean demo)

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| React dashboard | http://localhost:3000 |
| FastAPI (interactive docs) | http://localhost:8000/docs |
| FastAPI (Redoc) | http://localhost:8000/redoc |

---

## 3. Environment Variables

All settings are driven by environment variables (or `.env`). No secrets are ever hardcoded — the app refuses to start if a required variable is missing.

| Variable | Default | Purpose |
|----------|---------|---------|
| `UPLOAD_DIR` | `uploads` | Where uploaded videos are stored |
| `RESULTS_DIR` | `results` | Where analysis outputs are written |
| `MODELS_DIR` | `models` | Where YOLO weights are cached |
| `MAX_VIDEO_DURATION_SEC` | `60` | Hard cap on video length |
| `MAX_FILE_SIZE_MB` | `500` | Hard cap on upload size |
| `FRAME_SAMPLE_RATE` | `5` | Process every Nth frame for pitch control |
| `TRACKING_FRAME_RATE` | `1` | Process every frame for tracking |
| `YOLO_MODEL` | `yolo11m.pt` | Model name; use `yolo11n.pt` for speed |
| `YOLO_CONF_THRESHOLD` | `0.4` | Detection confidence threshold |
| `YOLO_IOU_THRESHOLD` | `0.5` | Non-max suppression IOU threshold |
| `TRACKER_TYPE` | `bytetrack` | `bytetrack`, `botsort`, or `deepocsort` |
| `PITCH_LENGTH` | `105.0` | Pitch length in metres |
| `PITCH_WIDTH` | `68.0` | Pitch width in metres |
| `PC_N_GRID_CELLS_X` | `50` | Pitch control grid resolution (x) |
| `PC_N_GRID_CELLS_Y` | `32` | Pitch control grid resolution (y) |
| `PC_MAX_PLAYER_SPEED` | `5.0` | Max player speed (m/s) for Spearman model |
| `PC_REACTION_TIME` | `0.7` | Player reaction time (seconds) |
| `PIS_WEIGHT_PAGERANK` | `0.4` | Weight for PageRank in Player Influence Score |
| `PIS_WEIGHT_BETWEENNESS` | `0.3` | Weight for Betweenness Centrality in PIS |
| `PIS_WEIGHT_SPATIAL` | `0.3` | Weight for Spatial Dominance in PIS |
| `N_TEAMS` | `2` | Number of teams to classify |
| `KMEANS_CLUSTERS` | `3` | K-Means clusters (team A, team B, ref/GK) |
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |
| `DEBUG` | `true` | Enable debug mode |

Copy `.env.example` to `.env` and override only what you need. Never commit `.env`.

---

## 4. End-to-End Workflow

The platform works as an async pipeline. You upload a video, get back a `job_id`, poll until the job completes, then fetch results by section.

### Step 1 — Upload a video and start analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "video=@my_clip.mp4" \
  -F "pis_pagerank=0.4" \
  -F "pis_betweenness=0.3" \
  -F "pis_spatial=0.3"
```

**Response:**
```json
{
  "job_id": "3f8a1c2d-...",
  "status": "pending",
  "message": "Analysis started"
}
```

Save the `job_id` — you need it for all subsequent calls. The `pis_*` form fields are optional; the defaults above match config.

### Step 2 — Poll for progress

```bash
curl http://localhost:8000/api/status/3f8a1c2d-...
```

**Response:**
```json
{
  "job_id": "3f8a1c2d-...",
  "status": "processing",
  "progress": 47,
  "message": "Running pitch control model"
}
```

Keep polling until `"status": "completed"`. Status values: `pending` → `processing` → `completed` (or `failed`).

### Step 3 — Fetch results

Once complete, retrieve any combination of result sections:

```bash
# Full result bundle
curl http://localhost:8000/api/results/3f8a1c2d-...

# Passing network only
curl http://localhost:8000/api/network/3f8a1c2d-...

# Pitch control (all frames)
curl http://localhost:8000/api/pitch-control/3f8a1c2d-...

# Pitch control for a specific frame
curl http://localhost:8000/api/pitch-control/3f8a1c2d-.../frame/12

# Player influence rankings (PIS)
curl http://localhost:8000/api/influence/3f8a1c2d-...

# Tactical pattern insights
curl http://localhost:8000/api/tactics/3f8a1c2d-...

# AI narrative insights
curl http://localhost:8000/api/insights/3f8a1c2d-...

# Possession stats + event timeline
curl http://localhost:8000/api/possession/3f8a1c2d-...
```

### Step 4 — Export PDF report

```bash
curl -O -J http://localhost:8000/api/export/3f8a1c2d-.../pdf
```

This generates and downloads a PDF named `football_analysis_<first-8-chars-of-job-id>.pdf`.

---

## 5. Full API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — returns API status and CUDA availability |
| `POST` | `/api/analyze` | Upload MP4 video → start full analysis pipeline |
| `GET` | `/api/status/{job_id}` | Poll job progress (0–100%) |
| `GET` | `/api/results/{job_id}` | Full analysis result bundle (all sections) |
| `GET` | `/api/network/{job_id}` | Passing network: nodes, edges, centrality metrics |
| `GET` | `/api/pitch-control/{job_id}` | Pitch control heatmap data (all frames) |
| `GET` | `/api/pitch-control/{job_id}/frame/{frame_idx}` | Pitch control for a single frame |
| `GET` | `/api/influence/{job_id}` | Player Influence Score rankings |
| `GET` | `/api/tactics/{job_id}` | Tactical pattern insights |
| `GET` | `/api/insights/{job_id}` | AI-generated narrative summary |
| `GET` | `/api/possession/{job_id}` | Possession stats and event timeline |
| `GET` | `/api/export/{job_id}/pdf` | Download full PDF report |

Interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` (Redoc) while the server is running.

---

## 6. Understanding the Outputs

### Passing Network (`/api/network/{job_id}`)

Returns a graph where nodes are players and edges are passes. Each node carries five centrality scores:

- **Degree Centrality** — how many passing connections a player has
- **Betweenness Centrality** — how often a player is on the shortest passing route between others
- **Closeness Centrality** — how quickly a player can reach all others via passes
- **Eigenvector Centrality** — influence weighted by the importance of connected players
- **PageRank** — influence, accounting for the quality of who passes to whom

### Pitch Control (`/api/pitch-control/{job_id}`)

Frame-by-frame territorial dominance based on the Spearman (2018) PPCF model. Each cell in the pitch grid has a value from 0 (full opposition control) to 1 (full team control). Use the `/frame/{frame_idx}` endpoint to step through individual frames.

### Player Influence Score (`/api/influence/{job_id}`)

A composite ranking:

```
PIS = 0.4 × PageRank + 0.3 × Betweenness Centrality + 0.3 × Spatial Dominance
```

Weights are adjustable per-job via the `pis_pagerank`, `pis_betweenness`, and `pis_spatial` form fields on `POST /api/analyze`. They must sum to 1.

### Tactical Insights (`/api/tactics/{job_id}`)

Detected patterns include overloaded zones, space creation movements, passing triangles, central progression, wing attacks, high-press indicators, and possession structure. Each pattern reports whether it was detected and a confidence metric.

### AI Insights (`/api/insights/{job_id}`)

A natural-language narrative summary generated from all computed metrics. Useful for reports and non-technical stakeholders.

---

## 7. Running Tests

```bash
cd backend
pytest tests/ -v --cov=services --cov-report=html
```

This runs the full unit test suite against the services layer and writes a coverage report to `htmlcov/`. Open `htmlcov/index.html` in a browser to inspect per-file coverage.

Always run tests before ending a session if you've touched any shared service, middleware, or pipeline code — a change in a shared module can silently break something else.

---

## 8. Linting and Formatting

Run before marking any piece of work done:

```bash
# Python (install once: pip install black ruff)
black backend/
ruff check backend/

# TypeScript / React
cd frontend
npm run lint
```

---

## 9. Docs Folder

The `/docs` folder is kept up to date alongside the code:

- `handoff.md` — current project state, what was last done, known issues, and next steps. Read this first at the start of any new session.
- `map.md` — relationship map: endpoints → services → data. Read this when touching more than one route or service.
- `prompts.md` — log of prompts run against the coding agent, with outcomes.
- `repository_analysis.md` — analysis of the four external repos the platform builds on and how their code was integrated.

Edit these files efficiently: change only what changed, don't regenerate from scratch.

---

## 10. Adding a New Endpoint

Follow the layering convention from `Backend.md`:

1. **Route handler** in `backend/api/routes.py` — validates the request, calls a service function, returns the response.
2. **Service/business logic** in `backend/services/` — the actual computation. Keep it separate from the route handler.
3. **Schema** in `backend/models/schemas.py` — add a Pydantic response model.
4. **Test** in `backend/tests/` — cover at least happy path, missing job_id (404), and job not yet complete (202).
5. **Update** `docs/map.md` with the new endpoint → service → data relationship.
