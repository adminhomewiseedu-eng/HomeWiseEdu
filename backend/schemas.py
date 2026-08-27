from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
import datetime

# Auth schemas
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "parent"

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

# Subject schemas
class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    icon: str
    color: str
    description: Optional[str] = None

# Child schemas
class ChildCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str
    age: int = 9
    date_of_birth: Optional[str] = None
    education_system: str = "UK" # UK, USA, Canada, Australia
    level: int = 0 # Neutral level 0-13 (0 = UK Reception / US Kindergarten)
    subject_ids: Optional[List[int]] = []
    avatar: str = "🦁"
    student_email: Optional[str] = None
    student_password: Optional[str] = None

class ChildUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[str] = None
    education_system: Optional[str] = None
    level: Optional[int] = None
    avatar: Optional[str] = None
    subject_ids: Optional[List[int]] = None

class StudentCredentialsUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class ChildSubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_id: int
    subject: SubjectOut

class ChildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parent_id: int
    name: str
    age: int
    date_of_birth: Optional[str] = None
    education_system: str
    level: int
    level_label: Optional[str] = None
    grade: Optional[str] = None
    avatar: str
    profile_image_url: Optional[str] = None
    student_email: Optional[str] = None
    xp: int
    streak_days: int
    enrolled_subjects: Optional[List[ChildSubjectOut]] = []
    completed_lessons_count: Optional[int] = 0
    progress_percentage: Optional[int] = 0

# Lesson & Curriculum schemas
class QuizQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question: str
    options: List[str]
    correct_answer: str
    explanation_correct: Optional[str] = None
    explanation_incorrect: Optional[str] = None

class LessonDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lesson_id: int
    day_number: int
    activity_type: str
    title: str
    learning_objectives: Optional[List[str]] = []
    key_concept: Optional[str] = None
    bible_reference: Optional[str] = None
    biblical_theme: Optional[str] = None
    biblical_application: Optional[str] = None
    character_reference: Optional[str] = None
    estimated_duration: Optional[str] = None
    ai_script: Optional[str] = None
    real_world_context: Optional[str] = None
    visual_support: Optional[str] = None
    origin_of_knowledge: Optional[str] = None
    video_url: Optional[str] = None
    practice_questions: Optional[List[Any]] = []
    vocabulary: Optional[List[Any]] = []
    reading_recommendations: Optional[List[str]] = []
    status: Optional[str] = "active"

class LessonSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    unit_id: int
    level: int
    title: str
    topic: Optional[str] = None
    order_num: int
    curriculum_country: Optional[str] = None
    default_evidence_task: Optional[str] = None

class LessonDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    unit_id: int
    level: int
    title: str
    topic: Optional[str] = None
    order_num: int
    curriculum_country: Optional[str] = None
    objectives: List[str]
    learn_content: str
    examples: List[Dict[str, Any]]
    vocabulary: List[Dict[str, Any]]
    key_points: List[str]
    bible_reflection: Optional[str] = None
    character_connection: Optional[str] = None
    default_evidence_task: Optional[str] = None
    days: Optional[List[LessonDayOut]] = []
    quiz_questions: List[QuizQuestionOut]

class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_id: int
    level: int
    title: str
    order_num: int
    lessons: List[LessonSummaryOut]

class SubjectWithUnitsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    icon: str
    color: str
    description: Optional[str] = None
    units: List[UnitOut]

# Evidence schemas
class EvidenceSubmit(BaseModel):
    child_id: int
    lesson_id: Optional[int] = None
    day_number: Optional[int] = 1
    subject: str
    lesson_title: str
    skill: str
    evidence_type: str = "lesson" # project, lesson, real-world
    submission_type: str = "text" # text, file, audio, video
    content: Optional[str] = None

class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    child_id: int
    lesson_id: Optional[int] = None
    day_number: Optional[int] = 1
    subject: str
    lesson_title: str
    skill: str
    evidence_type: str
    submission_type: str
    content: Optional[str] = None
    file_upload: Optional[str] = None
    score: Optional[int] = None
    ai_feedback: str
    verified: bool
    created_at: datetime.datetime

# Quiz Submit Schema
class QuizAnswer(BaseModel):
    question_id: int
    selected_answer: str

class QuizSubmission(BaseModel):
    child_id: int
    lesson_id: int
    day_number: int = 1
    answers: List[QuizAnswer]

class QuizResultOut(BaseModel):
    score: int
    total_questions: int
    percentage: int
    xp_earned: int
    passed: bool
    feedback: str

# AI Guidance Chat Schema
class AITutorChatRequest(BaseModel):
    child_id: int
    lesson_id: int
    day_number: int = 1
    current_tab: int # 0=Objectives, 1=Learn, 2=Examples, 3=Words, 4=Remember
    message_history: Optional[List[Dict[str, str]]] = []
    user_prompt: Optional[str] = None
    event_type: Optional[str] = None
    delivery_token: Optional[str] = None

class AITutorChatResponse(BaseModel):
    tutor_reply: str
    speech_text: str
    suggested_follow_up: Optional[str] = None
    pedagogical_state: Optional[Dict[str, Any]] = None
    practice_ready: Optional[bool] = False
    delivery_token: Optional[str] = None
    requires_delivery_confirmation: bool = False

# Parent Alerts & Recommendations
class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    severity: str
    title: str
    subtitle: str
    is_read: bool
    created_at: datetime.datetime

class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    child_id: int
    title: str
    description: str
    status: str
    created_at: datetime.datetime

class RecommendationAction(BaseModel):
    action: str # "approve" or "override"
