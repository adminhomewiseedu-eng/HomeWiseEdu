import os
import hashlib
import logging
import httpx
from typing import Optional, Dict, Any
from ..config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1/text-to-speech"

async def generate_speech_audio(text: str, voice_id: Optional[str] = None) -> Optional[str]:
    """
    On-demand voice generation using ElevenLabs with disk-level content-hash caching.
    Returns relative URL to cached mp3 (e.g. '/uploads/audio/{hash}.mp3').
    """
    if not text or not text.strip():
        return None

    clean_text = text.strip()
    active_voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
    if not active_voice_id:
        logger.info("No ELEVENLABS_VOICE_ID configured. Skipping audio generation.")
        return None

    # Safe diagnostic logging: log masked voice ID to confirm configuration without exposing secrets
    masked_voice = (active_voice_id[:4] + "..." + active_voice_id[-4:]) if len(active_voice_id) > 8 else "configured"
    logger.info(f"Using configured ElevenLabs voice ID: {masked_voice}")
    
    # 1. Compute deterministic content hash for caching
    content_key = f"{clean_text}_{active_voice_id}".encode("utf-8")
    audio_hash = hashlib.sha256(content_key).hexdigest()
    file_name = f"{audio_hash}.mp3"
    file_path = os.path.join(settings.AUDIO_DIR, file_name)
    relative_url = f"/uploads/audio/{file_name}"

    # 2. Return cached audio file if it already exists (Zero API cost & instant response)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return relative_url

    # 3. If no API key configured, return None so client uses browser speech synthesis
    if not settings.ELEVENLABS_API_KEY:
        logger.info("ELEVENLABS_API_KEY not configured. Skipping ElevenLabs audio generation.")
        return None

    # 4. Request audio from ElevenLabs
    url = f"{ELEVENLABS_BASE_URL}/{active_voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": clean_text[:1200], # safe character limit per audio clip
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Generated and cached ElevenLabs audio: {file_name}")
                return relative_url
            else:
                logger.warning(f"ElevenLabs API error ({response.status_code}): {response.text}")
    except Exception as e:
        logger.error(f"Error calling ElevenLabs API: {e}")

    return None
