# ⚽ Football Analytics Platform

> **Integrated Network and Pitch Control Modeling for Football Performance Analysis**

A production-ready platform that accepts football video clips (up to 60 seconds) and automatically generates passing networks, pitch control maps, player influence metrics, and tactical insights.

---

## 🏗️ Architecture Overview

```
football-analytics/
├── backend/                    # FastAPI Python backend
│   ├── services/
│   │   ├── video_processor.py  # Frame extraction & homography
│   │   ├── tracker.py          # YOLO + ByteTrack player/ball tracking
│   │   ├── team_classifier.py  # Jersey color clustering (K-Means)
│   │   ├── event_detector.py   # Pass/reception/possession detection
│   │   ├── passing_network.py  # NetworkX graph + centrality metrics
│   │   ├── pitch_control.py    # Spearman model (Tracking-PitchControl)
│   │   ├── influence_scorer.py # Combined player influence scoring
│   │   ├── tactical_analyzer.py# Pattern detection
│   │   └── ai_insights.py      # NL summary generation
│   ├── api/
│   │   └── routes.py           # FastAPI endpoints
│   ├── models/                 # Pydantic schemas
│   ├── tests/                  # Unit tests
│   ├── main.py
│   └── requirements.txt
├── frontend/                   # React + TypeScript dashboard
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
cd football-analytics

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Download YOLO weights (auto-downloads on first run)
# Alternatively: python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"

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
| `POST` | `/api/analyze` | Upload video & trigger full analysis |
| `GET`  | `/api/results/{job_id}` | Fetch analysis results |
| `GET`  | `/api/network/{job_id}` | Passing network data |
| `GET`  | `/api/pitch-control/{job_id}/{frame}` | Pitch control for a frame |
| `GET`  | `/api/influence/{job_id}` | Player influence rankings |
| `GET`  | `/api/tactics/{job_id}` | Tactical insights |
| `GET`  | `/api/export/{job_id}/pdf` | Export PDF report |
| `GET`  | `/api/health` | Health check |

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
Weights are configurable via API.

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
6. **PDF Export** (full report)
7. **Interactive Dashboard** (React)

---

## 📚 References

- Spearman, W. (2018). *Beyond Expected Goals*. 12th MIT Sloan Sports Analytics Conference.
- [sreekar-voleti/Tracking-PitchControl](https://github.com/sreekar-voleti/Tracking-PitchControl)
- [Friends-of-Tracking-Data/LaurieOnTracking](https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking)
