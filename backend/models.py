import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="parent") # parent, student, admin
    account_status = Column(String, default="active", nullable=False) # active, suspended
    avatar = Column(String, default="S")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    auth_version = Column(Integer, default=0, nullable=False)

    children = relationship("Child", back_populates="parent", cascade="all, delete-orphan", foreign_keys="Child.parent_id")
    student_child = relationship("Child", back_populates="login_user", uselist=False, foreign_keys="Child.user_id")
    alerts = relationship("ParentAlert", back_populates="parent", cascade="all, delete-orphan")
    recommendations = relationship("AIRecommendation", back_populates="parent", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    parent_profile = relationship("ParentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin_profile = relationship("AdminProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class ParentProfile(Base):
    __tablename__ = "parent_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address_line_1 = Column(String, nullable=True)
    address_line_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state_region = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    profile_image_name = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="parent_profile")


class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address_line_1 = Column(String, nullable=True)
    address_line_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state_region = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    profile_image_name = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="admin_profile")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, default=9)
    date_of_birth = Column(String, nullable=True) # e.g. "2015-04-12"
    education_system = Column(String, default="UK", nullable=False) # UK, USA, Canada, Australia
    level = Column(Integer, default=4, nullable=False) # Canonical Level 0 -> 13
    grade = Column(String, default="Year 4") # legacy/display cached grade
    avatar = Column(String, default="🦁")
    profile_image_name = Column(String, nullable=True)
    xp = Column(Integer, default=0)
    streak_days = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    last_active_date = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    parent = relationship("User", back_populates="children", foreign_keys=[parent_id])
    login_user = relationship("User", back_populates="student_child", foreign_keys=[user_id])
    enrolled_subjects = relationship("ChildSubject", back_populates="child", cascade="all, delete-orphan")
    progress_records = relationship("StudentProgress", back_populates="child", cascade="all, delete-orphan")
    evidence_records = relationship("LearningEvidence", back_populates="child", cascade="all, delete-orphan")
    sessions = relationship("LessonSession", back_populates="child", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="child", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, nullable=False) # e.g. Mathematics, English Language, Science, Understanding The Word
    slug = Column(String, unique=True, index=True, nullable=False)
    icon = Column(String, default="📚")
    color = Column(String, default="#7C3AED")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    enrollments = relationship("ChildSubject", back_populates="subject", cascade="all, delete-orphan")
    units = relationship("Unit", back_populates="subject", cascade="all, delete-orphan")


class ChildSubject(Base):
    """Relational enrollment mapping between a Child and the Academic Pathway Subjects they study."""
    __tablename__ = "child_subjects"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("child_id", "subject_id", name="uq_child_subject"),
    )

    child = relationship("Child", back_populates="enrolled_subjects")
    subject = relationship("Subject", back_populates="enrollments")


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    level = Column(Integer, default=4, nullable=False) # Canonical Level 0 -> 13
    title = Column(String, nullable=False)
    order_num = Column(Integer, default=1)

    subject = relationship("Subject", back_populates="units")
    lessons = relationship("Lesson", back_populates="unit", cascade="all, delete-orphan")


class Lesson(Base):
    """Lesson Topic (e.g. Counting to 5, Fractions Practice, Magnetic Forces). Contains 3 Days."""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    level = Column(Integer, default=4, nullable=False) # Canonical Level 0 -> 13
    title = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    order_num = Column(Integer, default=1)
    curriculum_country = Column(String, nullable=True)
    
    # Structured Lesson Summary Fields
    objectives = Column(JSON, default=list)
    learn_content = Column(Text, nullable=False)
    examples = Column(JSON, default=list)
    vocabulary = Column(JSON, default=list)
    key_points = Column(JSON, default=list)
    bible_reflection = Column(Text, nullable=True)
    character_connection = Column(Text, nullable=True)
    default_evidence_task = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    unit = relationship("Unit", back_populates="lessons")
    days = relationship("LessonDay", back_populates="lesson", cascade="all, delete-orphan", order_by="LessonDay.day_number")
    quiz_questions = relationship("QuizQuestion", back_populates="lesson", cascade="all, delete-orphan")
    progress_records = relationship("StudentProgress", back_populates="lesson")
    quiz_attempts = relationship("QuizAttempt", back_populates="lesson", cascade="all, delete-orphan")
    sessions = relationship("LessonSession", back_populates="lesson", cascade="all, delete-orphan")


