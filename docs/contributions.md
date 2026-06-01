# Code Contributions & Attribution

All reused code in this repository is properly attributed below.
Every reused function/class also carries an inline attribution comment in its source file.

---

## Verbatim Reused Components

### 1. Tracking-PitchControl (MIT License)
- **Repository**: https://github.com/sreekar-voleti/Tracking-PitchControl
- **Author**: Sreekar Voleti
- **License**: MIT

| File in this project | Reused from | Functions |
|---|---|---|
| `backend/services/pitch_control_engine.py` | `PitchControl.py` | `player`, `initialize_players`, `check_offsides`, `default_model_params`, `generate_PPCF`, `pitch_control_for_frame` |
| `backend/services/tracking_utils.py` | `DataCleaning.py` | `compute_vel_and_acc`, `_remove_player_vel_and_acc`, `convert_units`, `find_goalkeeper` |

**Modifications made:**
- `pitch_control_engine.py`: Fixed `numpy.sign` typo in `check_offsides`, added `PitchControlService` wrapper class, added batch computation via `ThreadPoolExecutor`
- `tracking_utils.py`: No modifications to verbatim functions; added `TrackingDataAdapter` as new class

---

### 2. football-match-intelligence (MIT License)
- **Repository**: https://github.com/DataKnight1/football-match-intelligence
- **Author**: Tiago Monteiro / DataKnight1
- **Date**: 21-12-2025
- **License**: MIT

| File in this project | Reused from | Functions |
|---|---|---|
| `backend/services/tactical_analyzer.py` | `src/metrics/tactical.py` | `calculate_pitch_control_simplified`, `calculate_pressing_intensity`, `calculate_pass_availability`, `calculate_high_press_triggers`, `calculate_ppda`, `calculate_penetration_index`, `find_player_encounters`, `calculate_field_tilt` |
| `backend/services/pitch_utils.py` | `src/utils/pitch.py` | `pitch_dimensions`, `get_pitch_zone` |

**Modifications made:**
- `tactical_analyzer.py`: Added `TacticalAnalyzer` service class with new pattern detection methods (`_detect_overloads`, `_detect_triangles`, `_detect_wing_attacks`, `_detect_central_progression`, `_detect_high_press`, `_detect_space_creation`)
- `pitch_utils.py`: Added `compute_zone_stats` and `zone_overload_summary` (new functions)

---

### 3. passing-networks-in-python (MIT License)
- **Repository**: https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python
- **Authors**: Sergio Llana (@SergioMinuto90), Laurie Shaw (@EightyFivePoint)
- **License**: MIT

| File in this project | Reused from | Logic |
|---|---|---|
| `backend/services/passing_network.py` | `processing/tracking.py`, `processing/eventing.py` | `PassingNetworkBuilder` ABC pattern, `prepare_data()` structure |
| `backend/services/passing_network.py` | `visualization/passing_network.py` | `draw_pass_map()` visualization logic |
| `backend/services/tracking_utils.py` | `utils.py` | `to_metric_coordinates`, `merge_tracking_data`, `to_single_playing_direction` |
| `backend/services/event_detector.py` | `processing/tracking.py` | `_context_frames()` possession detection logic |

**Modifications made:**
- `passing_network.py`: ABC interface preserved; data format adapted from Metrica CSV to our internal tracking dict format; `draw_pass_map()` visualization converted from matplotlib to Plotly JSON; **added** `build_networkx_graph()`, `compute_centrality_metrics()` with all 5 metrics, `PassingNetworkService` class
- `event_detector.py`: Possession phase detection logic adapted from `_context_frames()`; all other detection (pass, reception, shot) is new
- `tracking_utils.py`: Functions used verbatim; no modifications

---

## New Original Code

All code below was written specifically for this project with no equivalent in the source repositories:

| File | Description |
|------|-------------|
| `backend/services/video_processor.py` | OpenCV frame extraction, HSV pitch boundary detection, homography estimation |
| `backend/services/tracker.py` | YOLOv11 + ByteTrack integration, foot-point pixel→pitch coordinate mapping |
| `backend/services/team_classifier.py` | K-Means jersey color clustering with HSV torso histograms |
| `backend/services/influence_scorer.py` | Composite PIS = 0.4×PageRank + 0.3×Betweenness + 0.3×Spatial formula |
| `backend/services/ai_insights.py` | Template-based NL insight generation |
| `backend/services/pdf_exporter.py` | ReportLab PDF report generation |
| `backend/services/pipeline.py` | 9-step async analysis orchestrator |
| `backend/api/routes.py` | All FastAPI REST endpoints |
| `backend/models/schemas.py` | All Pydantic request/response models |
| `backend/config.py` | Pydantic settings |
| `backend/main.py` | FastAPI application entry point |
| `frontend/src/` | Entire React + TypeScript dashboard |

---

## License Compliance

All source repositories are MIT licensed. This project's use is compliant:
- ✅ Original copyright notices preserved in inline comments
- ✅ License files present in `external_repos/*/`
- ✅ Attribution listed here and in `docs/repository_analysis.md`
- ✅ No GPL or copyleft dependencies introduced

---

## Methodology Citations

```bibtex
@inproceedings{spearman2018beyond,
  title     = {Beyond Expected Goals},
  author    = {Spearman, William},
  booktitle = {12th MIT Sloan Sports Analytics Conference},
  year      = {2018}
}

@misc{llana2020passing,
  author = {Llana, Sergio and Shaw, Laurie},
  title  = {Passing Networks in Python},
  year   = {2020},
  url    = {https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python}
}
```
