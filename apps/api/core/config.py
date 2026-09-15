from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+psycopg://scanvideo:scanvideo@postgres:5432/scanvideo"
    media_root: Path = Path("/data/media")
    min_video_duration: float = 10.0
    max_video_duration: float = 180.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
settings.media_root.mkdir(parents=True, exist_ok=True)