class LessonDay(Base):
    """Specific daily lesson activity (Day 1 - Explore, Day 2 - Practice, Day 3 - Apply)."""
    __tablename__ = "lesson_days"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    day_number = Column(Integer, default=1, nullable=False) # 1, 2, 3
    activity_type = Column(String, default="Explore", nullable=False) # Explore, Practice, Apply
    title = Column(String, nullable=False)
    
    # Client Blueprint Structured Fields
    learning_objectives = Column(JSON, default=list)
    key_concept = Column(Text, nullable=True)
    bible_reference = Column(String, nullable=True)
    biblical_theme = Column(String, nullable=True)
    biblical_application = Column(Text, nullable=True)
    character_reference = Column(String, nullable=True)
    estimated_duration = Column(String, default="20 mins")
    ai_script = Column(Text, nullable=True) # AI Teaching Script / guidance
    real_world_context = Column(Text, nullable=True)
    visual_support = Column(Text, nullable=True)
    origin_of_knowledge = Column(Text, nullable=True)
    video_url = Column(Text, nullable=True)
    practice_questions = Column(JSON, default=list)
    vocabulary = Column(JSON, default=list)
    reading_recommendations = Column(JSON, default=list)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("lesson_id", "day_number", name="uq_lesson_day"),
    )

    lesson = relationship("Lesson", back_populates="days")

    @property
    def worked_examples(self):
        from .utils.lesson_content import authored_worked_examples
        return authored_worked_examples(self.lesson, self)


class LessonSession(Base):
    """Lightweight resumable lesson session tracking student's active position and chat history."""
    __tablename__ = "lesson_sessions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    day_number = Column(Integer, default=1, nullable=False)
    current_tab = Column(Integer, default=0) # 0=Objectives, 1=Learn, 2=Examples, 3=Words, 4=Remember
    pedagogical_state = Column(JSON, default=dict) # Backend-owned state: current_phase, worked_examples_completed, etc.
    messages = Column(JSON, default=list) # [{sender: "tutor", text: "..."}]
    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("child_id", "lesson_id", "day_number", name="uq_lesson_session_child_lesson_day"),
    )

    child = relationship("Child", back_populates="sessions")
    lesson = relationship("Lesson", back_populates="sessions")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    question = Column(String, nullable=False)
    options = Column(JSON, nullable=False) # ["2/4", "1/3", "3/5", "2/3"]
    correct_answer = Column(String, nullable=False)
    explanation_correct = Column(String, nullable=True)
    explanation_incorrect = Column(String, nullable=True)

    lesson = relationship("Lesson", back_populates="quiz_questions")


class StudentProgress(Base):
    __tablename__ = "student_progress"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    day_number = Column(Integer, default=1, nullable=False) # Day 1, 2, 3
    activity_type = Column(String, default="Explore") # Explore, Practice, Apply
    status = Column(String, default="completed") # not_started, in_progress, completed
    quiz_score = Column(Integer, default=100) # percentage
    mastery_status = Column(String, default="competent") # developing, competent, mastered
    remediation_needed = Column(Boolean, default=False)
    quiz_xp_awarded = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("child_id", "lesson_id", "day_number", name="uq_student_progress_child_lesson_day"),
    )

    child = relationship("Child", back_populates="progress_records")
    lesson = relationship("Lesson", back_populates="progress_records")


class QuizAttempt(Base):
    """Immutable grading snapshot for one completed quiz submission."""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    submission_id = Column(String(64), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    day_number = Column(Integer, nullable=False, default=1)
    score_percentage = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    passed = Column(Boolean, nullable=False)
    xp_earned = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    __table_args__ = (
        CheckConstraint("score_percentage >= 0 AND score_percentage <= 100", name="ck_quiz_attempt_score_percentage"),
        CheckConstraint("correct_count >= 0", name="ck_quiz_attempt_correct_count"),
        CheckConstraint("total_questions >= 0", name="ck_quiz_attempt_total_questions"),
        CheckConstraint("correct_count <= total_questions", name="ck_quiz_attempt_counts"),
        Index("ix_quiz_attempts_submission_id", "submission_id", unique=True),
        Index("ix_quiz_attempts_child_lesson_day_completed", "child_id", "lesson_id", "day_number", "completed_at"),
    )

    child = relationship("Child", back_populates="quiz_attempts")
    lesson = relationship("Lesson", back_populates="quiz_attempts")


class LearningEvidence(Base):
    __tablename__ = "learning_evidence"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    day_number = Column(Integer, default=1)
    subject = Column(String, nullable=False) # e.g. "Mathematics", "English", "Science"
    lesson_title = Column(String, nullable=False)
    skill = Column(String, nullable=False) # e.g. "Equivalent fractions", "Counting to 5"
    evidence_type = Column(String, default="lesson") # project, lesson, real-world
    submission_type = Column(String, default="text") # text, image, video, audio, file
    content = Column(Text, nullable=True)
    file_upload = Column(String, nullable=True) # relative URL path
    stored_file_name = Column(String, nullable=True) # generated server-side name; never client input
    score = Column(Integer, nullable=True)
    ai_feedback = Column(Text, nullable=False)
    verified = Column(Boolean, default=True)
    completion_xp_awarded = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    child = relationship("Child", back_populates="evidence_records")


class AIInteraction(Base):
    """Audit and session log for AI tutor and evaluation interactions."""
    __tablename__ = "ai_interactions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    day_number = Column(Integer, default=1)
    session_id = Column(String, nullable=True)
    role = Column(String, default="assistant") # user, assistant, system
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ParentAlert(Base):
    __tablename__ = "parent_alerts"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True)
    severity = Column(String, default="normal") # high (red), medium (amber), info (green)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    parent = relationship("User", back_populates="alerts")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending") # pending, approved, overridden
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    parent = relationship("User", back_populates="recommendations")
