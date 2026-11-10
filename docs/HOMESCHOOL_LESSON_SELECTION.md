# Homeschool lesson selection and parent plans

Local implementation only. Production migration and release require separate approval.

## Data and behavior

`0014_lesson_assignments` follows `0013_programme_entitlements`. It adds nullable
positive `lessons.curriculum_week` and `lesson_assignments`. It does not backfill
weeks, change enrollment, reset sessions or update progress/quiz/evidence/XP.
Assignments reference existing lesson/day identities; completion is read from
`StudentProgress`. Duplicate child/session/date assignments reuse the record.
Rescheduling conflicts return 409. Cancellation retains the assignment record.
Lessons with assignments cannot be permanently deleted.
The uniqueness rule covers active assignments only, so a cancelled date can be
used again without deleting its historical plan record.

Parents select a child under **Plan learning**, filter subject, curriculum
week and unit, choose an assignment date and priority (0 first), and assign sessions.
They can change dates/priorities or cancel. Completed assignments are listed
separately. An assignment that becomes ineligible can still be cancelled.

Students see outstanding parent assignments first and may choose any assigned
subject. Independent browsing remains available. Due assignments determine the
primary dashboard recommendation; future assignments remain visible. Choosing
Week 10 never completes Weeks 1–9. Start/Resume uses the existing lesson ID and
day launch callback. Quiz readiness and teaching progression remain unchanged.

All new planning/browsing endpoints are Homeschool-only. They validate child
ownership, parent role for mutations, parent-derived programme, enrollment,
level, archive state and publication of the exact day. Assignments never grant
access. Existing classroom entry points pass day identity into the shared
authorization helper. Historical evidence retains its existing entitlement
checks without being hidden merely because a child advanced a level.

## Authored curriculum weeks

No authoritative CSV/spreadsheet was available locally. No existing lesson
number is assumed to be a week number. Unknown weeks display **Week not supplied**.
The browser fixtures use synthetic Week 10 metadata solely to test selection.
Subject, unit and lesson/session selection work when every week is null; week
population is not a prerequisite for this release.

To enable real Week 10 selection, supply the authoritative curriculum CSV with
an optional **Curriculum Week** column containing positive whole numbers.
All rows for a lesson must agree. Existing identity columns must remain stable:
Subject, Level, Unit_Name and Lesson Number. Blank/absent weeks preserve any
previously authored value; they never guess or erase it. Use existing Admin CSV
validation/preview and review identity matches before any separately approved
import. No curriculum has been imported by this implementation task.
The full importer updates teaching content as well as metadata. Do not upload a
partial crosswalk to populate weeks. A future week-only operation needs separate
approval and must update only verified existing lesson IDs.

## Local verification

Run from the repository root in PowerShell. Use the existing local Python venv.
These commands create a new disposable SQLite database and synthetic fixtures;
they do not run a production migration or use an existing database.

```powershell
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $env:TEMP ('hwe-selection-browser-' + [guid]::NewGuid().ToString('N') + '.db')).Replace('\', '/')
$env:ENVIRONMENT = 'test'
$env:AUTO_INIT_DB = 'false'
$env:SEED_MODE = 'none'
$env:OPENAI_API_KEY = ''
$env:ALLOWED_ORIGINS = 'http://127.0.0.1:3012'
backend/venv/Scripts/python.exe -m backend.tests.lesson_selection_browser_fixture
backend/venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8012
```

In another PowerShell window:

```powershell
cd frontend
$env:VITE_API_URL = 'http://127.0.0.1:8012'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 3012 --strictPort
```

Open `http://127.0.0.1:3012/login`. Disposable fixture accounts are
`planning-parent@example.test` and `planning-student@example.test` with the
test-only password `LocalPlanning123!`. These identities exist only in the
new fixture database. Never create them in production.

1. Parent: choose Planning child, Mathematics, Week 10, date and priority; assign.
2. Assign English through Week not supplied. Reschedule, reorder and cancel.
3. Student: verify assignments first, browse both subjects, and inspect unknown weeks.
4. Confirm 0 completed lessons and 0 XP after planning/browsing.
5. Check 320, 375, 390, 430, 768, 1024 and 1440px in DevTools.
6. Stop both services using Ctrl+C. Preserve any existing local databases.

Automated browser checks (cached Playwright Chromium; no browser download):

```powershell
cd frontend
node tests/lessonSelection.browser.mjs
```

The browser test blocks non-local requests, creates screenshots under the OS
temporary directory and closes its browser. It does not exercise live teaching.

Migration verification: `backend/venv/Scripts/python.exe backend/tests/test_migration_0014_assignments.py`
executes real Alembic operations against an in-memory SQLite database.
`backend/venv/Scripts/python.exe backend/tests/verify_0014_postgres.py` uses the existing
PostgreSQL 18 Windows tools to create a separate localhost-only disposable cluster,
run real Alembic upgrade/downgrade/re-upgrade checks with synthetic historical
records, and stop the cluster in a finally block. It retains synthetic logs in
the OS temporary directory. Both checks passed locally. Downgrade refuses to
discard assignments or authored weeks.

