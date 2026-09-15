from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+psycopg://scanvideo:scanvideo@postgres:5432/scanvideo"
    media_root: Path = Path("./data/media")
    secret_root: Path = Path("./.secrets")
    trend_feed_urls: list[str] = []

    min_video_duration: float = Field(default=10.0, ge=0)
    max_video_duration: float = Field(default=180.0, gt=0)
    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    translation_provider: str = "argos"
    tts_provider: str = "edge"
    tts_voice: str = "vi-VN-HoaiMyNeural"
    tts_rate: str = "+0%"
    tts_volume: str = "0dB"
    output_width: int = Field(default=1080, gt=0)
    output_height: int = Field(default=1920, gt=0)
    background_gain_db: float = -10.0
    narration_gain_db: float = 3.0

    openai_api_key: str = ""
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    youtube_access_token: str = ""
    youtube_client_secrets_file: Path = Path("./.secrets/client_secret.json")
    youtube_token_file: Path = Path("./.secrets/youtube_token.json")
    youtube_redirect_uri: str = "http://localhost:8000/api/v1/oauth/youtube/callback"
    tiktok_access_token: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8000/api/v1/oauth/tiktok/callback"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator("max_video_duration")
    @classmethod
    def max_must_exceed_min(cls, value: float, info):
        minimum = info.data.get("min_video_duration", 10.0)
        if value < minimum:
            raise ValueError("max_video_duration must be >= min_video_duration")
        return value


settings = Settings()
settings.media_root.mkdir(parents=True, exist_ok=True)
settings.secret_root.mkdir(parents=True, exist_ok=True)
