import re
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..database import get_db
from ..models import Lesson, LessonDay, Child, StudentProgress, QuizQuestion, LessonSession, AIInteraction, User, Unit
from ..schemas import AITutorChatRequest, AITutorChatResponse, QuizSubmission, QuizResultOut
from ..services.openai_service import get_tutor_response, is_legacy_or_markdown_heavy, evaluate_academic_response
from ..utils.levels import get_level_label
from .auth import get_current_user, authorize_child

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

TAB_NAMES = ["Objectives", "Learn", "Examples", "Words", "Remember"]

ACKNOWLEDGEMENT_PHRASES = {
    "yes", "yeah", "yep", "yup", "okay", "ok", "i'm ready", "im ready", "ready",
    "let's go", "lets go", "sure", "i understand", "i can", "continue", "got it",
    "alright", "all right", "sounds good", "next", "i'm good", "im good", "good",
    "fine", "i am good", "i'm fine", "doing well", "great", "cool", "understood"
}

REPEAT_OR_CLARIFICATION_PHRASES = {
    re.sub(r'[^\w\s]', '', p.lower()) for p in [
        "repeat", "say that again", "say again", "repeat that", "repeat the question",
        "can you repeat", "could you repeat", "what did you say", "i missed that",
        "i didnt hear", "i didn't hear", "go again", "one more time", "pardon",
        "excuse me", "what was the question", "what was that", "can you say that again",
        "i was not paying attention", "i wasn't paying attention", "how many", "how many slices",
        "how much", "tell me again", "explain that again"
    ]
}

def is_acknowledgement(text: Optional[str]) -> bool:
    """Classifies whether a student utterance is a conversational acknowledgement rather than academic evidence."""
    if not text:
        return False
    clean = re.sub(r'[^\w\s]', '', text.strip().lower())
    if clean in ACKNOWLEDGEMENT_PHRASES:
        return True
    words = clean.split()
    if len(words) <= 4 and (
        words[0] in {"yes", "ok", "okay", "ready", "sure", "good", "fine", "yeah", "yep", "got", "alright", "sounds", "understood"}
        or clean in {"okay sounds good", "sounds good to me", "yes im ready", "yes i am ready", "sure lets go", "alright lets go", "im ready to learn", "i am ready to learn"}
    ):
        return True
    return False

def is_repeat_or_clarification(text: Optional[str]) -> bool:
    """Classifies whether a student utterance is asking to repeat or clarify instructions."""
    if not text:
        return False
    clean = re.sub(r'[^\w\s]', '', text.strip().lower())
    for phrase in REPEAT_OR_CLARIFICATION_PHRASES:
        if phrase in clean:
            return True
    return False

