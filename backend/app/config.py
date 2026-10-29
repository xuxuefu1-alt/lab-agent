from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    mysql_url: str  # 数据库
    APP_ENV: str = "development"
    JWT_SECRT_KEY: str  # 密钥
    JWT_EXPIRE_HOURS: int = 24  # 过期时间
    JWT_ALGORITHM: str 
    LLM_API_KEY:str
    LLM_BASE_URL:str
    LLM_MODEL:str
    REDIS_URL: str | None = None
    AI_CHECKPOINT_PREFIX: str = "lab_agent_checkpoint"
    AI_CHECKPOINT_TTL_MINUTES: int = 1440
    AI_CONTEXT_MESSAGE_LIMIT: int = 8
    AI_CONTEXT_TOKEN_BUDGET: int = 4000
    OTEL_SERVICE_NAME: str = "lab-agent-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )


settings = Settings()

UPLOAD_DIR = BASE_DIR / "uploads"  # 创建上传文件
# 上传文件兜底 防止没有upload文件夹
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
