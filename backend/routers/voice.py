from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..services.elevenlabs_service import generate_speech_audio

router = APIRouter(prefix="/api/voice", tags=["voice"])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

class TTSResponse(BaseModel):
    audio_url: Optional[str] = None
    success: bool

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_url = await generate_speech_audio(req.text, req.voice_id)
    return TTSResponse(audio_url=audio_url, success=audio_url is not None)
