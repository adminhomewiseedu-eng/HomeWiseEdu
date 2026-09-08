# HomeWiseEdu Railway deployment plan

This is a deployment runbook, not an authorization to deploy. The immediate MVP storage choice is a Railway Volume because the application already serves files through FastAPI and changing to object storage would be a larger functional rewrite.

## Services

1. **PostgreSQL** — Railway managed PostgreSQL. Private networking only. Backups and retention must be enabled in Railway.
2. **Backend** — repository root `.`; Nixpacks build command `pip install -r backend/requirements.txt`; pre-deploy command `alembic upgrade head`; start command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`; health check `/ready`. Public HTTPS is required for the frontend API and protected file URLs; use the PostgreSQL private URL.
3. **Frontend** — root `frontend`; Nixpacks build (`npm ci && npm run build`); start `node server.mjs`; health check `/`. The built-in server provides SPA fallback for `/parent`, `/student`, `/lesson/*`, and `/quiz/*`.
4. **Volume** — attach to the backend at `/data/homewiseedu`; set `STORAGE_ROOT=/data/homewiseedu`. Do not attach it to the frontend.

## Variable matrix

| Scope | Variable | Required purpose |
|---|---|---|
| Backend private | `DATABASE_URL` | Railway PostgreSQL private connection URL |
| Backend private | `SECRET_KEY` | Random value of at least 32 characters |
| Backend private | `OPENAI_API_KEY` | Tutor/evaluation and fallback TTS |
| Backend private | `ELEVENLABS_API_KEY` | Primary teacher voice |
| Backend config | `ENVIRONMENT=production` | Enables fail-closed production behavior |
| Backend config | `OPENAI_MODEL` | Approved OpenAI chat/evaluation model |
| Backend config | `ELEVENLABS_VOICE_ID` | Authoritative Ms. Ade voice ID |
| Backend config | `ALLOWED_ORIGINS` | Comma-separated public HTTPS frontend origins |
| Backend config | `FRONTEND_URL` | Public HTTPS frontend origin used to construct password-reset links |
| Backend private | `SMTP_HOST`, `SMTP_PORT` | Transactional SMTP provider connection |
| Backend private | `SMTP_USERNAME`, `SMTP_PASSWORD` | Transactional SMTP credentials when required |
| Backend config | `SMTP_FROM_EMAIL` | Verified sender; normally `support@homewiseedu.com` |
| Backend config | `SMTP_USE_TLS=true` | Enables STARTTLS for SMTP delivery |
| Backend config | `PASSWORD_RESET_EXPIRE_MINUTES=45` | Single-use reset-token lifetime |
| Backend config | `PASSWORD_RESET_RATE_LIMIT=5` | Per-process request cap within the configured window |
| Backend config | `PASSWORD_RESET_RATE_WINDOW_SECONDS=900` | Password-reset throttling window |
| Backend config | `STORAGE_ROOT=/data/homewiseedu` | Durable evidence, report and student-profile-image root on the volume |
| Backend config | `TTS_CACHE_DIR=/tmp/homewiseedu/tts` | Disposable, regenerable TTS cache |
| Backend config | `MAX_UPLOAD_BYTES` | Optional override; default 26214400 |
| Backend config | `MAX_PROFILE_IMAGE_BYTES` | Optional student profile image limit; default 5242880 |
| Backend config | `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Optional conservative pool overrides (5/10 defaults) |
| Backend config | `AUTO_INIT_DB=false` | Explicit defense in depth; production already disables it |
| Backend config | `SEED_MODE=none` | Production must not create demo users |
| Frontend public | `VITE_API_URL` | Public HTTPS backend origin; it is embedded at build time |
| Railway-provided | `PORT` | Injected independently into backend/frontend services |
| Railway-provided | `RAILWAY_ENVIRONMENT` | Production environment marker |

Never place provider keys, `SECRET_KEY`, or `DATABASE_URL` in a `VITE_*` variable.
Never enable `PASSWORD_RESET_DEV_MODE` in production; startup rejects it. Production also requires `SMTP_HOST` and `SMTP_FROM_EMAIL` and fails startup if delivery is not configured. Configure `SMTP_USERNAME` and `SMTP_PASSWORD` together when the provider requires authentication.

## Migration and data preparation

For a clean database, `alembic upgrade head` creates the current schema. The Railway backend pre-deploy command executes it once before replicas start. Application startup only verifies readiness; it never mutates production schema.

For a legacy pre-Alembic database:

1. Back up the database.
2. Audit duplicates in `lesson_sessions` and `student_progress` by `(child_id, lesson_id, day_number)` and resolve them deliberately.
3. Verify the legacy tables correspond to the initial baseline, then run `alembic stamp 0001_current_schema`.
4. Run `alembic upgrade head`. The upgrade adds missing pedagogical state, quiz/evidence XP idempotency fields, nullable evidence scores, and uniqueness constraints. It refuses to invent a duplicate-row resolution policy.

No downgrade is automated because these integrity migrations can destroy data.

## Seeding and curriculum

`python -m backend.seed_data` seeds only the 12 system reference subjects. `python -m backend.seed_data --demo` additionally creates known demo accounts, sample curriculum, fake progress, and test credentials; never run `--demo` in production.

Real curriculum is uploaded by an authenticated admin to `POST /api/curriculum/import-csv`. The importer validates UTF-8 CSV size, required hierarchy fields, Level 0–13, Day 1–3, and activity type. It is idempotent by natural hierarchy keys and commits the entire file once. Invalid rows roll the whole import back and return a safe result; retry the corrected file. Import a small staging file first and retain the source CSV as the rollback/audit artifact.

## Storage and retention

- `STORAGE_ROOT/evidence`: durable student uploads; included in volume backups and the product retention/deletion policy.
- `STORAGE_ROOT/reports`: reserved durable path for report/certificate files if that feature is later implemented.
- `STORAGE_ROOT/profiles`: durable child profile pictures; include it in volume backups and the same deletion/retention policy as child records.
- `TTS_CACHE_DIR`: disposable audio cache; safe to clear because speech can be regenerated.
- atomic temporary cache/upload files: disposable and removed after replacement/failure.

Uploads are capped, extension/MIME/content-signature checked, assigned generated names, and never use the client path. Advanced malware scanning is future defense-in-depth, not part of this MVP.

## Deployment order

1. Provision PostgreSQL and take note of its private `DATABASE_URL`.
2. Create the backend service, attach `/data/homewiseedu`, and configure all backend variables.
3. Run/observe the pre-deploy migration; stop if duplicate or schema checks fail.
4. Deploy backend and verify `/health` then `/ready` over HTTPS.
5. Create frontend service, set `VITE_API_URL` to the backend HTTPS origin, and deploy.
6. Obtain the frontend HTTPS domain; update backend `ALLOWED_ORIGINS` and redeploy backend configuration.
7. Smoke-test parent/student login, a nested-route refresh, lesson resume, voice fallback, quiz completion, upload retrieval, report ownership, and pending evidence retry.
8. Enable database/volume backups and review logs without submitting real child data during the smoke test.

## Functional status boundaries

- Reports: authenticated, ownership-checked JSON report endpoint is implemented. PDF generation is **not implemented**.
- Certificates: **not implemented**; dashboard certificate counts are presentation/mock data and are not downloadable assets.
- Stripe: **not implemented**. Basic/Premium/Elite products, trial rules, currencies, price IDs, subscription persistence, checkout, customer portal, and webhook verification remain a separate milestone.
