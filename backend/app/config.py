from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Video Reference"
    host: str = "0.0.0.0"
    port: int = 8000
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "sqlite:////app/storage/app.db"
    storage_dir: str = "/app/storage"
    queue_name: str = "video-jobs"
    job_timeout_sec: int = 7200
    default_asr_model: str = "base"
    default_transcription_mode: str = "accurate"
    default_language: str = "ru"
    default_summary_mode: str = "extractive"
    highlight_min_duration_sec: int = 60
    highlight_target_duration_sec: int = 75
    highlight_max_duration_sec: int = 90
    max_upload_mb: int = 500

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
STORAGE_DIR = Path(settings.storage_dir)
UPLOADS_DIR = STORAGE_DIR / "uploads"
JOBS_DIR = STORAGE_DIR / "jobs"
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

for path in (STORAGE_DIR, UPLOADS_DIR, JOBS_DIR):
    path.mkdir(parents=True, exist_ok=True)
