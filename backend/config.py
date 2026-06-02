"""
Application Configuration
=========================
Environment-driven settings with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Directories
    UPLOAD_DIR: str = "uploads"
    RESULTS_DIR: str = "results"
    MODELS_DIR: str = "models"

    # Video constraints
    MAX_VIDEO_DURATION_SEC: int = 60
    MAX_FILE_SIZE_MB: int = 500
    FRAME_SAMPLE_RATE: int = 5          # Process every Nth frame for pitch control
    TRACKING_FRAME_RATE: int = 1        # Process every frame for tracking

    # YOLO
    YOLO_MODEL: str = "yolo11m.pt"      # nano for speed; swap to yolo11m.pt for accuracy
    YOLO_CONF_THRESHOLD: float = 0.4
    YOLO_IOU_THRESHOLD: float = 0.5

    # Tracking
    TRACKER_TYPE: str = "bytetrack"     # bytetrack | botsort | deepocsort

    # Pitch dimensions (standard: 105m x 68m)
    PITCH_LENGTH: float = 105.0
    PITCH_WIDTH: float = 68.0

    # Pitch control model parameters (Spearman 2018)
    PC_N_GRID_CELLS_X: int = 50
    PC_N_GRID_CELLS_Y: int = 32
    PC_MAX_PLAYER_SPEED: float = 5.0    # m/s
    PC_REACTION_TIME: float = 0.7       # seconds
    PC_TTI_SIGMA: float = 0.45          # spread in time-to-intercept distribution
    PC_KAPPA_DEF: float = 3.0           # defensive advantage factor

    # Player Influence Score weights
    PIS_WEIGHT_PAGERANK: float = 0.4
    PIS_WEIGHT_BETWEENNESS: float = 0.3
    PIS_WEIGHT_SPATIAL: float = 0.3

    # Team clustering
    N_TEAMS: int = 2
    KMEANS_CLUSTERS: int = 3           # team A, team B, referee/goalkeeper

    # API / Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
