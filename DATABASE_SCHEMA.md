# HomeWiseEdu database schema

This document accompanies [`schema.sql`](schema.sql). It provides a technical reviewer with the current PostgreSQL structure without exposing credentials, environment variables, application data, test accounts or provider secrets.

## Schema authority

- ORM: SQLAlchemy 2.x declarative models in `backend/models.py`
- Migrations: Alembic revisions in `backend/migrations/versions`
- Current migration head: `0003_curriculum_blueprint`
- Production database: PostgreSQL through `psycopg2-binary`
- Local default: SQLite when `DATABASE_URL` is absent

At the source commit recorded at the top of `schema.sql`, a clean database can be reconstructed by setting a PostgreSQL `DATABASE_URL` in the process environment and running:

```powershell
alembic upgrade head
```

Migration `0001_current_schema` creates the baseline from current SQLAlchemy metadata. Revisions `0002_phase_hardening` and `0003_curriculum_blueprint` add legacy integrity and curriculum fields where required.

Because the initial migration imports live model metadata, `schema.sql` is also retained as a fixed review snapshot. Future model changes should produce a new Alembic revision and a regenerated schema snapshot.

## Included structures

The snapshot contains 14 application tables and the Alembic version table:

- Identity and enrolment: `users`, `children`, `subjects`, `child_subjects`
- Curriculum: `units`, `lessons`, `lesson_days`, `quiz_questions`
- Learning state: `lesson_sessions`, `student_progress`, `learning_evidence`
- AI and parent support: `ai_interactions`, `parent_alerts`, `ai_recommendations`
- Migration tracking: `alembic_version`

Foreign keys in `schema.sql` show the persisted relationships. SQLAlchemy also defines ORM relationships and application-side cascades. The current foreign keys do not use PostgreSQL `ON DELETE CASCADE`, so ORM cascades must not be mistaken for database cascades.

### Foreign-key relationships

- `children.parent_id → users.id`
- `child_subjects.child_id → children.id`
- `child_subjects.subject_id → subjects.id`
- `units.subject_id → subjects.id`
- `lessons.unit_id → units.id`
- `lesson_days.lesson_id → lessons.id`
- `lesson_sessions.child_id → children.id`
- `lesson_sessions.lesson_id → lessons.id`
- `quiz_questions.lesson_id → lessons.id`
- `student_progress.child_id → children.id`
- `student_progress.lesson_id → lessons.id`
- `learning_evidence.child_id → children.id`
- `learning_evidence.lesson_id → lessons.id`
- `ai_interactions.child_id → children.id`
- `ai_interactions.lesson_id → lessons.id`
- `parent_alerts.parent_id → users.id`
- `parent_alerts.child_id → children.id`
- `ai_recommendations.parent_id → users.id`
- `ai_recommendations.child_id → children.id`

### Uniqueness and indexes

- Primary keys exist on every table.
- User email, subject title and subject slug are unique.
- Child/subject enrolment is unique by `(child_id, subject_id)`.
- Lesson days are unique by `(lesson_id, day_number)`.
- Lesson sessions and progress records are each unique by `(child_id, lesson_id, day_number)`.
- SQLAlchemy `index=True` indexes are included with their generated `ix_*` names.

## Enums and constrained values

There are no native PostgreSQL enum types in the current schema. Fields such as user role, activity type, progress status, mastery status and recommendation status are `VARCHAR` values governed by application logic. No enum definitions were invented for this export.

## Defaults

Most defaults in the models are SQLAlchemy/Python defaults, not PostgreSQL server defaults. They are therefore intentionally absent from the DDL. This reflects the current database contract: normal application inserts receive defaults through the ORM, while direct SQL inserts must supply required behavior explicitly.

## Safe schema-only dump from PostgreSQL

If a PostgreSQL development environment is later provisioned, install PostgreSQL client tools and keep its connection string only in the process environment. Generate a structure-only dump with:

```powershell
pg_dump `
  --dbname="$env:DATABASE_URL" `
  --schema-only `
  --schema=public `
  --no-owner `
  --no-privileges `
  --format=plain `
  --file=schema-only.sql
```

This command excludes table rows and removes ownership and privilege statements. It does not require placing a connection string in a tracked script or documentation file.

Validate the result before sharing:

```powershell
Select-String -Path schema-only.sql -Pattern "INSERT INTO|COPY .* FROM stdin|DATABASE_URL|postgresql://|password|api[_-]?key|token" -CaseSensitive:$false
```

No `INSERT INTO` or `COPY ... FROM stdin` application-data statements should be present. Review any other match manually before distribution.

## Restore validation

Validate a schema dump only against an empty disposable PostgreSQL database:

```powershell
psql --dbname="$env:EMPTY_REVIEW_DATABASE_URL" --set ON_ERROR_STOP=1 --file=schema-only.sql
```

Never restore a review export over an existing development or production database.

## Security boundaries

Do not commit or distribute:

- `.env` files or their values
- PostgreSQL connection strings
- passwords or password hashes
- OpenAI or ElevenLabs credentials
- JWT secrets or tokens
- parent, child, curriculum-progress or evidence records
- dumps created without `--schema-only`

The committed schema files contain structure only.
