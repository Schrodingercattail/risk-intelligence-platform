"""
Application Configuration

All environment-based configuration is centralized here.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


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
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    # Model Paths
    MODEL_PATH: str = "./ml-models/artifacts"

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
    HIGH_RISK_THRESHOLD: float = 0.8
    MEDIUM_RISK_THRESHOLD: float = 0.5

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
