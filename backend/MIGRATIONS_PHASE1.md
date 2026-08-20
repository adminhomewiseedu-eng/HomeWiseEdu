# Phase 1 schema migration

Fresh databases receive these constraints through SQLAlchemy metadata. Existing
SQLite development databases are upgraded at startup: the XP flag is added and
unique indexes are created only when no conflicting rows already exist. Existing
duplicates are preserved for manual review.

Before applying the PostgreSQL migration, inspect duplicates:

```sql
SELECT child_id, lesson_id, day_number, COUNT(*)
FROM lesson_sessions
GROUP BY child_id, lesson_id, day_number
HAVING COUNT(*) > 1;

SELECT child_id, lesson_id, day_number, COUNT(*)
FROM student_progress
GROUP BY child_id, lesson_id, day_number
HAVING COUNT(*) > 1;
```

Resolve any returned rows according to their most recent authoritative state,
then apply:

```sql
ALTER TABLE student_progress
    ADD COLUMN IF NOT EXISTS quiz_xp_awarded BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_lesson_session_child_lesson_day
    ON lesson_sessions (child_id, lesson_id, day_number);

CREATE UNIQUE INDEX IF NOT EXISTS uq_student_progress_child_lesson_day
    ON student_progress (child_id, lesson_id, day_number);
```

Production startup also now requires `SECRET_KEY` to contain at least 32
characters. Set `ENVIRONMENT=production` (Railway also triggers production
validation through `RAILWAY_ENVIRONMENT`).