For an existing disposable local database at 0013, explicitly approve and run
`alembic upgrade 0014_lesson_assignments` with its local DATABASE_URL. Startup does
not run Alembic. Do not use the known-broken historical clean-bootstrap chain.

## Feature file inventory

Existing files modified for this feature (earlier unrelated dirty work is preserved):

- `backend/main.py` — readiness revision only.
- `backend/models.py`, `backend/schemas.py` — optional week metadata and assignments.
- `backend/routers/auth.py` — shared level/day authorization; historical evidence exception.
- `backend/routers/parent.py`, `backend/routers/student.py` — planning, browsing and recommendation.
- `backend/routers/curriculum.py` — published metadata and assignment deletion dependencies.
- `backend/routers/evidence.py` — day authorization on submission; retain historical evidence access.
- `backend/routers/lessons.py`, `backend/routers/voice.py` — pass day identity to authorization only; no teaching/Realtime internals changed.
- `backend/services/curriculum_importer.py` — optional authored Curriculum Week column.
- `frontend/package.json` — include all utility regression tests in the test command; dependencies unchanged.
- `frontend/src/services/api.js` — learning plan client.
- `frontend/src/components/templates/ParentDashboardScreen.jsx`.
- `frontend/src/components/templates/StudentDashboardScreen.jsx`.
- `frontend/src/index.css` — scoped responsive planning controls.

New files:

- `backend/migrations/versions/0014_lesson_assignments.py`.
- `backend/services/lesson_selection.py`.
- `backend/tests/test_lesson_selection.py`.
- `backend/tests/test_migration_0014_assignments.py`.
- `backend/tests/verify_0014_postgres.py`.
- `backend/tests/lesson_selection_browser_fixture.py`.
- `frontend/src/components/organisms/LessonSelection.jsx`.
- `frontend/src/utils/lessonSelection.js`.
- `frontend/src/utils/lessonSelection.test.js`.
- `frontend/tests/lessonSelection.browser.mjs`.
- `docs/HOMESCHOOL_LESSON_SELECTION.md`.

Screenshots, test databases, native PostgreSQL test data and test logs remain
outside the repository in the OS temporary directory. They are not release content.

## Controlled production release plan (not executed)

Preparation baseline is Bible Study release commit
`c550437d0744ad4a50fafca6a640bce8db6895bd`. The existing Bible Study branch is
unchanged. A separate local branch contains only this document's 27 feature
files. Root requirements.txt, dependency lockfile, Bible registration/routing,
and deployment configuration are inherited unchanged from that baseline.

No production service, database revision or backup availability was inspected
during this local preparation. The following live checks require separate approval.

1. **Approve publication and preflight.** Verify pushing the dedicated branch
   will not auto-deploy either service, then approve pushing the exact reviewed
   commit to the production-linked repository. Do not merge into main. Verify
   current backend/frontend deployment IDs and immutable source SHAs; preserve
   them in the release record. Confirm schema is exactly
   `0013_programme_entitlements`; stop on any different revision. Verify backend
   Root Directory is repository root, builder Railpack, Config File Path disabled,
   start command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, health
   check `/ready`, empty pre-deploy command, and the existing Postgres reference.
   Verify frontend Root Directory `/frontend` and its public API URL. Stop if
   there are unexpected pending changes. Do not activate repository railway.json
   or alter credentials. Confirm both exact release builds can be deployed.
2. **Verify a current backup.** Approve a fresh consistent encrypted backup if
   the last verified backup predates current writes. Independently restore and
   verify it in isolation before migration. Record checksum, revision, timestamp
   and aggregate counts without exposing credentials or personal records. An
   older verified backup does not establish protection for newer data. Do not
   restore over production during normal release or smoke testing.
3. **Approve one explicit migration.** Use a one-shot runner pinned to the exact
   release SHA, the existing production Postgres reference, required configuration
   and Python dependencies. Disable automatic starts/restarts; confirm no seed or
   app startup command executes. Use bounded lock/statement timeouts for the
   Alembic process, for example `PGOPTIONS='-c lock_timeout=5s -c statement_timeout=120s'`.
   After confirming `alembic current` is exactly 0013, run only:

   ```text
   python -m alembic upgrade 0014_lesson_assignments
   python -m alembic current
   ```

   Confirm final revision 0014; inspect the nullable week column/positive check,
   assignment foreign keys, active-only unique index and other indexes. Confirm
   zero assignments, zero populated weeks, stable existing curriculum IDs and
   unchanged aggregate account/progress/quiz/evidence/session counts while
   accounting for any legitimate concurrent activity. Disable the runner.
   Failure must stop the release; do not repeatedly retry or run the historical
   clean-bootstrap chain. PostgreSQL DDL is transactional, but verify the actual
   resulting revision instead of assuming rollback succeeded.
