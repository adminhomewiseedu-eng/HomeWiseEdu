import os
from typing import List
from pydantic import BaseModel

def _load_env_file():
    """Load key-value pairs from .env file if present, without overwriting existing environment variables."""
    for env_path in [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
    ]:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v

_load_env_file()

def _get_normalized_db_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "sqlite:///./homewiseedu.db")
    # Railway PostgreSQL URLs often use postgres:// which SQLAlchemy 2.0 requires as postgresql://
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url

class Settings(BaseModel):
    PROJECT_NAME: str = "HomeWiseEdu API"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str = _get_normalized_db_url()
    SECRET_KEY: str = os.getenv("SECRET_KEY", "homewiseedu-super-secure-jwt-key-2026-xyz")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS Origins (Comma-separated in environment, e.g. "https://app.up.railway.app,http://localhost:3000")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")
    
    # OpenAI Settings (Primary AI Provider)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # ElevenLabs Settings (Voice Service)
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "")
    
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")
    AUDIO_DIR: str = os.path.join(os.path.dirname(__file__), "uploads", "audio")

    @property
    def allowed_origins_list(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            # Safe development defaults
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
