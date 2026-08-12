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
    APP_NAME: str = "Risk Intelligence Platform API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/risk_platform"

    # API
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "http://frontend:3000"]

    # Model Paths - Use absolute path for consistency
    MODEL_PATH: str = MODEL_PATH_ABSOLUTE

    # LLM Configuration
    # ENABLE_LLM_EXPLANATION: Control whether LLM is used for explanation generation
    # Default: false (platform uses model-based explanations)
    # When true: Requires ANTHROPIC_API_KEY to be set
    ENABLE_LLM_EXPLANATION: bool = False
    ANTHROPIC_API_KEY: str = ""
    # ANTHROPIC_BASE_URL: Optional override for the Anthropic API endpoint.
    # Empty (default) -> use the official Anthropic endpoint (https://api.anthropic.com).
    # Set this to route calls through an Anthropic-compatible gateway while keeping
    # the anthropic SDK unchanged, e.g. the Zhipu GLM gateway:
    #   https://open.bigmodel.cn/api/anthropic
    ANTHROPIC_BASE_URL: str = ""
    # ANTHROPIC_MODEL: Model id passed to messages.create().
    # Use a Claude model id for the official endpoint, or a provider-specific id
    # (e.g. glm-5.2) when ANTHROPIC_BASE_URL points at a compatible gateway.
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.3
    # SHOW_USER_ID_IN_LLM_PROMPT: Control whether user_id is sent to LLM
    # Default: false - user_id is redacted for privacy
    # When true: user_id is included in LLM prompt (use with caution)
    SHOW_USER_ID_IN_LLM_PROMPT: bool = False
    # LOG_REDACT_USER_ID: Control whether user_id is redacted in structured logs
    # Default: true - user_id is redacted in logs for privacy
    # When false: actual user_id is logged (use with caution for debugging)
    # This is separate from SHOW_USER_ID_IN_LLM_PROMPT - logs can be more restrictive
    LOG_REDACT_USER_ID: bool = True

    # Explanation Cache & Rate Limiting
    # EXPLAIN_CACHE_TTL_SECONDS: Time-to-live for explanation cache (default: 600 seconds = 10 minutes)
    EXPLAIN_CACHE_TTL_SECONDS: int = 600
    # EXPLAIN_CACHE_MAX_SIZE: Maximum number of cached entries (default: 1024)
    EXPLAIN_CACHE_MAX_SIZE: int = 1024
    # EXPLAIN_RATE_LIMIT_PER_MIN: Rate limit per client IP per minute (default: 30)
    EXPLAIN_RATE_LIMIT_PER_MIN: int = 30
    # EXPLAIN_LLM_TIMEOUT_SECONDS: Timeout for LLM API calls (default: 5 seconds)
    EXPLAIN_LLM_TIMEOUT_SECONDS: int = 5

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
