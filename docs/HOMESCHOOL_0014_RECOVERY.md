# Schema-compatible backend recovery

This is a separate recovery branch based on deployed Bible Study commit
`c550437d0744ad4a50fafca6a640bce8db6895bd`. It does not change feature release
`ea6a625a6bd5d34050fa5acd01414b156eb15f6d`, main, transport or pedagogy.
Use the exact published recovery SHA in the release report, not an unpinned tip.

## Compatibility contract

- Only `0013_programme_entitlements` and `0014_lesson_assignments` are supported.
- Production `/ready` verifies the single revision, every old mapped table/column,
  and (for 0014) the nullable integer week column, positive-week CHECK, assignment
  columns/primary key, three foreign keys and delete actions, position CHECK,
  lookup indexes and active-only unique index. Unknown/incomplete schemas fail 503.
- The old ORM intentionally does not map assignments or weeks. Normal account,
  lesson, dashboard, quiz and progress operations therefore leave those fields alone.
- Permanent lesson deletion checks all assignment rows, including cancelled rows,
  and authored weeks. It refuses deletion even without student learning history.
- Old curriculum reimport preserves stable IDs and ignores the unknown week column;
  populated-data tests prove it leaves assignments and authored weeks unchanged.
- No assignment/browser controls or new APIs are implemented in this recovery.
  New assignment actions are unavailable, not silently rerouted to old APIs.

## Frontend compatibility

The frontend tree is byte-for-byte inherited from c550437; root requirements.txt
and backend dependencies are also unchanged. Its existing login/dashboard/lesson
contracts are covered by real HTTP tests. For full recovery retain or restore
frontend c550437. If the feature frontend has already deployed, restore it first:
the feature UI calls assignment/browser APIs deliberately absent from recovery.
Keep the schema at 0014 and preserve all new data while using the previous UI.

## Local verification (no production access)

Use an existing Python environment with backend/requirements.txt installed.
Set DATABASE_URL to a fresh disposable local database, ENVIRONMENT=test,
AUTO_INIT_DB=false, SEED_MODE=none and local temporary upload/audio directories.

```text
python -m pytest backend/tests/test_recovery_schema.py -q
python backend/tests/verify_recovery_postgres.py
```

The PostgreSQL 18 verifier uses existing Windows PostgreSQL tools, a random
localhost-only port, generated disposable credentials and synthetic accounts.
It represents existing 0013 using the c550437 model metadata plus a baseline
revision marker, and runs the exact approved 0014 fixture through real Alembic.
It never runs the known-broken historical clean-bootstrap chain. It tests 0013,
0014 empty, and 0014 with active/cancelled assignments and authored weeks, including
actual production-mode Uvicorn starts and four real HTTP logins per database.
Every local process is stopped in finally; synthetic logs remain outside Git.

`backend/tests/fixtures/0014_lesson_assignments.py` is an exact, inactive copy of
the approved migration solely for repeatable compatibility tests. The recovery
branch's active migration head remains 0013. **Never run Alembic upgrade head,
downgrade, revision --autogenerate or metadata-based schema synchronization from
this branch against production.** It is an application recovery, not a schema runner.

## Recovery triggers and preconditions

Invoke only after separately approved recovery execution, if the feature backend
fails after migration 0014 succeeded or has an established application regression.
If migration itself fails, stop and verify its actual revision before choosing any
application action. Never guess the resulting schema or downgrade automatically.

Before the feature migration, record/verify:

1. Published exact recovery SHA exists in both repositories; both auto-deploy
   sources still watch main, not the recovery branch. No CI push hook deploys it.
2. The current verified encrypted backup exists and matches its recorded checksum.
   Do not restore it automatically or alter it as part of application recovery.
3. Recovery source is reachable from the client repository and Railway's explicit
   `serviceInstanceDeployV2(commitSha:...)` operation remains available.
4. Backend root stays repository root, builder Railpack, config-file override
   disabled, pre-deploy empty, start command unchanged, health path /ready,
   AUTO_INIT_DB=false and the correct Postgres reference. No pending changes.
5. The frontend c550437 source remains available. Do not blindly redeploy c550437
   backend after 0014: its readiness requires 0013.

## Exact future execution

Do not run during recovery preparation. After explicit production recovery approval,
from this checkout run the following, substituting the full immutable recovery SHA
reported with this branch. The script checks that it matches the published client
recovery branch before any deployment:

```powershell
.\scripts\recover_homeschool_0014.ps1 `
  -RecoveryCommit '<FULL_VERIFIED_RECOVERY_SHA>' `
  -ApprovedForRecovery -Schema0014Verified
```

The operator must first verify 0014 through the approved migration runner/evidence;
the switch is an explicit prerequisite, not a database verification substitute.
The script reads configuration without printing secrets, refuses drift, holds or
explicitly restores frontend c550437, deploys ONLY the pinned recovery SHA to
backend, checks the returned deployment SHA/status with a 15-minute deadline and
requires HTTP 200 at /health, /ready and homewiseedu.com. Its exact backend API call:

```graphql
mutation {
  serviceInstanceDeployV2(
    environmentId: "f22a49df-1a16-4171-b498-29844997a398"
    serviceId: "ec8adde3-9dcc-4fd1-ac05-b9b85e03756c"
    commitSha: "<FULL_VERIFIED_RECOVERY_SHA>"
  )
}
```

It does not change service sources/variables, run a migration/seed, restore a
database, create QA users or merge main. Do not execute a mutation merely to test
this procedure. Only API signatures, script syntax/guards and local application
compatibility are validated during preparation; a live deployment is not claimed.

After deployment inspect sanitized build/runtime logs and independently verify
revision 0014, assignment/week/progress aggregate preservation through an approved
read-only path. Use approved existing Homeschool/Bible accounts, without creating
assignments, attempts or evidence, for authenticated smoke tests. If deployment,
SHA, readiness or authorization checks fail, stop and report. Do not repeatedly
redeploy, weaken readiness, discard assignment/week values or restore a stale DB.

Reverting application code does not reverse a database migration. Database recovery
and any later return to the feature revision require their own explicit approval.

## Preparation verification — 24 November 2026

- Complete backend suite: 103 passed on a new disposable SQLite database with
  synthetic legacy demo fixtures. Ten tests specifically exercise recovery shape,
  preserved data and fail-closed behavior. External API credentials were cleared.
- PostgreSQL 18.6: all three scenarios passed real Alembic/HTTP checks, including
  populated assignments, cancelled rows, authored weeks, protected deletion,
  reimport preservation and snapshots before/after production-mode startup.
  All local Uvicorn/PostgreSQL processes were stopped.
- Unchanged frontend: 96 tests passed; Vite 6.4.5 production build passed, with
  artifacts outside Git and VITE_API_URL=https://example.invalid. No fresh browser
  visual acceptance or live Realtime session was performed for this backend-only
  recovery; existing frontend code and lesson transport are unchanged.
- Python compilation, pip check, active Alembic head (0013), exact normalized
  fixture match to approved 0014, PowerShell parser and unapproved-execution guard
  passed. The recovery deployment API has NOT been executed in preparation.
- Existing Passlib/bcrypt-version and Starlette/httpx deprecation warnings remain;
  successful real authentication was verified. No dependency changes were made.
- Publication safety: backend/frontend deploy triggers target main; the migration
  service has no trigger. No effective staged changes or repository workflow
  deploying a pushed recovery branch was found. Recheck at execution time.