def advance_pedagogical_state(
    current_state: Optional[Dict[str, Any]],
    user_prompt: Optional[str],
    is_opening_turn: bool = False,
    eval_result: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    event_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Advances the backend-authoritative pedagogical state machine.
    Enforces minimum 3 worked examples, validates academic response quality,
    prevents incorrect or acknowledgement responses from advancing, preserves active tasks
    across repetitions/clarifications, and ensures completion is strictly backend-governed.
    """
    state = dict(current_state or {})
    if not state or is_opening_turn:
        return {
            "current_phase": "GREETING",
            "current_objective": "",
            "worked_examples_required": 3,
            "worked_examples_completed": 0,
            "worked_examples_delivered": {"1": False, "2": False, "3": False},
            "understanding_check_status": "pending",
            "guided_practice_status": "pending",
            "application_status": "pending",
            "mastery_status": "in_progress",
            "remediation_count": 0,
            "active_task": "",
            "active_question": "",
            "active_expected_concept": "",
            "active_phase": "",
            "pending_delivery_token": "",
            "pending_delivery_phase": "",
            "is_repeat_turn": False,
            "practice_ready": False
        }

    phase = state.get("current_phase", "GREETING")

    # Teacher-led content advances only after the current authoritative playback
    # reports completion with its server-issued delivery token.
    if event_type == "teacher_delivery_completed":
        delivered = dict(state.get("worked_examples_delivered") or {"1": False, "2": False, "3": False})
        if phase == "TEACHING":
            state["current_phase"] = "WORKED_EXAMPLE_1"
        elif phase == "WORKED_EXAMPLE_1":
            delivered["1"] = True
            state["worked_examples_completed"] = sum(bool(delivered[str(i)]) for i in (1, 2, 3))
            state["current_phase"] = "WORKED_EXAMPLE_2"
        elif phase == "WORKED_EXAMPLE_2":
            delivered["2"] = True
            state["worked_examples_completed"] = sum(bool(delivered[str(i)]) for i in (1, 2, 3))
            state["current_phase"] = "WORKED_EXAMPLE_3"
        elif phase == "WORKED_EXAMPLE_3":
            delivered["3"] = True
            state["worked_examples_completed"] = sum(bool(delivered[str(i)]) for i in (1, 2, 3))
            if state["worked_examples_completed"] >= state.get("worked_examples_required", 3):
                state["current_phase"] = "UNDERSTANDING_CHECK"
        elif phase == "LESSON_SUMMARY":
            state["practice_ready"] = True
            state["current_phase"] = "PRACTICE_READY"
        state["worked_examples_delivered"] = delivered
        state["pending_delivery_token"] = ""
        state["pending_delivery_phase"] = ""
        state["is_repeat_turn"] = False
        return state

    # Clarification/repeat requests MUST preserve active content and not advance or penalize
    if is_repeat_or_clarification(user_prompt):
        state["is_repeat_turn"] = True
        return state

    state["is_repeat_turn"] = False
    examples_done = state.get("worked_examples_completed", 0)
    examples_req = state.get("worked_examples_required", 3)
    user_ack = is_acknowledgement(user_prompt)

    if phase == "GREETING":
        state["current_phase"] = "TEACHING"

    elif phase in {"TEACHING", "WORKED_EXAMPLE_1", "WORKED_EXAMPLE_2", "WORKED_EXAMPLE_3", "LESSON_SUMMARY"}:
        # Student speech (including micro-interactions) never marks teacher content delivered.
        pass

    elif phase == "UNDERSTANDING_CHECK":
        if user_ack:
            # Acknowledgement is NOT academic proof of understanding
            state["understanding_check_status"] = "pending"
        elif evaluation_allows_advance(phase, eval_result):
            # Academic response verified as CORRECT -> advance to GUIDED_PRACTICE
            state["understanding_check_status"] = "passed"
            state["current_phase"] = "GUIDED_PRACTICE"
        else:
            # Incorrect or unverified response -> keep in phase for remediation
            state["understanding_check_status"] = "needs_remediation"
            state["remediation_count"] = state.get("remediation_count", 0) + 1

    elif phase == "GUIDED_PRACTICE":
        if user_ack:
            # Acknowledgement cannot complete guided practice
            state["guided_practice_status"] = "pending"
        elif evaluation_allows_advance(phase, eval_result):
            # Guided participation verified -> advance to APPLICATION
            state["guided_practice_status"] = "passed"
            state["current_phase"] = "APPLICATION"
            if context:
                state["active_task"] = context.get("real_world_context", "") or "Real-world application task"
        else:
            state["guided_practice_status"] = "in_progress"
            state["remediation_count"] = state.get("remediation_count", 0) + 1

    elif phase == "APPLICATION":
        if user_ack:
            # Acknowledgement is NOT reasoning
            state["application_status"] = "pending"
        elif evaluation_allows_advance(phase, eval_result):
            # Application verified -> advance to MASTERY_CHECK
            state["application_status"] = "passed"
            state["current_phase"] = "MASTERY_CHECK"
        else:
            state["application_status"] = "in_progress"
            state["remediation_count"] = state.get("remediation_count", 0) + 1

    elif phase == "MASTERY_CHECK":
        if user_ack:
            state["mastery_status"] = "in_progress"
        elif evaluation_allows_advance(phase, eval_result):
            # Real evidence demonstrated & verified -> advance to LESSON_SUMMARY (not immediately PRACTICE_READY)
            state["mastery_status"] = "mastered"
            state["current_phase"] = "LESSON_SUMMARY"
        else:
            state["mastery_status"] = "in_progress"
            state["remediation_count"] = state.get("remediation_count", 0) + 1

    elif phase == "PRACTICE_READY":
        state["practice_ready"] = True

    return state


def evaluation_allows_advance(phase: str, eval_result: Optional[Dict[str, Any]]) -> bool:
    """Backend-enforced academic advancement policy; LLM can_advance is advisory only."""
    if not eval_result:
        return False
    result = str(eval_result.get("result", "unclear")).lower()
    if result == "correct":
        return True
    if phase == "GUIDED_PRACTICE" and result == "partially_correct":
        return bool(eval_result.get("guided_contribution_sufficient", False))
    return False


def _extract_active_question(text: str) -> str:
    """Returns the final spoken question without inventing curriculum content."""
    if not text:
        return ""
    matches = re.findall(r"([^?.!]*\?)", text.strip(), flags=re.MULTILINE)
    return matches[-1].strip() if matches else ""


def populate_active_academic_state(state: Dict[str, Any], guidance: Dict[str, Any], context: Dict[str, Any]) -> None:
    phase = state.get("current_phase", "")
    if phase not in {"UNDERSTANDING_CHECK", "GUIDED_PRACTICE", "APPLICATION", "MASTERY_CHECK"}:
        return
    # A repeat/remediation response reuses the authoritative original question.
    if state.get("is_repeat_turn") or (state.get("active_phase") == phase and state.get("active_question")):
        return
    tutor_text = guidance.get("tutor_reply", "").strip()
    question = _extract_active_question(tutor_text) or tutor_text
    state["active_question"] = question
    if phase == "APPLICATION":
        state["active_task"] = context.get("real_world_context", "") or question
    else:
        state["active_task"] = question
    objectives = context.get("learning_objectives") or []
    expected = context.get("key_concept") or (objectives[0] if isinstance(objectives, list) and objectives else str(objectives))
    state["active_expected_concept"] = str(expected)[:1000]
    state["active_phase"] = phase

class SessionUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    child_id: int
    lesson_id: int
    day_number: int = 1
    current_tab: int = 0
    messages: Optional[List[Dict[str, str]]] = []


class RealtimePedagogyEvent(BaseModel):
    model_config = {"extra": "forbid"}
    child_id: int
    lesson_id: int
    day_number: int = 1
    event_type: str
    student_response: Optional[str] = None
    assistant_response: Optional[str] = None
    delivery_token: Optional[str] = None


ACADEMIC_PHASES = {"UNDERSTANDING_CHECK", "GUIDED_PRACTICE", "APPLICATION", "MASTERY_CHECK"}
TEACHER_DELIVERY_PHASES = {"TEACHING", "WORKED_EXAMPLE_1", "WORKED_EXAMPLE_2", "WORKED_EXAMPLE_3", "LESSON_SUMMARY"}


def _lesson_context(lesson, active_day, child) -> Dict[str, Any]:
    level_num = child.level if child.level is not None else lesson.level
    return {
        "student_name": child.name,
        "level": level_num,
        "level_label": get_level_label(level_num, child.education_system),
        "subject": lesson.unit.subject.title if lesson.unit and lesson.unit.subject else "General",
        "unit_title": lesson.unit.title if lesson.unit else "General Unit",
        "lesson_title": lesson.title,
        "lesson_topic": lesson.topic or lesson.title,
        "day_number": active_day.day_number if active_day else 1,
        "activity_type": active_day.activity_type if active_day else "Explore",
        "curriculum_country": lesson.curriculum_country or "",
        "learning_objectives": (active_day.learning_objectives if active_day else None) or lesson.objectives or [],
        "key_concept": (active_day.key_concept if active_day else None) or lesson.learn_content or "",
        "ai_script": active_day.ai_script if active_day else "",
        "examples": (active_day.practice_questions if active_day and active_day.practice_questions else lesson.examples) or [],
        "real_world_context": (active_day.real_world_context if active_day else None) or "Use an age-appropriate everyday example.",
    }


def _realtime_phase_directive(state: Dict[str, Any], eval_result: Optional[Dict[str, Any]] = None) -> str:
    phase = state.get("current_phase", "GREETING")
    common = (
        f"Authoritative phase: {phase}. Do not advance beyond this phase yourself. "
        "Keep the spoken turn concise and natural. "
    )
    directives = {
        "TEACHING": "Greet the learner by name and teach the key concept briefly, then stop speaking.",
        "WORKED_EXAMPLE_1": "Deliver worked example 1 step by step, then stop speaking.",
        "WORKED_EXAMPLE_2": "Deliver a distinct worked example 2 step by step, then stop speaking.",
        "WORKED_EXAMPLE_3": "Deliver a distinct worked example 3 step by step, then stop speaking.",
        "UNDERSTANDING_CHECK": "Ask exactly one short understanding-check question and wait for the learner.",
        "GUIDED_PRACTICE": "Give one guided-practice task, ask one question, and wait for the learner.",
        "APPLICATION": "Give one curriculum-grounded real-life application task and wait for the learner.",
        "MASTERY_CHECK": "Ask exactly one independent mastery question and wait for the learner.",
        "LESSON_SUMMARY": "Give a brief lesson summary and encouragement, then stop speaking.",
        "PRACTICE_READY": "The backend has unlocked practice. Briefly tell the learner the quiz is ready.",
    }
    evaluation = ""
    if eval_result:
        evaluation = (
            " Backend evaluation result: "
            f"{eval_result.get('result', 'unclear')}. "
            f"Feedback basis: {eval_result.get('feedback', '')}. "
            "Follow this result; do not replace it with your own mastery decision."
        )
    if state.get("is_repeat_turn"):
        return common + "Repeat or rephrase the preserved active question/task without changing it."
    return common + directives.get(phase, "Continue only within the current phase and ask one question at a time.") + evaluation


@router.post("/realtime-event")
async def realtime_pedagogy_event(
    payload: RealtimePedagogyEvent,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compact authoritative state bridge for the persistent Realtime classroom."""
    child = authorize_child(db, current_user, payload.child_id)
    lesson = db.query(Lesson).filter(Lesson.id == payload.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    active_day = next((day for day in lesson.days if day.day_number == payload.day_number), None)
    if lesson.days and not active_day:
        raise HTTPException(status_code=404, detail="Lesson day not found")
    if active_day and current_user.role != "admin" and (active_day.status or "").lower() not in {"active", "published"}:
        raise HTTPException(status_code=404, detail="Lesson day not found")

    session = db.query(LessonSession).filter(
        LessonSession.child_id == payload.child_id,
        LessonSession.lesson_id == payload.lesson_id,
        LessonSession.day_number == payload.day_number,
    ).first()
    state = dict(session.pedagogical_state or {}) if session else {}
    response_phase = state.get("current_phase")
    context = _lesson_context(lesson, active_day, child)
    eval_result = None

    if payload.event_type == "start_class":
        if not state:
            state = advance_pedagogical_state(None, None, is_opening_turn=True)
        if state.get("current_phase") == "GREETING":
            state = advance_pedagogical_state(state, "start class", context=context)
    elif payload.event_type == "teacher_delivery_completed":
        if state.get("current_phase") not in TEACHER_DELIVERY_PHASES:
            raise HTTPException(status_code=409, detail="No teacher delivery is awaiting completion")
        expected = state.get("pending_delivery_token")
        if not expected or not secrets.compare_digest(payload.delivery_token or "", expected):
            raise HTTPException(status_code=409, detail="Stale or invalid teacher delivery token")
        if state.get("pending_delivery_phase") != state.get("current_phase"):
            raise HTTPException(status_code=409, detail="Teacher delivery phase is stale")
        state = advance_pedagogical_state(
            state,
            None,
            context=context,
            event_type="teacher_delivery_completed",
        )
    elif payload.event_type == "academic_response":
        phase = state.get("current_phase")
        if phase not in ACADEMIC_PHASES:
            raise HTTPException(status_code=409, detail="The current phase is not accepting academic evidence")
        response_text = (payload.student_response or "").strip()
        if not response_text:
            raise HTTPException(status_code=400, detail="Student response is required")
        clarification = is_repeat_or_clarification(response_text)
        acknowledgement = is_acknowledgement(response_text)
        if not clarification and not acknowledgement:
            eval_result = await evaluate_academic_response(
                student_name=child.name,
                context=context,
                phase=phase,
                student_response=response_text,
                last_tutor_question=state.get("active_question") or "",
            )
        state = advance_pedagogical_state(
            state,
            response_text,
            eval_result=eval_result,
            context=context,
        )
    elif payload.event_type == "assistant_response_completed":
        assistant_text = (payload.assistant_response or "").strip()
        if assistant_text:
            populate_active_academic_state(state, {"tutor_reply": assistant_text}, context)
    else:
        raise HTTPException(status_code=400, detail="Unsupported realtime pedagogy event")

    if state.get("current_phase") in TEACHER_DELIVERY_PHASES and not state.get("pending_delivery_token"):
        state["pending_delivery_token"] = secrets.token_urlsafe(24)
        state["pending_delivery_phase"] = state.get("current_phase")

    messages = list(session.messages or []) if session else []
    if payload.student_response:
        messages.append({"sender": "me", "text": payload.student_response})
    if payload.assistant_response:
        messages.append({
            "sender": "tutor",
            "text": payload.assistant_response,
            "phase": response_phase or state.get("current_phase"),
        })
    messages = messages[-80:]

    if not session:
        session = LessonSession(
            child_id=payload.child_id,
            lesson_id=payload.lesson_id,
            day_number=payload.day_number,
            current_tab=0,
            pedagogical_state=state,
            messages=messages,
            is_completed=state.get("practice_ready", False),
        )
        db.add(session)
    else:
        session.pedagogical_state = state
        session.messages = messages
        session.is_completed = bool(state.get("practice_ready"))
    db.commit()

    return {
        "pedagogical_state": state,
        "practice_ready": bool(state.get("practice_ready")),
        "delivery_token": state.get("pending_delivery_token") or None,
        "phase_instruction": _realtime_phase_directive(state, eval_result),
        "evaluation": eval_result,
    }

@router.post("/chat-guidance", response_model=AITutorChatResponse)
async def tutor_chat_guidance(
    req: AITutorChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lesson = db.query(Lesson).filter(Lesson.id == req.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    child = authorize_child(db, current_user, req.child_id)
    student_name = child.name
    edu_sys = child.education_system
    level_num = child.level if child.level is not None else lesson.level
    level_label = get_level_label(level_num, edu_sys)

    tab_idx = max(0, min(req.current_tab, 4))
    tab_name = TAB_NAMES[tab_idx]

    # Fetch active session to retrieve and advance authoritative pedagogical state
    session = db.query(LessonSession).filter(
        LessonSession.child_id == req.child_id,
        LessonSession.lesson_id == req.lesson_id,
        LessonSession.day_number == req.day_number
    ).first()

    current_ped_state = session.pedagogical_state if session and session.pedagogical_state else None
    opening_prompt = (req.user_prompt or "").strip().lower() in {
        "welcome", "hello", "hi", "hey", "good morning", "good afternoon",
        "start", "start lesson", "begin", "let's begin", "lets begin",
    }
    # Only a genuinely new session can be an opening turn. A later "hello"
    # must never reset an in-progress lesson back to GREETING.
    is_opening_turn = not req.event_type and not current_ped_state and (
        not req.user_prompt or opening_prompt
    )

    if req.event_type == "teacher_delivery_completed":
        if not current_ped_state:
            raise HTTPException(status_code=409, detail="No teacher delivery is awaiting completion")
        expected_token = current_ped_state.get("pending_delivery_token")
        expected_phase = current_ped_state.get("pending_delivery_phase")
        if not expected_token or not secrets.compare_digest(req.delivery_token or "", expected_token):
            raise HTTPException(status_code=409, detail="Stale or invalid teacher delivery token")
        if expected_phase != current_ped_state.get("current_phase"):
            raise HTTPException(status_code=409, detail="Teacher delivery phase is stale")

    active_day = next((d for d in lesson.days if d.day_number == req.day_number), None)
    if lesson.days and not active_day:
        raise HTTPException(status_code=404, detail="Lesson day not found")
    if active_day and current_user.role != "admin" and (active_day.status or "").lower() not in {"active", "published"}:
        raise HTTPException(status_code=404, detail="Lesson day not found")
    real_world_context = (
        (active_day.real_world_context if active_day else None)
        or "Use an age-appropriate everyday example (e.g. sharing snacks, measuring toys, or household objects)."
    )

    context = {
        "student_name": student_name,
        "level": level_num,
        "level_label": level_label,
        "subject": lesson.unit.subject.title if lesson.unit and lesson.unit.subject else "General",
        "unit_title": lesson.unit.title if lesson.unit else "General Unit",
        "lesson_title": lesson.title,
        "lesson_topic": lesson.title,
        "day_number": req.day_number,
        "activity_type": active_day.activity_type if active_day else "Explore",
        "curriculum_country": lesson.curriculum_country or "",
        "estimated_duration": active_day.estimated_duration if active_day else "20 mins",
        "learning_objectives": (active_day.learning_objectives if active_day else None) or lesson.objectives or [],
        "key_concept": (active_day.key_concept if active_day else None) or lesson.learn_content or "",
        "ai_script": active_day.ai_script if active_day else "",
        "visual_support": active_day.visual_support if active_day else "",
        "origin_of_knowledge": active_day.origin_of_knowledge if active_day else "",
        "video_url": active_day.video_url if active_day else "",
        "practice_questions": active_day.practice_questions if active_day else [],
        "examples": (active_day.practice_questions if active_day and active_day.practice_questions else lesson.examples) or [],
        "real_world_context": real_world_context,
        "vocabulary": (active_day.vocabulary if active_day and active_day.vocabulary else lesson.vocabulary) or [],
        "reading_recommendations": active_day.reading_recommendations if active_day else [],
        "key_points": lesson.key_points or [],
        "bible_reference": active_day.bible_reference if active_day else "",
        "biblical_theme": active_day.biblical_theme if active_day else "",
        "bible_reflection": (active_day.biblical_application if active_day else None) or lesson.bible_reflection or "",
        "character_connection": (active_day.character_reference if active_day else None) or lesson.character_connection or ""
    }

    # Evaluate academic response quality if in an evaluative phase and input is not an acknowledgement or repeat request
    eval_result = None
    is_clarification = is_repeat_or_clarification(req.user_prompt)
    if current_ped_state and current_ped_state.get("current_phase") in {
        "UNDERSTANDING_CHECK", "GUIDED_PRACTICE", "APPLICATION", "MASTERY_CHECK"
    } and not is_opening_turn and not is_acknowledgement(req.user_prompt) and not is_clarification:
        last_tutor_msg = current_ped_state.get("active_question") or next(
            (m.get("text") for m in reversed(req.message_history or []) if m.get("sender") == "tutor"), None
        )
        eval_result = await evaluate_academic_response(
            student_name=student_name,
            context=context,
            phase=current_ped_state.get("current_phase"),
            student_response=req.user_prompt or "",
            last_tutor_question=last_tutor_msg
        )

    new_ped_state = advance_pedagogical_state(
        current_ped_state,
        req.user_prompt,
        is_opening_turn=is_opening_turn,
        eval_result=eval_result,
        context=context,
        event_type=req.event_type
    )
    # If the learner initiates the class with a greeting, acknowledge it and
    # launch the scheduled teaching content in the same response. Requiring a
    # second "proceed" turn creates a generic assistant-like opening.
    if is_opening_turn and req.user_prompt:
        new_ped_state = advance_pedagogical_state(
            new_ped_state,
            req.user_prompt,
            context=context,
        )

    guidance = await get_tutor_response(
        student_name=student_name,
        context=context,
        # A delivery confirmation may arrive with the learner's response. Keep
        # that response in the conversational turn while the server advances
        # the already-delivered teacher phase.
        user_prompt=req.user_prompt or "Continue the current lesson from the authoritative phase.",
        history=req.message_history,
        pedagogical_state=new_ped_state,
        eval_result=eval_result
    )

    populate_active_academic_state(new_ped_state, guidance, context)

    requires_delivery_confirmation = new_ped_state.get("current_phase") in {
        "TEACHING", "WORKED_EXAMPLE_1", "WORKED_EXAMPLE_2", "WORKED_EXAMPLE_3", "LESSON_SUMMARY"
    }
    issued_delivery_token = None
    if requires_delivery_confirmation:
        issued_delivery_token = secrets.token_urlsafe(24)
        new_ped_state["pending_delivery_token"] = issued_delivery_token
        new_ped_state["pending_delivery_phase"] = new_ped_state.get("current_phase")

    # Persist updated pedagogical state into session
    if not session:
        session = LessonSession(
            child_id=req.child_id,
            lesson_id=req.lesson_id,
            day_number=req.day_number,
            current_tab=req.current_tab,
            pedagogical_state=new_ped_state,
            messages=req.message_history or [],
            is_completed=new_ped_state.get("practice_ready", False)
        )
        db.add(session)
    else:
        session.pedagogical_state = new_ped_state
        if new_ped_state.get("practice_ready", False):
            session.is_completed = True

    # Log interaction for audit
    interaction = AIInteraction(
        child_id=req.child_id,
        lesson_id=req.lesson_id,
        day_number=req.day_number,
        role="assistant",
        prompt=req.user_prompt or f"Tab guidance: {tab_name}",
        response=guidance["tutor_reply"]
    )
    db.add(interaction)
    db.commit()

    return AITutorChatResponse(
        tutor_reply=guidance["tutor_reply"],
        speech_text=guidance["speech_text"],
        pedagogical_state=new_ped_state,
        practice_ready=new_ped_state.get("practice_ready", False),
        delivery_token=issued_delivery_token,
        requires_delivery_confirmation=requires_delivery_confirmation
    )

@router.post("/session")
def update_lesson_session(
    sess_in: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates or creates a lightweight resumable lesson session."""
    authorize_child(db, current_user, sess_in.child_id)
    session = db.query(LessonSession).filter(
        LessonSession.child_id == sess_in.child_id,
        LessonSession.lesson_id == sess_in.lesson_id,
        LessonSession.day_number == sess_in.day_number
    ).first()

    if not session:
        session = LessonSession(
            child_id=sess_in.child_id,
            lesson_id=sess_in.lesson_id,
            day_number=sess_in.day_number,
            current_tab=sess_in.current_tab,
            pedagogical_state={},
            messages=sess_in.messages or [],
            is_completed=False
        )
        db.add(session)
    else:
        session.day_number = sess_in.day_number
        session.current_tab = sess_in.current_tab
        session.messages = sess_in.messages or []

    db.commit()
    return {"status": "saved", "current_tab": session.current_tab, "day_number": session.day_number, "pedagogical_state": session.pedagogical_state}

@router.get("/session/{child_id}/{lesson_id}/{day_number}")
def get_lesson_session(
    child_id: int,
    lesson_id: int,
    day_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves existing resumable session if student returns to this lesson, discarding contaminated legacy history."""
    authorize_child(db, current_user, child_id)
    session = db.query(LessonSession).filter(
        LessonSession.child_id == child_id,
        LessonSession.lesson_id == lesson_id,
        LessonSession.day_number == day_number
    ).first()

    if not session or not session.messages:
        state = session.pedagogical_state if session and session.pedagogical_state else {}
        return {
            "current_tab": 0,
            "day_number": day_number,
            "messages": [],
            "is_completed": session.is_completed if session else False,
            "pedagogical_state": state,
            "practice_ready": bool(state.get("practice_ready") or state.get("current_phase") == "PRACTICE_READY")
        }

    # If previous session messages contain bloated markdown or numbered lists, discard them so tutor starts fresh
    has_legacy = any(is_legacy_or_markdown_heavy(m.get("text", "")) for m in session.messages)
    if has_legacy:
        session.messages = []
        db.commit()
        return {
            "current_tab": 0,
            "day_number": day_number,
            "messages": [],
            "is_completed": False,
            "pedagogical_state": session.pedagogical_state or {},
            "practice_ready": bool((session.pedagogical_state or {}).get("practice_ready") or (session.pedagogical_state or {}).get("current_phase") == "PRACTICE_READY")
        }

    return {
        "current_tab": session.current_tab,
        "day_number": session.day_number,
        "messages": session.messages,
        "is_completed": session.is_completed,
        "pedagogical_state": session.pedagogical_state or {},
        "practice_ready": bool((session.pedagogical_state or {}).get("practice_ready") or (session.pedagogical_state or {}).get("current_phase") == "PRACTICE_READY")
    }

def _ready_session(db: Session, child_id: int, lesson_id: int, day_number: int) -> LessonSession:
    session = db.query(LessonSession).filter(
        LessonSession.child_id == child_id,
        LessonSession.lesson_id == lesson_id,
        LessonSession.day_number == day_number
    ).first()
    state = session.pedagogical_state if session else {}
    if not session or not (
        state.get("practice_ready") is True or state.get("current_phase") == "PRACTICE_READY"
    ):
        raise HTTPException(status_code=409, detail="Lesson is not ready for practice")
    return session


def _quiz_questions_for_lesson(db: Session, lesson: Lesson):
    """Return this lesson's quiz, or an exact structured-curriculum duplicate's quiz."""
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.lesson_id == lesson.id
    ).order_by(QuizQuestion.id.asc()).all()
    if questions:
        return questions

    topic_key = " ".join((lesson.topic or "").lower().split())
    if not topic_key or not lesson.unit:
        return []

    candidates = db.query(Lesson).join(Unit).filter(
        Lesson.id != lesson.id,
        Lesson.level == lesson.level,
        Unit.subject_id == lesson.unit.subject_id,
    ).all()
    for candidate in candidates:
        if " ".join((candidate.topic or "").lower().split()) != topic_key:
            continue
        candidate_questions = db.query(QuizQuestion).filter(
            QuizQuestion.lesson_id == candidate.id
        ).order_by(QuizQuestion.id.asc()).all()
        if candidate_questions:
            return candidate_questions
    return []


def _require_published_day(lesson: Lesson, day_number: int, current_user: User) -> None:
    day = next((item for item in lesson.days if item.day_number == day_number), None)
    if lesson.days and (not day or (current_user.role != "admin" and (day.status or "").lower() not in {"active", "published"})):
        raise HTTPException(status_code=404, detail="Lesson day not found")

@router.get("/{lesson_id}/quiz")
def get_quiz(
    lesson_id: int,
    child_id: int,
    day_number: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    authorize_child(db, current_user, child_id)
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _require_published_day(lesson, day_number, current_user)
    _ready_session(db, child_id, lesson_id, day_number)
    questions = _quiz_questions_for_lesson(db, lesson)
    if not questions:
        raise HTTPException(status_code=409, detail="No reviewed quiz is configured for this lesson")
    return questions

@router.post("/submit-quiz", response_model=QuizResultOut)
def submit_quiz(
    sub: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lesson = db.query(Lesson).filter(Lesson.id == sub.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _require_published_day(lesson, sub.day_number, current_user)
    
    child = authorize_child(db, current_user, sub.child_id)
    _ready_session(db, sub.child_id, sub.lesson_id, sub.day_number)

    questions = _quiz_questions_for_lesson(db, lesson)
    if not questions:
        raise HTTPException(status_code=409, detail="No reviewed quiz is configured for this lesson")

    correct_count = 0
    total_questions = len(questions)
    answer_map = {a.question_id: str(a.selected_answer).strip().lower() for a in sub.answers if a.selected_answer is not None}

    for q in questions:
        expected = str(q.correct_answer).strip().lower()
        actual = answer_map.get(q.id)
        if actual == expected:
            correct_count += 1

    percentage = int((correct_count / total_questions) * 100) if total_questions > 0 else 100
    proposed_xp = 20 + (correct_count * 5)

    # Record or update StudentProgress immediately in database
    progress = db.query(StudentProgress).filter(
        StudentProgress.child_id == sub.child_id,
        StudentProgress.lesson_id == sub.lesson_id,
        StudentProgress.day_number == sub.day_number
    ).first()

    if not progress:
        progress = StudentProgress(
            child_id=sub.child_id,
            lesson_id=sub.lesson_id,
            day_number=sub.day_number,
            activity_type="Practice",
            status="completed" if percentage >= 60 else "in_progress",
            quiz_score=percentage,
            mastery_status="mastered" if percentage >= 80 else ("competent" if percentage >= 60 else "developing"),
            quiz_xp_awarded=True
        )
        db.add(progress)
        xp_earned = proposed_xp
        child.xp += xp_earned
    else:
        if percentage >= 60:
            progress.status = "completed"
        progress.quiz_score = percentage
        progress.mastery_status = "mastered" if percentage >= 80 else ("competent" if percentage >= 60 else "developing")
        if not progress.quiz_xp_awarded:
            progress.quiz_xp_awarded = True
            xp_earned = proposed_xp
            child.xp += xp_earned
        else:
            xp_earned = 0

    db.commit()

    return QuizResultOut(
        score=correct_count,
        total_questions=total_questions,
        percentage=percentage,
        xp_earned=xp_earned,
        passed=percentage >= 60,
        feedback="Perfect score! You're ready to submit your learning evidence. 🏆" if percentage == 100 else f"You scored {percentage}% ({correct_count}/{total_questions})! Great practice—let's prove your learning."
    )
