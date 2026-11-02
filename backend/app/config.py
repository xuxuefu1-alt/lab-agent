from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """集中管理服务配置，并为本地 Demo 提供可运行的默认值。"""

    mysql_url: str
    APP_ENV: str = "development"
    JWT_SECRT_KEY: str = "dev-only-change-me"
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MODEL: str = "gemini-3.1-flash-lite"
    REDIS_URL: str | None = None
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    AI_CHECKPOINT_PREFIX: str = "lab_agent_checkpoint"
    AI_CHECKPOINT_TTL_MINUTES: int = 1440
    AI_CONTEXT_MESSAGE_LIMIT: int = 8
    AI_CONTEXT_TOKEN_BUDGET: int = 4000
    AI_CONTEXT_SUMMARY_TRIGGER_MESSAGES: int = 12
    AI_CONTEXT_SUMMARY_CHAR_BUDGET: int = 2400
    AI_INTENT_ROUTER_TIMEOUT_SECONDS: int = 10
    OTEL_SERVICE_NAME: str = "lab-agent-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
if settings.APP_ENV == "production":
    if not settings.mysql_url.startswith("mysql"):
        raise RuntimeError("Production requires mysql_url to point to MySQL")
    if not settings.REDIS_URL:
        raise RuntimeError("Production requires REDIS_URL for LangGraph checkpoints")

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024
ALLOWED_FILE = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
]
