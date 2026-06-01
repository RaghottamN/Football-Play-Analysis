"""
Pydantic Models / Schemas
=========================
NEW module — request/response schemas for all API endpoints.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────────────────────────

class PISWeightsRequest(BaseModel):
    pagerank:    float = Field(default=0.4, ge=0, le=1)
    betweenness: float = Field(default=0.3, ge=0, le=1)
    spatial:     float = Field(default=0.3, ge=0, le=1)


# ── Response Models ───────────────────────────────────────────────────────────

class JobStatusResponse(BaseModel):
    job_id:   str
    status:   str  # pending | processing | completed | failed
    progress: int  # 0–100
    message:  str


class VideoMetadata(BaseModel):
    filename:     str
    fps:          float
    total_frames: int
    duration_sec: float
    width:        int
    height:       int


class NetworkNode(BaseModel):
    id:          str
    label:       str
    x:           float
    y:           float
    passes:      int
    pagerank:    float
    betweenness: float
    degree:      float


class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: int


class TeamNetwork(BaseModel):
    nodes:      List[NetworkNode]
    edges:      List[NetworkEdge]
    centrality: Dict[str, Dict[str, float]]


class PassingNetworkResponse(BaseModel):
    home:    TeamNetwork
    away:    TeamNetwork
    summary: Dict[str, Any]


class PitchControlFrame(BaseModel):
    ppcf_home:        List[List[float]]
    ppcf_away:        List[List[float]]
    xgrid:            List[float]
    ygrid:            List[float]
    home_control_pct: float
    away_control_pct: float


class PitchControlResponse(BaseModel):
    frames:  List[Dict]   # first 10 frames
    summary: Dict[str, Any]


class PlayerInfluenceRecord(BaseModel):
    player_id:         str
    team:              str
    pagerank:          float
    betweenness:       float
    spatial_dominance: float
    pis:               float
    rank:              int


class InfluenceResponse(BaseModel):
    home:    List[PlayerInfluenceRecord]
    away:    List[PlayerInfluenceRecord]
    weights: Dict[str, float]


class TacticalInsightsResponse(BaseModel):
    field_tilt:           Dict[str, float]
    overloaded_zones:     List[Dict]
    passing_triangles:    Dict[str, int]
    wing_attacks:         Dict[str, float]
    central_progression:  Dict[str, Any]
    high_press:           Dict[str, Any]
    space_creation:       Dict[str, Any]


class AIInsightsResponse(BaseModel):
    key_insights:      List[str]
    tactical_summary:  str
    player_highlights: List[str]
    match_narrative:   str


class FullAnalysisResult(BaseModel):
    job_id:             str
    video_metadata:     VideoMetadata
    possession_stats:   Dict[str, float]
    passing_network:    Dict[str, Any]
    pitch_control:      Dict[str, Any]
    influence_rankings: Dict[str, List]
    tactical_insights:  Dict[str, Any]
    ai_insights:        Dict[str, Any]
    event_summary:      Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    cuda:   bool
    models_dir: str
    version: str = "1.0.0"
