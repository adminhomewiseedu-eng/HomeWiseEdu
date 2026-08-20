# Phase 3 migration notes

Alembic is the production schema authority. `backend.main` retains `create_all`, the local SQLite compatibility helper, and local/demo seeding only when the process is non-production and `AUTO_INIT_DB=true`. Production runs none of them.

`0001_current_schema` is the clean-database baseline. `0002_phase_hardening` is deliberately conditional so a reviewed legacy database can be stamped at the baseline and upgraded without blindly dropping or recreating tables. See `DEPLOYMENT_RAILWAY.md` for the required backup, duplicate audit, stamp, and upgrade sequence.
