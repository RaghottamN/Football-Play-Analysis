# Repository Analysis — Football Analytics Platform

> Generated: 2026-06-02  
> Author: Antigravity (analysis of cloned external repositories)

---

## Overview

Four repositories were cloned to `external_repos/` and fully analyzed before writing any new code.  
The final platform is built **on top of** these, reusing their strongest components.

```
External Repositories
       ↓
Imported / Reused Components  (verbatim copy with attribution)
       ↓
Adapted Components            (lightly modified / wrapped)
       ↓
New Modules Developed         (video pipeline, YOLO tracker, FastAPI, React UI)
       ↓
Integrated Football Analytics Platform
```

---

## Repository 1 — Tracking-PitchControl

| Field | Value |
|-------|-------|
| **Source** | https://github.com/sreekar-voleti/Tracking-PitchControl |
| **License** | MIT |
| **Reusability Score** | **10 / 10** |

### Key Files & Functions

| File | Key Functions |
|------|--------------|
| `PitchControl.py` | `player` class, `generate_PPCF()`, `pitch_control_for_frame()`, `default_model_params()` |
| `DataCleaning.py` | `compute_vel_and_acc()`, `convert_units()`, `find_goalkeeper()` |
| `Visualization.py` | `plot_pitch()`, `plot_frame()` |

### Integration Strategy
Use `PitchControl.py` verbatim as `backend/services/pitch_control_engine.py`.
Wrap `pitch_control_for_frame()` in a service that accepts YOLO-derived tracking DataFrames.

---

## Repository 2 — football-match-intelligence

| Field | Value |
|-------|-------|
| **Source** | https://github.com/DataKnight1/football-match-intelligence |
| **License** | MIT |
| **Reusability Score** | **8 / 10** |

### Key Files & Functions

| File | Key Functions |
|------|--------------|
| `src/metrics/tactical.py` | `calculate_pitch_control_simplified()`, `calculate_pressing_intensity()`, `calculate_field_tilt()`, `calculate_ppda()`, `calculate_penetration_index()`, `calculate_pass_availability()`, `calculate_high_press_triggers()` |
| `src/visualizations/passing.py` | `plot_phase_pass_network()`, `plot_vertical_pass_network()` |
| `src/utils/pitch.py` | `pitch_dimensions()`, `get_pitch_zone()` |
| `src/analyzer.py` | `MatchAnalyzer` class |

### Integration Strategy
Reuse all 7 tactical metric functions verbatim in `backend/services/tactical_analyzer.py`.
Reuse `get_pitch_zone()` in `backend/services/pitch_utils.py`.

---

## Repository 3 — passing-networks-in-python

| Field | Value |
|-------|-------|
| **Source** | https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python |
| **License** | MIT |
| **Reusability Score** | **9 / 10** |

### Key Files & Functions

| File | Key Functions |
|------|--------------|
| `processing/tracking.py` | `MetricaPassingNetwork`, `_context_frames()`, `prepare_data()` |
| `processing/eventing.py` | `StatsBombPassingNetwork`, `StatsBombBasicPassingNetwork` |
| `visualization/passing_network.py` | `draw_pitch()`, `draw_pass_map()` |
| `utils.py` | `to_metric_coordinates()`, `merge_tracking_data()`, `to_single_playing_direction()` |

### Integration Strategy
Reuse `PassingNetworkBuilder` ABC pattern as base class.
Adapt `draw_pass_map()` to Plotly JSON output.
Extend with NetworkX for 5 centrality metrics + PageRank.

---

## Repository 4 — football_analytics (eddwebster)

| Field | Value |
|-------|-------|
| **Source** | https://github.com/eddwebster/football_analytics |
| **License** | MIT |
| **Reusability Score** | **6 / 10** |

### Integration Strategy
Reference only — cite notebooks for metric formulas. No direct code reuse (Jupyter notebook format).

---

## Reusability Matrix

| Component | Source | Reuse | Target File |
|-----------|--------|-------|-------------|
| Spearman PPCF core | Tracking-PitchControl | Verbatim | `pitch_control_engine.py` |
| `compute_vel_and_acc()` | Tracking-PitchControl | Verbatim | `tracking_utils.py` |
| `plot_pitch()` | Tracking-PitchControl | Adapted→Plotly | `visualizer.py` |
| `calculate_field_tilt()` | football-match-intelligence | Verbatim | `tactical_analyzer.py` |
| `calculate_pressing_intensity()` | football-match-intelligence | Verbatim | `tactical_analyzer.py` |
| `calculate_ppda()` | football-match-intelligence | Verbatim | `tactical_analyzer.py` |
| `calculate_high_press_triggers()` | football-match-intelligence | Verbatim | `tactical_analyzer.py` |
| `calculate_penetration_index()` | football-match-intelligence | Verbatim | `tactical_analyzer.py` |
| `calculate_pass_availability()` | football-match-intelligence | Verbatim | `tactical_analyzer.py` |
| `get_pitch_zone()` | football-match-intelligence | Verbatim | `pitch_utils.py` |
| `PassingNetworkBuilder` ABC | passing-networks | Adapted | `passing_network.py` |
| `_context_frames()` logic | passing-networks | Adapted | `event_detector.py` |
| `to_metric_coordinates()` | passing-networks | Verbatim | `tracking_utils.py` |
| Video extraction | — | NEW | `video_processor.py` |
| YOLO + ByteTrack | — | NEW | `tracker.py` |
| Team color clustering | — | NEW | `team_classifier.py` |
| NetworkX centrality | — | NEW | `passing_network.py` |
| Player Influence Score | — | NEW | `influence_scorer.py` |
| FastAPI routes | — | NEW | `api/routes.py` |
| React dashboard | — | NEW | `frontend/` |

---

## Architecture Flow

```
Tracking-PitchControl      → pitch_control_engine.py (PPCF Spearman model)
football-match-intelligence → tactical_analyzer.py (8 tactical functions)
                            → pitch_utils.py (zone classification)
passing-networks-in-python → passing_network.py (builder pattern + viz)
                           → event_detector.py (possession detection)
                           → tracking_utils.py (coordinate utilities)
          ↓
New Modules
├── video_processor.py     (OpenCV + homography)
├── tracker.py             (YOLOv11 + ByteTrack)
├── team_classifier.py     (K-Means jersey color)
├── influence_scorer.py    (PIS composite score)
├── ai_insights.py         (NL summary generation)
├── pdf_exporter.py        (ReportLab PDF)
├── api/routes.py          (FastAPI endpoints)
└── frontend/              (React + TypeScript)
          ↓
Integrated Football Analytics Platform
POST /api/analyze → full pipeline
GET  /api/results, /api/pitch-control, /api/network, /api/influence, /api/tactics, /api/export/pdf
```

---

## Attribution

All reused code preserves original author attribution in file headers:

- **Tracking-PitchControl**: Sreekar Voleti (MIT)
- **football-match-intelligence**: Tiago Monteiro / DataKnight1 (MIT)
- **passing-networks-in-python**: Sergio Llana `@SergioMinuto90`, Laurie Shaw `@EightyFivePoint` (MIT)
- **football_analytics**: Edd Webster (MIT)
