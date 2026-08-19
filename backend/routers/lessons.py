from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..database import get_db
from ..models import Lesson, LessonDay, Child, StudentProgress, QuizQuestion, LessonSession, AIInteraction
from ..schemas import AITutorChatRequest, AITutorChatResponse, QuizSubmission, QuizResultOut
from ..services.openai_service import get_tutor_response
from ..utils.levels import get_level_label

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

TAB_NAMES = ["Objectives", "Learn", "Examples", "Words", "Remember"]

class SessionUpdate(BaseModel):
    child_id: int
    lesson_id: int
    day_number: int = 1
    current_tab: int = 0
    messages: Optional[List[Dict[str, str]]] = []
    is_completed: bool = False

@router.post("/chat-guidance", response_model=AITutorChatResponse)
async def tutor_chat_guidance(req: AITutorChatRequest, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == req.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    child = db.query(Child).filter(Child.id == req.child_id).first()
    student_name = child.name if child else "Student"
    edu_sys = child.education_system if child else "UK"
    level_num = child.level if child and child.level is not None else lesson.level
    level_label = get_level_label(level_num, edu_sys)

    tab_idx = max(0, min(req.current_tab, 4))
    tab_name = TAB_NAMES[tab_idx]

    # Map content based on tab
    tab_contents = [
        ", ".join(lesson.objectives or []),
        lesson.learn_content or "",
        str(lesson.examples or []),
        str(lesson.vocabulary or []),
        ", ".join(lesson.key_points or [])
    ]
    current_content = tab_contents[tab_idx]

    context = {
        "student_name": student_name,
        "level": level_num,
        "level_label": level_label,
        "subject": lesson.unit.subject.title if lesson.unit and lesson.unit.subject else "General",
        "unit_title": lesson.unit.title if lesson.unit else "General Unit",
        "lesson_topic": lesson.title,
        "day_number": 1,
        "activity_type": "Explore",
        "current_tab_name": tab_name,
        "learning_objectives": lesson.objectives or [],
        "key_concept": lesson.learn_content or "",
        "tab_content": current_content
    }

    guidance = await get_tutor_response(
        student_name=student_name,
        context=context,
        user_prompt=req.user_prompt,
        history=req.message_history
    )

    # Log interaction for audit
    interaction = AIInteraction(
        child_id=req.child_id,
        lesson_id=req.lesson_id,
        day_number=1,
        role="assistant",
        prompt=req.user_prompt or f"Tab guidance: {tab_name}",
        response=guidance["tutor_reply"]
    )
    db.add(interaction)
    db.commit()

    return guidance

@router.post("/session")
def update_lesson_session(sess_in: SessionUpdate, db: Session = Depends(get_db)):
    """Updates or creates a lightweight resumable lesson session."""
    session = db.query(LessonSession).filter(
        LessonSession.child_id == sess_in.child_id,
        LessonSession.lesson_id == sess_in.lesson_id
    ).first()

    if not session:
        session = LessonSession(
            child_id=sess_in.child_id,
            lesson_id=sess_in.lesson_id,
            day_number=sess_in.day_number,
            current_tab=sess_in.current_tab,
            messages=sess_in.messages or [],
            is_completed=sess_in.is_completed
        )
        db.add(session)
    else:
        session.day_number = sess_in.day_number
        session.current_tab = sess_in.current_tab
        session.messages = sess_in.messages or []
        session.is_completed = sess_in.is_completed

    db.commit()
    return {"status": "saved", "current_tab": session.current_tab, "day_number": session.day_number}

@router.get("/session/{child_id}/{lesson_id}")
def get_lesson_session(child_id: int, lesson_id: int, db: Session = Depends(get_db)):
    """Retrieves existing resumable session if student returns to this lesson."""
    session = db.query(LessonSession).filter(
        LessonSession.child_id == child_id,
        LessonSession.lesson_id == lesson_id
    ).first()

    if not session:
        return {"current_tab": 0, "day_number": 1, "messages": [], "is_completed": False}

    return {
        "current_tab": session.current_tab,
        "day_number": session.day_number,
        "messages": session.messages,
        "is_completed": session.is_completed
    }

@router.post("/submit-quiz", response_model=QuizResultOut)
def submit_quiz(sub: QuizSubmission, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == sub.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    child = db.query(Child).filter(Child.id == sub.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    questions = db.query(QuizQuestion).filter(QuizQuestion.lesson_id == sub.lesson_id).all()
    if not questions:
        # Fallback 100%
        return QuizResultOut(score=3, total_questions=3, percentage=100, xp_earned=35, passed=True, feedback="Great job!")

    correct_count = 0
    total_questions = len(questions)
    answer_map = {a.question_id: str(a.selected_answer).strip().lower() for a in sub.answers if a.selected_answer is not None}

    for q in questions:
        expected = str(q.correct_answer).strip().lower()
        actual = answer_map.get(q.id)
        if actual == expected:
            correct_count += 1

    percentage = int((correct_count / total_questions) * 100) if total_questions > 0 else 100
    xp_earned = 20 + (correct_count * 5)

    # Award XP
    child.xp += xp_earned

    # Record or update StudentProgress immediately in database
    progress = db.query(StudentProgress).filter(
        StudentProgress.child_id == sub.child_id,
        StudentProgress.lesson_id == sub.lesson_id
    ).first()

    if not progress:
        progress = StudentProgress(
            child_id=sub.child_id,
            lesson_id=sub.lesson_id,
            day_number=1,
            activity_type="Practice",
            status="completed" if percentage >= 60 else "in_progress",
            quiz_score=percentage,
            mastery_status="mastered" if percentage >= 80 else ("competent" if percentage >= 60 else "developing")
        )
        db.add(progress)
    else:
        if percentage >= 60:
            progress.status = "completed"
        progress.quiz_score = percentage
        progress.mastery_status = "mastered" if percentage >= 80 else ("competent" if percentage >= 60 else "developing")

    db.commit()

    return QuizResultOut(
        score=correct_count,
        total_questions=total_questions,
        percentage=percentage,
        xp_earned=xp_earned,
        passed=percentage >= 60,
        feedback="Perfect score! You're ready to submit your learning evidence. 🏆" if percentage == 100 else f"You scored {percentage}% ({correct_count}/{total_questions})! Great practice—let's prove your learning."
    )
