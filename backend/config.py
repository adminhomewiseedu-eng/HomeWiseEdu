import os
import tempfile
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from pydantic import BaseModel


def _load_env_file():
    for env_path in [Path(__file__).resolve().parent.parent / ".env", Path(__file__).resolve().parent / ".env"]:
        if env_path.exists():
            with env_path.open("r", encoding="utf-8") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_env_file()


def _normalized_database_url() -> str:
    value = os.getenv("DATABASE_URL", "sqlite:///./homewiseedu.db")
    return value.replace("postgres://", "postgresql://", 1) if value.startswith("postgres://") else value


class Settings(BaseModel):
    PROJECT_NAME: str = "HomeWiseEdu API"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str = _normalized_database_url()
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    PORT: int = int(os.getenv("PORT", "8000"))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "")
    ELEVENLABS_MODEL_ID: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    ELEVENLABS_STABILITY: float = float(os.getenv("ELEVENLABS_STABILITY", "0.66"))
    ELEVENLABS_SIMILARITY_BOOST: float = float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.69"))
    ELEVENLABS_STYLE: float = float(os.getenv("ELEVENLABS_STYLE", "0.13"))
    ELEVENLABS_USE_SPEAKER_BOOST: bool = os.getenv("ELEVENLABS_USE_SPEAKER_BOOST", "true").lower() in {"1", "true", "yes"}
    ELEVENLABS_SPEED: float = float(os.getenv("ELEVENLABS_SPEED", "1.13"))
    AUTO_INIT_DB: bool = os.getenv("AUTO_INIT_DB", "true").lower() in {"1", "true", "yes"}
    SEED_MODE: str = os.getenv("SEED_MODE", "demo")
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
    MAX_PROFILE_IMAGE_BYTES: int = int(os.getenv("MAX_PROFILE_IMAGE_BYTES", str(5 * 1024 * 1024)))
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    STORAGE_ROOT: str = os.getenv("STORAGE_ROOT", "")
    TTS_CACHE_DIR: str = os.getenv(
        "TTS_CACHE_DIR",
        str(Path(tempfile.gettempdir()) / "homewiseedu" / "tts")
        if os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
        else str(Path(__file__).resolve().parent / "uploads" / "audio"),
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in {"production", "prod"} or bool(os.getenv("RAILWAY_ENVIRONMENT"))

    @property
    def EVIDENCE_DIR(self) -> str:
        return str(Path(self.STORAGE_ROOT or Path(__file__).resolve().parent / "uploads") / "evidence")

    @property
    def REPORTS_DIR(self) -> str:
        return str(Path(self.STORAGE_ROOT or Path(__file__).resolve().parent / "uploads") / "reports")

    @property
    def UPLOAD_DIR(self) -> str:
        return self.STORAGE_ROOT or str(Path(__file__).resolve().parent / "uploads")

    @property
    def AUDIO_DIR(self) -> str:
        return self.TTS_CACHE_DIR

    @property
    def PROFILE_IMAGE_DIR(self) -> str:
        return str(Path(self.STORAGE_ROOT or Path(__file__).resolve().parent / "uploads") / "profiles")

    @property
    def allowed_origins_list(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return [] if self.is_production else [
                "http://localhost:3000", "http://localhost:5173",
                "http://127.0.0.1:3000", "http://127.0.0.1:5173",
            ]
        return [origin.strip().rstrip("/") for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


def validate_production_settings(candidate: Settings) -> None:
    """Fail closed on unsafe production configuration without exposing values."""
    if not candidate.is_production:
        return
    missing = [name for name in (
        "DATABASE_URL", "SECRET_KEY", "OPENAI_API_KEY", "OPENAI_MODEL",
        "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "ALLOWED_ORIGINS", "STORAGE_ROOT",
    ) if not getattr(candidate, name, "")]
    if missing:
        raise RuntimeError("Missing required production variables: " + ", ".join(missing))
    if len(candidate.SECRET_KEY) < 32:
        raise RuntimeError("Production SECRET_KEY must contain at least 32 characters")
    if not candidate.DATABASE_URL.startswith(("postgresql://", "postgresql+")):
        raise RuntimeError("Production DATABASE_URL must use PostgreSQL")
    for origin in candidate.allowed_origins_list:
        parsed = urlparse(origin)
        hostname = (parsed.hostname or "").lower()
        if (parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}
                or parsed.params or parsed.query or parsed.fragment or origin == "*"
                or hostname in {"localhost", "127.0.0.1", "::1"}):
            raise RuntimeError("Production ALLOWED_ORIGINS must contain only HTTPS public origins")


settings = Settings()
validate_production_settings(settings)
if not settings.SECRET_KEY:
    # Development reloads must not invalidate every active browser session.
    # Production already fails closed above when SECRET_KEY is missing.
    settings.SECRET_KEY = "homewiseedu-local-development-only-secret-key"

for directory in (settings.EVIDENCE_DIR, settings.REPORTS_DIR, settings.PROFILE_IMAGE_DIR, settings.TTS_CACHE_DIR):
    Path(directory).mkdir(parents=True, exist_ok=True)
