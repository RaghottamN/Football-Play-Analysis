# ⚽ Football Analytics Platform

> **Integrated Network and Pitch Control Modeling for Football Performance Analysis**

A production-ready platform that accepts football video clips (up to 60 seconds) and automatically generates passing networks, pitch control maps, player influence metrics, and tactical insights.

---

## 🏗️ Architecture Overview

```
football-analytics/
├── backend/                          # FastAPI Python backend
│   ├── services/
│   │   ├── pipeline.py               # Full analysis pipeline orchestrator
│   │   ├── event_detector.py         # Pass/reception/possession detection
│   │   ├── passing_network.py        # NetworkX graph + centrality metrics
│   │   ├── pitch_control_engine.py   # Spearman PPCF model (Tracking-PitchControl)
│   │   ├── pitch_utils.py            # Pitch zone classification utilities
│   │   ├── influence_scorer.py       # Combined player influence scoring (PIS)
│   │   ├── tactical_analyzer.py      # Pattern detection (press, tilt, triangles…)
│   │   ├── ai_insights.py            # NL summary generation
│   │   └── pdf_exporter.py           # ReportLab PDF export
│   ├── api/
│   │   └── routes.py                 # FastAPI endpoints
│   ├── models/
│   │   └── schemas.py                # Pydantic request/response schemas
│   ├── tests/                        # Unit tests
│   ├── config.py                     # Environment-driven settings
│   ├── main.py
│   └── requirements.txt
├── frontend/                         # React + TypeScript dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── VideoUpload.tsx
│   │   │   ├── PitchControl.tsx
│   │   │   ├── PassingNetwork.tsx
│   │   │   ├── InfluenceTable.tsx
│   │   │   ├── TacticalInsights.tsx
│   │   │   └── Timeline.tsx
│   │   ├── pages/
│   │   └── App.tsx
│   └── package.json
├── docs/
│   ├── handoff.md                    # Session handoff (read first each session)
│   ├── map.md                        # Endpoint → service → DB relationship map
│   ├── prompts.md                    # Prompt log with outcomes
│   └── repository_analysis.md       # External repo analysis and integration notes
├── external_repos/                   # Cloned source repos (reference only)
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- CUDA-capable GPU (optional but recommended)
- Docker & Docker Compose

### Local Development

```bash
# 1. Clone and enter the project
cd Football-Play-Analysis

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # copy and edit as needed

# 3. Download YOLO weights (auto-downloads on first run)
# Alternatively: python -c "from ultralytics import YOLO; YOLO('yolo11m.pt')"

# 4. Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Docker Deployment

```bash
docker-compose up --build
```

Access at:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check — API status and CUDA availability |
| `POST` | `/api/analyze` | Upload MP4 video → start full analysis pipeline |
| `GET`  | `/api/status/{job_id}` | Poll job progress (0–100%) |
| `GET`  | `/api/results/{job_id}` | Full analysis result bundle |
| `GET`  | `/api/network/{job_id}` | Passing network data (nodes, edges, centrality) |
| `GET`  | `/api/pitch-control/{job_id}` | Pitch control heatmap data (all frames) |
| `GET`  | `/api/pitch-control/{job_id}/frame/{frame_idx}` | Pitch control for a specific frame |
| `GET`  | `/api/influence/{job_id}` | Player Influence Score rankings |
| `GET`  | `/api/tactics/{job_id}` | Tactical pattern insights |
| `GET`  | `/api/insights/{job_id}` | AI-generated narrative summary |
| `GET`  | `/api/possession/{job_id}` | Possession stats and event timeline |
| `GET`  | `/api/export/{job_id}/pdf` | Download PDF report |

See [`HowToUse.md`](HowToUse.md) for request/response examples and a step-by-step workflow.

---

## 🧮 Metrics Computed

### Passing Network
- Degree Centrality
- Betweenness Centrality  
- Closeness Centrality
- Eigenvector Centrality
- PageRank

### Pitch Control (Spearman 2018 Model)
- Frame-by-frame territorial dominance
- Individual spatial influence per player
- Team controlled area percentage

### Player Influence Score
```
PIS = 0.4 × PageRank + 0.3 × Betweenness + 0.3 × Spatial Dominance
```
Weights are configurable per-job via `pis_pagerank`, `pis_betweenness`, `pis_spatial` form fields on `POST /api/analyze`.

### Tactical Patterns Detected
- Overloaded zones
- Space creation movements
- Passing triangles
- Central progression
- Wing attacks
- High press indicators
- Possession structure analysis

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v --cov=services --cov-report=html
```

---

## 📦 Output for a 60-Second Clip

1. **Passing Network Graph** (interactive Plotly)
2. **Pitch Control Heatmap** (per-frame animation)
3. **Player Influence Table** (ranked)
4. **Territorial Dominance Stats** (team-level)
5. **Tactical Insights Report** (NL summaries)
6. **AI Narrative Summary** (natural-language analysis)
7. **PDF Export** (full report)
8. **Interactive Dashboard** (React)

---

## 📚 References

- Spearman, W. (2018). *Beyond Expected Goals*. 12th MIT Sloan Sports Analytics Conference.
- [sreekar-voleti/Tracking-PitchControl](https://github.com/sreekar-voleti/Tracking-PitchControl)
- [DataKnight1/football-match-intelligence](https://github.com/DataKnight1/football-match-intelligence)
- [Friends-of-Tracking-Data/passing-networks-in-python](https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python)
- [eddwebster/football_analytics](https://github.com/eddwebster/football_analytics)
