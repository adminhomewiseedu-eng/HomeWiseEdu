import hashlib
import logging

import httpx
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..services.openai_service import generate_openai_speech_audio
from ..services.elevenlabs_service import generate_speech_audio
from ..models import User
from .auth import get_current_user, authorize_child

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

class TTSResponse(BaseModel):
    audio_url: Optional[str] = None
    success: bool

class RealtimeSessionRequest(BaseModel):
    child_id: int
    lesson_id: int
    day_number: int = 1

@router.post("/realtime-session")
async def create_realtime_session(
    req: RealtimeSessionRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mint a short-lived browser credential; the permanent key never leaves the server."""
    authorize_child(db, current_user, req.child_id)
    response.headers["Cache-Control"] = "no-store"
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Realtime classroom is not configured")

    safety_id = hashlib.sha256(f"homewiseedu:{current_user.id}".encode()).hexdigest()
    session = {
        "type": "realtime",
        "model": settings.OPENAI_REALTIME_MODEL,
        "output_modalities": ["audio"],
        "instructions": (
            "You are the streaming voice for Ms. Ade. Never choose curriculum, evaluate mastery, "
            "or respond to the learner independently. Only speak text explicitly supplied in a "
            "response.create instruction by the HomeWiseEdu backend."
        ),
        "audio": {
            "input": {
                "transcription": {"model": "gpt-4o-mini-transcribe", "language": "en"},
                "noise_reduction": {"type": "near_field"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.62,
                    "prefix_padding_ms": 350,
                    "silence_duration_ms": 1100,
                    "create_response": False,
                    "interrupt_response": True,
                },
            },
            "output": {"voice": settings.OPENAI_REALTIME_VOICE, "speed": 1.0},
        },
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                    "OpenAI-Safety-Identifier": safety_id,
                },
                json={"session": session},
            )
        if response.status_code >= 400:
            logger.warning("Realtime session provider failure status=%s", response.status_code)
            raise HTTPException(status_code=502, detail="Realtime classroom is temporarily unavailable")
        data = response.json()
        return {
            "client_secret": data.get("value"),
            "expires_at": data.get("expires_at"),
            "model": (data.get("session") or {}).get("model", settings.OPENAI_REALTIME_MODEL),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Realtime session creation failed type=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Realtime classroom is temporarily unavailable")

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(req: TTSRequest, current_user: User = Depends(get_current_user)):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_url = None

    # 1. Authoritative: Client-configured ElevenLabs Voice ID
    if settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID:
        target_voice_id = req.voice_id if req.voice_id and req.voice_id != "nova" else settings.ELEVENLABS_VOICE_ID
        audio_url = await generate_speech_audio(req.text, target_voice_id)

    # 2. Fallback: OpenAI Conversational Voice ('nova')
    if not audio_url:
        audio_url = await generate_openai_speech_audio(req.text, voice=req.voice_id or "nova")

    # 3. Fallback: Direct ElevenLabs request
    if not audio_url and req.voice_id and req.voice_id != "nova":
        audio_url = await generate_speech_audio(req.text, req.voice_id)

    return TTSResponse(audio_url=audio_url, success=audio_url is not None)
