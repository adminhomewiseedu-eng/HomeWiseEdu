import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)
engine_options = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update({"pool_recycle": 300, "pool_size": settings.DB_POOL_SIZE, "max_overflow": settings.DB_MAX_OVERFLOW})

engine = create_engine(settings.DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_db_schema():
    """Compatibility migration for existing local SQLite databases only."""
    if not settings.DATABASE_URL.startswith("sqlite") or settings.is_production:
        return
    with engine.begin() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(lesson_sessions)"))]
        if columns and "pedagogical_state" not in columns:
            conn.execute(text("ALTER TABLE lesson_sessions ADD COLUMN pedagogical_state JSON DEFAULT '{}'"))
        progress_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(student_progress)"))]
        if progress_columns and "quiz_xp_awarded" not in progress_columns:
            conn.execute(text("ALTER TABLE student_progress ADD COLUMN quiz_xp_awarded BOOLEAN NOT NULL DEFAULT 0"))
        evidence_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(learning_evidence)"))]
        if evidence_columns and "completion_xp_awarded" not in evidence_columns:
            conn.execute(text("ALTER TABLE learning_evidence ADD COLUMN completion_xp_awarded BOOLEAN NOT NULL DEFAULT 0"))
        if evidence_columns and "stored_file_name" not in evidence_columns:
            conn.execute(text("ALTER TABLE learning_evidence ADD COLUMN stored_file_name VARCHAR"))
        lesson_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(lessons)"))]
        if lesson_columns and "curriculum_country" not in lesson_columns:
            conn.execute(text("ALTER TABLE lessons ADD COLUMN curriculum_country VARCHAR"))
        day_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(lesson_days)"))]
        if day_columns and "origin_of_knowledge" not in day_columns:
            conn.execute(text("ALTER TABLE lesson_days ADD COLUMN origin_of_knowledge TEXT"))
        if day_columns and "video_url" not in day_columns:
            conn.execute(text("ALTER TABLE lesson_days ADD COLUMN video_url TEXT"))
        child_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(children)"))]
        if child_columns and "user_id" not in child_columns:
            conn.execute(text("ALTER TABLE children ADD COLUMN user_id INTEGER"))
        if child_columns and "profile_image_name" not in child_columns:
            conn.execute(text("ALTER TABLE children ADD COLUMN profile_image_name VARCHAR"))
        if child_columns:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_children_user_id ON children(user_id)"))
        for table, index_name in (("lesson_sessions", "uq_lesson_session_child_lesson_day"), ("student_progress", "uq_student_progress_child_lesson_day")):
            duplicates = conn.execute(text(
                f"SELECT COUNT(*) FROM (SELECT child_id, lesson_id, day_number FROM {table} "
                "GROUP BY child_id, lesson_id, day_number HAVING COUNT(*) > 1)"
            )).scalar() or 0
            if duplicates == 0:
                conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table}(child_id, lesson_id, day_number)"))
            else:
                logger.warning("Local duplicates prevent unique index %s", index_name)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
