# HomeWiseEdu

HomeWiseEdu is an AI-supported homeschooling platform built around a structured curriculum. The backend—not the language model—owns lesson progression, mastery decisions, quiz readiness, enrolment, and persisted learning state.

## Product architecture

- **Frontend:** React 18, Vite, React Router and Axios
- **Backend:** FastAPI, SQLAlchemy and Alembic
- **Production database:** PostgreSQL
- **AI tutoring and evaluation:** OpenAI, called only from the backend
- **Primary teacher voice:** ElevenLabs
- **Voice fallbacks:** backend OpenAI TTS, then browser speech synthesis
- **Production target:** Railway with separate frontend, backend and PostgreSQL services

The pedagogical sequence is backend-governed:

`GREETING → TEACHING → WORKED_EXAMPLE_1 → WORKED_EXAMPLE_2 → WORKED_EXAMPLE_3 → UNDERSTANDING_CHECK → GUIDED_PRACTICE → APPLICATION → MASTERY_CHECK → LESSON_SUMMARY → PRACTICE_READY`

The AI may explain, tutor and evaluate a response, but it cannot independently unlock practice or decide curriculum progression.

## Repository structure

```text
backend/                 FastAPI application, migrations, models and tests
backend/prompts/         Tutor and evaluation prompt templates
backend/routers/         Auth, curriculum, lesson, voice and dashboard APIs
backend/services/        AI, voice, curriculum import and storage services
frontend/                React/Vite application
frontend/src/components/ Application screens and UI components
frontend/src/services/   API and coordinated speech/audio clients
DEPLOYMENT_RAILWAY.md     Detailed Railway production runbook
railway.json             Backend Railway configuration
```

## Local requirements

- Python 3.11 or newer
- Node.js 20 or newer
- PostgreSQL for production; SQLite is supported for local development
- OpenAI API key
- ElevenLabs API key and voice ID

## Environment configuration

Create `.env` in the repository root for local backend development:

```dotenv
ENVIRONMENT=development
DATABASE_URL=sqlite:///./homewiseedu.db
SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=your-ms-ade-voice-id
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
FRONTEND_URL=http://localhost:3000
PASSWORD_RESET_EXPIRE_MINUTES=45
# Development-only reset-link capture; never enable in production.
PASSWORD_RESET_DEV_MODE=true
AUTO_INIT_DB=true
SEED_MODE=demo
```

Create `frontend/.env.local`:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
```

Never place `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `SECRET_KEY` or `DATABASE_URL` in frontend variables. Environment files are excluded by `.gitignore` and must not be committed.

Password-reset email delivery uses backend-only SMTP configuration: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, and `SMTP_USE_TLS`. Production startup fails if SMTP delivery is absent, preventing a deployment from silently exposing a broken recovery flow. Local developers may temporarily enable `PASSWORD_RESET_DEV_MODE`; captured links remain in the backend process only and are never returned by the API or logged. Production rejects this setting.

## Run locally

### Backend

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Verify:

- API health: `http://127.0.0.1:8000/health`
- Database readiness: `http://127.0.0.1:8000/ready`
- API documentation: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

Chrome requires microphone permission for voice interaction. Headphones improve interruption detection by reducing teacher-audio feedback into the microphone.

## Tests

Backend:

```powershell
pytest backend
```

Frontend voice and resume tests:

```powershell
cd frontend
npm test
```

Production frontend build:

```powershell
cd frontend
$env:VITE_API_URL="https://your-backend.example.com"
npm run build
```

## Curriculum administration

Public signup creates parent accounts only; it cannot create administrators. Admin access must be provisioned deliberately by an authorised operator.

Parents can optionally enable a separate student login while creating or editing a child. Student accounts open only their linked student dashboard, while the owning parent retains access and can reset the student's credentials. Passwords are stored only as hashes and are never returned by the API.

The admin curriculum workflow is:

1. Sign in with an authorised admin account.
2. Open **Admin → Curriculum**.
3. Validate the curriculum CSV.
4. Import it as pending.
5. Review the generated hierarchy and lesson-day content.
6. Publish only approved lessons and lesson days.

Curriculum structure is `Level → Subject → Unit → Lesson → Lesson Day`. Lesson days are normally Day 1 Explore, Day 2 Practice and Day 3 Apply. A child only sees published curriculum matching their level and enrolled subjects.

Do not commit curriculum files containing private student or client data.

## Voice behavior

Ms. Ade uses the backend voice endpoint. ElevenLabs is authoritative, OpenAI TTS is the server fallback, and browser speech synthesis is the final fallback. A single audio coordinator cancels stale playback.

During lessons the microphone supports hands-free interruption. A detected interruption stops teacher playback without confirming that interrupted phase as delivered. The application then waits for the student's complete statement before requesting the next tutor response. Unclear or repeat requests must not count as failed academic attempts.

## Production deployment

See [DEPLOYMENT_RAILWAY.md](DEPLOYMENT_RAILWAY.md) for the complete service layout, required variables, migrations, storage volume, deployment order and smoke-test checklist.

Production requires:

- PostgreSQL `DATABASE_URL`
- a random `SECRET_KEY` of at least 32 characters
- OpenAI and ElevenLabs credentials
- an HTTPS-only `ALLOWED_ORIGINS` value
- durable `STORAGE_ROOT` for evidence, reports and child profile pictures
- `VITE_API_URL` configured at frontend build time
- `ENVIRONMENT=production`, `AUTO_INIT_DB=false` and `SEED_MODE=none`

Do not deploy production with demo seed data or local SQLite.

## Current scope boundaries

- Structured curriculum import, review and publishing are implemented.
- Parent, child, student and admin role flows are implemented.
- Backend-owned lesson progression, quiz readiness and progress persistence are implemented.
- Reports currently return authenticated JSON; PDF generation is not implemented.
- Certificates are not implemented.
- Subscription checkout and Stripe integration are not implemented.

## Security notes

- Provider keys remain server-side.
- Role and parent/child ownership checks are enforced by backend routes.
- Production configuration fails closed when required variables are unsafe or missing.
- Use separate credentials for development and production.
- Rotate any credential that has been exposed in chat, logs, screenshots or source control.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
