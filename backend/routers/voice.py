from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..config import settings
from ..services.openai_service import generate_openai_speech_audio
from ..services.elevenlabs_service import generate_speech_audio
from ..models import User
from .auth import get_current_user

router = APIRouter(prefix="/api/voice", tags=["voice"])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

class TTSResponse(BaseModel):
    audio_url: Optional[str] = None
    success: bool

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
