"""
Application Configuration

All environment-based configuration is centralized here.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Calculate project root and model path at module load time
_project_root = Path(__file__).parent.parent.parent
MODEL_PATH_ABSOLUTE = str(_project_root / "ml-models" / "artifacts")


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "Risk Platform API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/risk_platform"

    # API
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://frontend:3000"]

    # Model Paths - Use absolute path for consistency
    MODEL_PATH: str = MODEL_PATH_ABSOLUTE

    # LLM Configuration
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.3

    # Risk Scoring Weights
    ML_WEIGHT: float = 0.5
    RULE_WEIGHT: float = 0.3
    GRAPH_WEIGHT: float = 0.2

    # Risk Thresholds
    # Adjusted to match operational investigation workflow targets:
    # - Critical: 2-5% (via override logic)
    # - High: 5-15% (users with 70-89 scores)
    # - Medium: 35-50% (users with 50-69 scores)
    # - Low: 40-55% (users below 50)
    HIGH_RISK_THRESHOLD: float = 0.7
    MEDIUM_RISK_THRESHOLD: float = 0.5

    # Detection Attribution Thresholds
    # Methods with scores >= these thresholds are considered to have contributed meaningful risk signals
    DETECTION_ML_THRESHOLD: float = 10.0      # LightGBM score >= 10 considered meaningful
    DETECTION_RULE_THRESHOLD: float = 15.0    # Rule score >= 15 considered meaningful
    DETECTION_GRAPH_THRESHOLD: float = 10.0  # Graph score >= 10 considered meaningful

    # Coordinated Trading Detection
    COORDINATED_TRADE_TIME_WINDOW_SECONDS: int = 30
    COORDINATED_TRADE_PRICE_TOLERANCE: float = 0.01  # 1%
    COORDINATED_TRADE_QUANTITY_TOLERANCE: float = 0.05  # 5%
    COORDINATED_TRADE_MIN_OCCURRENCES: int = 3

    # Demo Data Generation
    DEMO_USER_COUNT: int = 2000
    DEMO_TRADE_COUNT: int = 20000
    DEMO_CLUSTER_COUNT: int = 25
    DEMO_NORMAL_RATIO: float = 0.7  # 70% normal users

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Export for easy access
settings = get_settings()
