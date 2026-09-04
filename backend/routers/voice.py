import hashlib
import json
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
from ..models import User, Lesson, LessonSession
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


def _realtime_classroom_instructions(child, lesson, active_day, state) -> str:
    curriculum = {
        "student_name": child.name,
        "level": child.level,
        "subject": lesson.unit.subject.title if lesson.unit and lesson.unit.subject else "General",
        "unit": lesson.unit.title if lesson.unit else "General Unit",
        "lesson": lesson.title,
        "topic": lesson.topic or lesson.title,
        "day_number": active_day.day_number if active_day else 1,
        "activity_type": active_day.activity_type if active_day else "Explore",
        "objectives": (active_day.learning_objectives if active_day else None) or lesson.objectives or [],
        "key_concept": (active_day.key_concept if active_day else None) or lesson.learn_content or "",
        "teaching_script": active_day.ai_script if active_day else "",
        "worked_example_seeds": (active_day.practice_questions if active_day else None) or lesson.examples or [],
        "real_world_context": active_day.real_world_context if active_day else "",
    }
    active_state = state or {"current_phase": "GREETING", "practice_ready": False}
    return (
        "You are Ms. Ade, the warm, concise live teacher in HomeWiseEdu. This is a child-safe "
        "voice classroom. Speak natural UK English only for the entire session. Never switch language, "
        "translate, imitate another language, or mirror a language inferred from unclear audio. If speech is "
        "unclear, ask the learner to repeat it in English while remaining in English yourself. "
        "STRUCTURED_CURRICULUM is authoritative. Follow its teaching_script as the "
        "primary teaching sequence, in order, and use its objectives, key_concept, worked_example_seeds, "
        "and real_world_context to support that sequence. Do not replace the teaching_script with a generic "
        "topic definition or an improvised mini-lesson. You may simplify the wording for the child's level, "
        "but preserve every instructional step and intended learner prompt. Use the supplied curriculum only; "
        "never choose a new curriculum "
        "or claim that a learner passed, mastered, advanced, or unlocked a quiz. The FastAPI backend "
        "is the sole authority for phase progression and practice_ready. Teach interactively: present one "
        "small idea at a time and then stop completely so the learner can respond. In a teaching or worked-example "
        "phase, explain and demonstrate the assigned idea before asking any question. Never make the learner supply "
        "the example, objects, or teaching content. Never say 'look here', 'look at this', or claim that physical or "
        "visual objects are present unless the app explicitly confirms that a matching visual is displayed. Describe "
        "an imagined example aloud when no confirmed visual is available. Never deliver several lesson sections as one monologue. "
        "Speak at a calm primary-school teaching pace, with short sentences, clear pauses between ideas, and "
        "extra emphasis on numbers and key vocabulary. Keep normal replies brief and natural, then yield. "
        "Use the learner's name sparingly, normally only in the greeting or encouragement, not in every reply. "
        "If the learner repeats the same phrase while waiting, acknowledge it once and answer immediately. "
        "Respond directly and immediately to "
        "repeats, clarifications, acknowledgements, and interruptions without changing the task. When the "
        "authoritative phase is UNDERSTANDING_CHECK, GUIDED_PRACTICE, APPLICATION, or MASTERY_CHECK, "
        "you MUST call submit_academic_response for any substantive learner answer before giving correctness "
        "feedback. Never call submit_academic_response during GREETING, TEACHING, WORKED_EXAMPLE_1, "
        "WORKED_EXAMPLE_2, WORKED_EXAMPLE_3, or LESSON_SUMMARY; respond conversationally during those phases. "
        "Do not call it for a repeat, clarification, 'wait', or simple acknowledgement. Never tell the learner that "
        "an answer was submitted, failed to submit, did not go through, or encountered a technical error. Treat the "
        "latest backend tool output or app-supplied phase instruction as authoritative. During a teacher-led "
        "phase, deliver only that phase and stop; the app will authorize the next phase after playback completes.\n"
        f"STRUCTURED_CURRICULUM={json.dumps(curriculum, ensure_ascii=True)}\n"
        f"INITIAL_AUTHORITATIVE_STATE={json.dumps(active_state, ensure_ascii=True)}"
    )

@router.post("/realtime-session")
async def create_realtime_session(
    req: RealtimeSessionRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mint a short-lived browser credential; the permanent key never leaves the server."""
    child = authorize_child(db, current_user, req.child_id)
    response.headers["Cache-Control"] = "no-store"
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Realtime classroom is not configured")

    lesson = db.query(Lesson).filter(Lesson.id == req.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    active_day = next((day for day in lesson.days if day.day_number == req.day_number), None)
    if lesson.days and not active_day:
        raise HTTPException(status_code=404, detail="Lesson day not found")
    if active_day and current_user.role != "admin" and (active_day.status or "").lower() not in {"active", "published"}:
        raise HTTPException(status_code=404, detail="Lesson day not found")
    lesson_session = db.query(LessonSession).filter(
        LessonSession.child_id == req.child_id,
        LessonSession.lesson_id == req.lesson_id,
        LessonSession.day_number == req.day_number,
    ).first()
    authoritative_state = lesson_session.pedagogical_state if lesson_session else None
    base_instructions = _realtime_classroom_instructions(child, lesson, active_day, authoritative_state)

    safety_id = hashlib.sha256(f"homewiseedu:{current_user.id}".encode()).hexdigest()
    session = {
        "type": "realtime",
        "model": settings.OPENAI_REALTIME_MODEL,
        "output_modalities": ["audio"],
        "instructions": base_instructions,
        "tools": [{
            "type": "function",
            "name": "submit_academic_response",
            "description": (
                "Submit a substantive answer to the current authoritative academic checkpoint. "
                "Never use for repeats, clarifications, interruptions, or acknowledgements."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_response": {"type": "string", "description": "The learner's answer exactly as heard."}
                },
                "required": ["student_response"],
                "additionalProperties": False,
            },
        }],
        "tool_choice": "auto",
        "audio": {
            "input": {
                "transcription": {"model": "gpt-4o-mini-transcribe", "language": "en"},
                # Laptop microphones normally capture a learner from farther
                # away than a headset. Preserve that speech before VAD runs.
                "noise_reduction": {"type": "far_field"},
                "turn_detection": {
                    "type": "semantic_vad",
                    # Balance natural thinking pauses with prompt turn-taking.
                    "eagerness": "medium",
                    "create_response": True,
                    "interrupt_response": True,
                },
            },
            "output": {"voice": settings.OPENAI_REALTIME_VOICE, "speed": 0.88},
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
            "base_instructions": base_instructions,
            "pedagogical_state": authoritative_state or {},
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
