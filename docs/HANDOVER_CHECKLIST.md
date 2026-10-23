# HomeWiseEdu Handover Checklist

Never record passwords, recovery codes, API keys, database URLs, or tokens in this repository.

## Ownership and access

### GitHub
- [ ] Client organisation owns the canonical repository and deployment branch.
- [ ] Two authorised maintainers have appropriate access; former temporary access is removed.
- [ ] Branch protection and deployment integration are documented.
- [ ] Recovery email and 2FA are client-controlled.

### Railway
- [ ] Client owns the project and can access frontend, backend, PostgreSQL, volume, deployments, and logs.
- [ ] Root directories, health checks, migration command, and deployment branch are correct.
- [ ] Billing, recovery email, and 2FA are client-controlled.

### PostgreSQL and storage
- [ ] Database and backend volume belong to the client project.
- [ ] Connection details exist only in service secrets/an approved password manager.
- [ ] Backup retention, off-site copy, restore owner, and data-retention policy are agreed.
- [ ] A restore has been tested outside production.

### Domain/DNS
- [ ] Client controls registrar/DNS, auto-renewal, billing, recovery, and 2FA for `homewiseedu.com`.
- [ ] Railway and Resend DNS records are documented.
- [ ] Dependencies are reviewed before changing/removing records.

### Resend
- [ ] Client controls the account and verified domain.
- [ ] Approved sender/reply-to settings are configured only in backend secrets.
- [ ] Client can access delivery logs/suppressions and controls recovery/2FA.
- [ ] Password-reset delivery is tested without exposing its token.

### OpenAI
- [ ] Client owns the production project and controls billing, limits, members, recovery, and 2FA.
- [ ] API access is stored only in backend secrets.
- [ ] Realtime model/voice configuration and usage monitoring are documented.

### Environment configuration
- [ ] Every README variable has an owner and purpose.
- [ ] Secrets exist only in Railway or an approved secret manager.
- [ ] Frontend contains only public build-time configuration.
- [ ] Demo seeding and development reset-link capture are disabled in production.
- [ ] Origins, frontend URL, storage root, upload limits, and pool settings are reviewed.
- [ ] Rotation procedure is documented outside source control.

## Backup checklist

- [ ] Back up PostgreSQL before migrations or material curriculum operations.
- [ ] Record environment, time, migration revision, and verification owner.
- [ ] Back up evidence/profile uploads separately; TTS cache is disposable.
- [ ] Encrypt backups and restrict access.
- [ ] Restore into isolation and verify migrations, foreign keys, and record counts.
- [ ] Check users, children, lessons/days, sessions, progress, questions, immutable quiz attempts, evidence, and referenced files.

## Production smoke test

- [ ] `homewiseedu.com`, backend `/health`, and `/ready` succeed over HTTPS.
- [ ] Parent registration/login/reset, child creation, subjects, and optional student credentials work.
- [ ] Student login/dashboard ownership is correct.
- [ ] Published multi-day and Weekly Lessons select the correct next session.
- [ ] Classroom retains backend-authoritative progression.
- [ ] Practice-ready quiz uses reviewed questions and persists one immutable attempt per submission ID.
- [ ] Evidence submit/retrieve and parent/admin progress views work.
- [ ] Admin curriculum validation/preview is non-mutating and dependency data renders.
- [ ] Transactional mail uses the verified HomeWiseEdu domain.
- [ ] Logs contain no secrets, reset tokens, or unnecessary private data.

## Authenticated mobile QA

Use temporary QA accounts at minimum at 390 px mobile and 1440 px desktop.

- [ ] **Parent:** dashboard, add/edit child, subjects, progress/evidence, profile/account/security, uploads and modals.
- [ ] **Student:** dashboard, lesson/classroom layout, quiz, completion/evidence, progress and portfolio.
- [ ] **Admin:** dashboard, parents/students, curriculum list/detail, validation interface, tables, filters, modals and settings.
- [ ] No page-level overflow, clipping, overlap, unusable navigation, tiny touch targets, or desktop regression.
- [ ] Classroom check is visual only unless a planned functional test is authorised.

## Client curriculum/content

- [ ] Client supplies and approves authoritative final CSV files.
- [ ] Each lesson explicitly uses multi-day or Weekly Lesson cadence.
- [ ] Multi-day lessons contain exactly Explore, Practice, Apply; Weekly Lessons contain one row.
- [ ] Subjects, levels, units, lesson numbers, objectives, scripts, and publication decisions are approved.
- [ ] Validate/preview before import; review matched/new hierarchy, warnings, cadence, and expected sessions.
- [ ] Review imported pending days before publication.
- [ ] Supply/review quiz questions for new or changed lessons where quiz use is required.
- [ ] Current/test curriculum is not represented as complete final client curriculum.
- [ ] Assign ongoing content owner and review process.

## Sign-off

- [ ] Technical, content, security/recovery, and backup ownership accepted.
- [ ] Final authenticated mobile QA completed.
- [ ] Known limits accepted: no Stripe/subscriptions, PDF reports, or certificates.
