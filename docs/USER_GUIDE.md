# HomeWiseEdu User Guide

This guide covers currently implemented functionality.

## Administrator

### Login and monitoring

Sign in through the normal login page with an authorised Admin account; public registration creates Parents only. The Admin dashboard provides parent/student lists, filters, progress, evidence counts, current lessons, and AI tutor session summaries. Open a record for detail. Email changes are not implemented.

### Curriculum validation and import

1. Open **Curriculum** and the import interface.
2. Select the approved CSV and run validation/preview.
3. Review errors, matched/new lessons, hierarchy warnings, cadence, and expected sessions.
4. Correct and revalidate until the preview matches the intended curriculum.
5. Import only as a separately authorised action; retain the approved CSV as the audit source.

Validation/preview is non-mutating. New imported lesson days remain pending.

### Weekly and multi-day lessons

- **Multi-day:** Day 1 Explore, Day 2 Practice, Day 3 Apply.
- **Weekly Lesson:** one standalone session.

Do not mix formats within a lesson. Reimport cannot change an existing lesson’s cadence, protecting student history.

### Review, edit, publish, archive

Open a lesson to review its hierarchy, cadence, objectives, teaching content, days, and quiz status. Edit supported lesson-day fields, then publish/unpublish approved days. Students receive only eligible published content.

Archive removes a lesson from normal active use while preserving history; Restore returns it. Permanent deletion is for unused lessons only. Dependency data identifies progress, sessions, evidence, AI interactions, and quiz attempts; dependencies block deletion. Use archive for used lessons.

### Quiz readiness

Curriculum practice prompts are not automatically reviewed quiz questions. Confirm appropriate questions/options/answers, resolve any quiz-review flag, and test with an authorised QA student only after practice readiness.

### Parent/student administration

Admins can view supported parent details/children, edit supported profile fields, send a reset link, and suspend/reactivate accounts. Student views show pathway, progress, evidence, quiz scores, and tutor activity.

## Parent

### Register, login, and reset password

Create a Parent account from the public registration page, then sign in. For a forgotten password, choose **Forgot password?**, enter the account email, and use the emailed link before expiry. The response intentionally does not reveal whether an email is registered; check spam/junk when necessary.

### Add and manage a child

1. Select **Add child** from the dashboard.
2. Enter name, age, education system/country, and level.
3. Select available subjects and an avatar/optional picture.
4. Optionally enable direct student login and provide the requested credentials.
5. Select **Create child**.

Curriculum availability depends on published content matching level and subjects. Existing child controls allow supported detail, subject, picture, and credential updates. The owning Parent retains access when direct login is enabled.

### Dashboard, profile, progress, and evidence

Use the dashboard and child views to review available lessons, progress, quiz/evidence information, and portfolio records. The header avatar opens the read-only Parent profile; **Settings → Profile** edits supported details/picture, **Account** shows account information, and **Security** links to password reset.

## Student

### Dashboard and lessons

Sign in with credentials enabled by the Parent. The dashboard shows the current lesson, pathway, quiz readiness, XP/reward summaries, feedback, and portfolio access. Select an available lesson, read its notes/examples, and start class when ready.

### Ms Ade classroom

Allow microphone access. The student can answer naturally, ask for help/clarification, or interrupt. The backend—not the voice model—controls progression and academic evidence. A quiet room and headphones can reduce echo. Avoid refreshing or opening duplicate copies of the same active session.

### Quiz and evidence

The quiz unlocks only at **Practice Ready** and when reviewed quiz content exists. Submit answers through the quiz screen; feedback/result appear and an immutable attempt snapshot is saved. Retrying the same submission does not duplicate the attempt.

Where requested, submit written and/or supported file evidence. Stored evidence appears in authorised portfolio, Parent, and Admin views after processing. Dashboard progress comes from persisted lesson, quiz, and evidence records.

### Moving forward

- Multi-day lessons move from Explore to Practice to Apply.
- Completing a Weekly Lesson moves toward the next eligible curriculum lesson.

The next item must be published and match the student’s level/subjects. If none appears, an Admin should check publication, cadence, subject assignment, and quiz/evidence requirements rather than creating duplicates.

## Current limitations

- Payments/subscriptions are not connected.
- PDF reports and certificates are not implemented.
- Final production curriculum and reviewed quizzes require client content approval.
