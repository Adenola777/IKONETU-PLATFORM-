# Running IkonetU

This file says how to tell that something is wrong, what to do first, and how to learn from it afterwards. It was written on 15 October 2026, before the first deployment. Nothing in it has been tried against the live service yet, and every step that depends on Render, Supabase or Sentry is marked **unverified** until it has been done once.

## Who is on call

The owner is on call until IkonetU has staff. The person on call needs access to four places: the Render dashboard, the Supabase dashboard, the Sentry project, and this repository. Record who holds each one here when that changes.

| Place | Who holds access |
|---|---|
| Render | Not recorded yet |
| Supabase | Not recorded yet |
| Sentry | Not recorded yet, because no Sentry project exists |
| GitHub | Adenola777 |

## How a problem shows itself

| Signal | Where | What it means |
|---|---|---|
| `GET /api/health` answers 503 | An uptime monitor pointed at it (not set up yet) | The app runs, but Supabase did not answer within five seconds |
| `/` does not answer | The same monitor, or Render's own health check | The app itself is down |
| An error in Sentry | The Sentry project, once `SENTRY_DSN` is set | A server action or route failed. The event names it, for example `evidence.save_failed`, with the error code and the venture's id |
| A line with `"level":"error"` | Render's log stream (**unverified**: how long Render keeps logs and how its search works) | The same failures as Sentry, one JSON line each, with the time, the event name and the codes |
| "Scores to update" on `/admin/evidence` | The staff queue | A decision was saved but the founder's score did not update after three attempts |

An uptime monitor is not part of the code. Any monitor that can call an address every few minutes and alert by email or text is enough. Point it at `https://<the public address>/api/health` and alert when it answers anything but 200 twice in a row.

## What to do first

1. **Supabase is unreachable** (`/api/health` answers 503). Open the Supabase dashboard and its status page. The app has a 15-second limit on every call to Supabase, so pages fail with an error message rather than hang. Nothing in the app needs restarting. Render's health check stays on `/`, which does not depend on Supabase.
2. **The app is down** (`/` does not answer). Open the latest deploy on Render. If the last deploy broke it, redeploy the previous one from Render's deploy list (**unverified**: Render's rollback steps). A database migration cannot be undone by redeploying, because the migrations only move forward.
3. **Errors after a release.** Compare the Sentry events and the log lines with the release time. If the cause is in the code, redeploy the previous release first and fix the cause afterwards.
4. **A score did not update.** Open `/admin/evidence` and press "Recompute the score" beside the venture. If it fails again, the log line `score.record_failed` carries the database's error code.
5. **Many sign-in failures.** The log lines `auth.code_request_failed` and `auth.code_check_failed` carry Supabase Auth's status and code. A 429 means Supabase refused because of its own rate limit (**unverified** against the real project).

## Backups and restoring

Whether the Supabase project has daily backups or point-in-time recovery depends on its plan, which has not been checked. Before launch the owner checks four things in the Supabase dashboard and records the answers here.

| Question | Answer |
|---|---|
| Which plan is the project on, and does it include daily backups? | Not checked |
| Is point-in-time recovery switched on, and how far back does it reach? | Not checked |
| Do the backups include the files in Storage (pitches and evidence files), or only the database? | Not checked |
| When was a restore last tried, into a separate project, and did the app work against it? | Never |

A backup that has never been restored is not known to work. A restore drill means restoring into a separate Supabase project, pointing a local copy of the app at it, and signing in as a test founder and a test investor.

## After an incident

Write a short note within a week, kept in `docs/incidents/` with the date in its name. It answers five questions in plain sentences:

1. What did people see, and for how long?
2. What caused it?
3. How was it found, and how long did that take?
4. What fixed it?
5. What change makes it less likely, or quicker to find, next time? Each change gets an owner and a date.

The note describes what happened. It does not blame a person.

## Turning on Sentry

1. Create a Sentry project for a Next.js app. Choose Sentry's EU data region if the account offers it (**unverified**: the regions Sentry offers).
2. Add Sentry to the privacy policy as a processor of error reports before anything is sent. The policy was adopted on 15 October 2026, so this is the owner's change to make.
3. Set `SENTRY_DSN` on Render, and optionally `SENTRY_ENVIRONMENT`, then restart the service. A rebuild is not needed, because the server reads both when it starts.
4. Check it once: make a test founder's action fail and confirm the event arrives with only the event name, the codes, the venture's id, and the request's method and path.

What Sentry receives was checked on 15 October 2026 against a local stand-in for Sentry's endpoint. Without a filter, Sentry's library attached the whole request, including the sign-in cookies and the text of the form, although `sendDefaultPii` was off. `apps/web/lib/sentry-scrub.ts` now removes the request's headers, cookies and body, the user and the breadcrumbs from every event, and the same check found none of them afterwards.
