# HomeWiseEdu

HomeWiseEdu is a role-based homeschooling platform combining administrator-managed curriculum, parent oversight, student dashboards, quizzes, learning evidence, and a live AI classroom led by “Ms Ade.” The backend remains authoritative for authentication, ownership, curriculum publication, lesson progression, mastery, quiz readiness, and persisted learning records.

Production: [https://homewiseedu.com](https://homewiseedu.com)

## Handover status

- The application is deployed at `homewiseedu.com`.
- Curriculum validation, import, review, publication, archive/restore, dependency checks, and protected deletion are implemented.
- The client’s complete final production curriculum has **not** yet been supplied. Final curriculum population is therefore a client-supplied content task.
- New or materially changed curriculum may require reviewed quiz content before student use.
- Current/test curriculum must not be presented as the client’s complete final curriculum.
- Stripe checkout, billing, and subscriptions are **not implemented or production-ready**. Pricing/trial labels are presentation only; the API reports billing as not configured.

Before operational handover, use [docs/HANDOVER_CHECKLIST.md](docs/HANDOVER_CHECKLIST.md) and [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Stack and architecture

- **Frontend:** React 18, Vite 6, React Router, Axios, Lucide
- **Backend:** FastAPI, SQLAlchemy 2, Pydantic, Uvicorn
- **Database/migrations:** PostgreSQL and Alembic (SQLite is available locally)
- **Authentication:** JWT, password hashing, role and ownership checks
- **AI/classroom:** OpenAI tutoring/evaluation and OpenAI Realtime over WebRTC
- **Email:** Resend transactional email with SMTP fallback support
- **Hosting/storage:** Railway frontend, backend, PostgreSQL, and backend persistent volume

```text
React browser ──HTTPS API──► FastAPI ──SQLAlchemy──► PostgreSQL
      └────────WebRTC──────► OpenAI Realtime
                              ├─ Resend/SMTP
                              └─ persistent uploads volume
```

OpenAI does not independently grant mastery or unlock quizzes. The backend owns pedagogical state, active questions/tasks, delivery acknowledgement, evaluation, practice readiness, and progress. The classroom sequence is:

`GREETING → TEACHING → WORKED_EXAMPLE_1 → WORKED_EXAMPLE_2 → WORKED_EXAMPLE_3 → UNDERSTANDING_CHECK → GUIDED_PRACTICE → APPLICATION → MASTERY_CHECK → LESSON_SUMMARY → PRACTICE_READY`

## Repository structure

```text
backend/                      FastAPI application, models, routers and tests
backend/services/             Curriculum, AI, email, voice and storage services
backend/prompts/              Server-side AI prompt templates
backend/migrations/versions/  Alembic revisions
frontend/                     React/Vite app and frontend Railway service
frontend/src/components/      Screens and UI components
frontend/src/services/        API, speech and Realtime clients
frontend/src/utils/           Classroom/UI helpers and tests
docs/                         Handover and user documentation
alembic.ini                   Migration configuration
railway.json                  Backend Railway configuration
DEPLOYMENT_RAILWAY.md         Detailed deployment runbook
```

## Local setup

Requirements: Python 3.11+, Node.js 20+, npm, and PostgreSQL for production-like development (or SQLite locally).

### Backend

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload --port 8000
```

- Health: `http://127.0.0.1:8000/health`
- Readiness: `http://127.0.0.1:8000/ready`
- Development API docs: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` in `frontend/.env.local` to the backend origin. Never place secrets in `VITE_*` variables; they are embedded in the browser bundle.

### Tests and build

```powershell
pytest backend
cd frontend
npm test
npm run build
```

Migration inspection:

```powershell
alembic current
alembic heads
alembic history
```

`python -m backend.seed_data` seeds reference subjects. `python -m backend.seed_data --demo` creates demo data and must never run in production.

## Environment variables

Only names and purposes are documented. Values belong in ignored local files or Railway.

### Backend

| Name | Purpose |
|---|---|
| `ENVIRONMENT` | Production/development behavior |
| `DATABASE_URL` | Database connection; PostgreSQL required in production |
| `SECRET_KEY` | Token signing |
| `ALLOWED_ORIGINS` | Permitted frontend origins |
| `FRONTEND_URL` | Public frontend origin for reset links |
| `PORT`, `RAILWAY_ENVIRONMENT` | Railway runtime metadata |
| `OPENAI_API_KEY` | Server-side OpenAI access |
| `OPENAI_MODEL` | Text/evaluation model |
| `OPENAI_REALTIME_MODEL`, `OPENAI_REALTIME_VOICE` | Realtime classroom configuration |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID` | Supported voice-path configuration |
| `ELEVENLABS_STABILITY`, `ELEVENLABS_SIMILARITY_BOOST`, `ELEVENLABS_STYLE`, `ELEVENLABS_USE_SPEAKER_BOOST`, `ELEVENLABS_SPEED` | Voice tuning |
| `RESEND_API_KEY` | Resend credential |
| `TRANSACTIONAL_FROM_EMAIL`, `TRANSACTIONAL_REPLY_TO_EMAIL` | Central sender/reply-to identities |
| `PASSWORD_RESET_FROM_EMAIL` | Compatibility sender fallback |
| `PASSWORD_RESET_EXPIRE_MINUTES`, `PASSWORD_RESET_RATE_LIMIT`, `PASSWORD_RESET_RATE_WINDOW_SECONDS` | Reset expiry/throttling |
| `PASSWORD_RESET_DEV_MODE` | Development-only capture; forbidden in production |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | SMTP fallback |
| `AUTO_INIT_DB`, `SEED_MODE` | Local schema/seed behavior; disable demo behavior in production |
| `STORAGE_ROOT`, `TTS_CACHE_DIR` | Persistent uploads and disposable TTS cache |
| `MAX_UPLOAD_BYTES`, `MAX_PROFILE_IMAGE_BYTES` | Upload limits |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | PostgreSQL pool limits |

### Frontend

| Name | Purpose |
|---|---|
| `VITE_API_URL` | Public backend origin embedded at build time |
| `PORT` | Railway frontend port |

## Roles

- **Admin:** manages parents/students, curriculum, publication, archive/restore, deletion safeguards, quiz review flags, monitoring, and settings. Public signup cannot create admins.
- **Parent:** manages profile, children, subjects, optional student login, progress, and evidence.
- **Student:** accesses the linked dashboard, published lessons, classroom, ready quizzes, and evidence/portfolio.

## Curriculum

The hierarchy is `Subject → Unit → Lesson → LessonDay`. Imports match by stable curriculum identity (subject, level, unit, lesson number) to preserve lesson IDs and history.

- **Multi-day:** exactly `Day 1 Explore`, `Day 2 Practice`, and `Day 3 Apply`.
- **Weekly:** exactly one `Weekly Lesson` session.

Cadences cannot be mixed within a lesson or changed on an existing lesson. The Admin workflow is: validate/preview CSV, inspect errors and hierarchy/cadence warnings, import approved content as pending, review/edit, review quiz readiness, then publish. Updates do not rewrite immutable quiz attempts. Material changes may flag quiz review.

## Quiz, progress, and evidence

- Quiz access requires backend practice readiness and reviewed questions.
- Curriculum practice prompts do not automatically become reviewed quiz questions.
- `quiz_attempts` contains immutable, idempotent submission snapshots.
- `student_progress` holds the current progress summary/unlock state.
- Evidence text/files are ownership-protected and available to authorised student, parent, and admin views.

## Email and AI configuration

Production transactional mail uses Resend with the verified HomeWiseEdu domain and centralized sender settings. SMTP is a fallback. Production fails closed without a valid reset-email path; development reset-link capture must remain disabled in production.

OpenAI keys remain backend-only. The authenticated backend issues short-lived Realtime session configuration; the browser connects via WebRTC while backend authority remains intact. Microphone permission is required. Headphones can reduce echo during barge-in testing.

## Railway deployment

Root `railway.json` installs backend requirements, starts Uvicorn, and checks `/ready`. It does **not** run migrations. Database migrations require a separately approved, explicit operator action after backup verification and before application deployment. `frontend/railway.json` installs/builds the frontend, starts `server.mjs`, and checks `/`. Attach persistent storage only to the backend. See [DEPLOYMENT_RAILWAY.md](DEPLOYMENT_RAILWAY.md).

Post-deploy: verify `/health`, `/ready`, `homewiseedu.com`, nested-route refresh, all three roles, a published lesson, and password-reset provider acceptance.

## Maintenance and troubleshooting

- **API/CORS failure:** verify backend health, `VITE_API_URL`, HTTPS, and `ALLOWED_ORIGINS`.
- **Backend not ready:** inspect migration and PostgreSQL logs; do not bypass readiness.
- **Missing reset email:** check Resend domain/sender, delivery logs, spam, and rate limits without logging tokens.
- **Import failure:** validate first; correct headers, hierarchy, cadence, or duplicate days.
- **Quiz conflict:** check practice readiness, reviewed questions, and quiz-review status; never expose unreviewed questions.
- **Missing upload after restart:** verify the persistent volume and `STORAGE_ROOT`.
- **Realtime issue:** capture safe event metadata only; never log keys, tokens, or unnecessary private content.

## Backup and restore

Back up PostgreSQL and the uploads volume separately. A database backup does not contain evidence/profile files.

```powershell
pg_dump --schema-only --no-owner --no-privileges --file schema-backup.sql <database>
pg_dump --format=custom --no-owner --file homewiseedu.backup <database>
pg_restore --clean --if-exists --no-owner --dbname <target-database> homewiseedu.backup
```

Restore into an approved isolated environment first. Verify Alembic state, foreign keys, record counts, authentication, curriculum, quiz attempts, and protected files before cutover. Encrypt backups and restrict access.

## Known boundaries

- Stripe/payments/subscriptions are not implemented.
- Reports are authenticated JSON; PDF generation is not implemented.
- Certificates are not implemented.
- Final client curriculum and reviewed quiz bank remain client content dependencies.

## License

See [LICENSE](LICENSE).