4. **Deploy backend immediately.** Deploy the same exact SHA explicitly and
   confirm source, `/health` 200 and `/ready` 200, database connectivity and no
   migration/seed execution in application startup logs. Migration takes a brief
   schema lock. Also, the old backend requires revision 0013 in `/ready`, so its
   readiness response becomes 503 after migration until the new backend is live.
   Schedule this coordination window; zero downtime is not established.
5. **Deploy frontend.** Only after backend checks pass, explicitly deploy the
   same SHA to frontend with its existing production API configuration. Confirm
   build/deployment health, website HTTP 200, no stale bundle or API errors.
6. **Smoke test.** Use approved existing Homeschool and Bible parent/student
   accounts, or have the owner test. Do not create accounts or alter existing
   assignments/progress without approval. Verify unknown-week subject/unit/lesson
   browsing, parent controls, entitlement rejection and unchanged Bible navigation
   at desktop and mobile sizes. Mutating assignment create/reschedule/cancel and
   actual learning completion require an approved dedicated QA child or explicit
   owner-led test. Preserve real progress and never populate guessed weeks.

### Recovery limits

- If migration fails, stop before application deployment. Verify revision and
  logs; retain the previous applications if still compatible with the actual
  schema. A failed migration must not trigger automatic downgrade or seeding.
- If frontend fails, restore its recorded previous healthy deployment while
  keeping the healthy new backend and schema 0014.
- If backend fails after migration succeeds, hold the previous frontend and
  prefer a reviewed roll-forward backend repair. Simply restoring c550437 is
  insufficient: its strict `/ready` expects 0013 and reports 503 on schema 0014.
  An application recovery revision that supports the retained 0014 schema and
  readiness check needs separate approval and validation. It is not prepared or
  deployed automatically by this task.
- A coordinated downgrade to 0013 is an approval-only option when there are no
  assignment records (including cancelled records) and no authored week values.
  The migration refuses otherwise. Never delete plans or clear weeks to bypass
  the guard. Do not downgrade 0013 or erase Bible programme classifications.
- Reverting code does not undo schema changes. Restoring a database backup can
  lose subsequent legitimate writes and is a separately approved disaster
  recovery action, not a routine application rollback.

Release approval must specify the reviewed SHA, backup verification, one-time
migration, backend deployment, frontend deployment and any QA data writes.
No remote push, production access, migration or deployment is part of local preparation.

## Local release verification — 10 November 2026

Reviewed all 27 feature files against c550437 in an isolated release checkout.
The final review added an explicit unit selector, backed by stable unit IDs,
so null-week lessons can be selected by subject, unit and lesson/session.
Unknown weeks remain null; no curriculum or progress records are backfilled.

- Backend: `python -m pytest backend/tests -q --tb=short --disable-warnings`
  — 106 passed, using a fresh disposable SQLite database and required legacy
  local demo fixtures. Existing deprecation/bcrypt warnings are not fixed here.
- Frontend: `node --test src/services/*.test.js src/utils/*.test.js` — 99 passed.
- Build: `node node_modules/vite/bin/vite.js build` — passed with
  `VITE_API_URL=https://example.invalid`; no production service was contacted.
- Real PostgreSQL 18: `python backend/tests/verify_0014_postgres.py` — upgrade,
  populated-data downgrade refusal, empty-new-data downgrade and re-upgrade
  passed; account programmes and representative historical records preserved.
- Python compilation, `git diff --check` and local Alembic head check — passed.
- Cached Playwright: `node tests/lessonSelection.browser.mjs` — parent creation,
  rescheduling, cancellation, priority, unknown-week unit filtering, student
  browsing and both lesson launch paths passed. Widths 320, 375, 390, 430, 768,
  1024 and 1440 had no page-level horizontal overflow. Desktop/mobile captures
  were visually inspected. No JS errors or unexpected failed API calls occurred;
  optional missing-avatar 404s and intentionally blocked external fonts are expected.
- No live voice/Realtime teaching was started. Its implementation is inherited;
  lesson/voice endpoint changes only pass exact day identity into authorization.
- All four new route handlers were reviewed: student lesson-options GET and
  parent assignment GET/POST/PATCH. Bible children are rejected by the new
  Homeschool service. Students cannot mutate parent plans. Creation/rescheduling
  requires current enrollment, level and published/unarchived session. A parent
  may cancel their own now-ineligible assignment; this grants no lesson access.
- Test servers and the disposable PostgreSQL process were stopped. All generated
  databases, native cluster files, screenshots and logs are outside the release.

Production configuration, current revision and current backup remain live
preflight items requiring approval; they were not accessed in this preparation.
