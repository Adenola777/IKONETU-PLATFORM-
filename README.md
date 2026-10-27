# IkonetU platform

This repository holds the new IkonetU codebase: the web app, the score engine and the database setup. It follows the PRD, TRD and SRD written in October 2026.

The web app is written in Python. It was rebuilt from a Next.js app on 17 October 2026, at the owner's request, and `service/README.md` records how the rebuild was checked and where it differs.

## What is in it

| Folder | Contents |
|---|---|
| `service` | The web app, in Python with FastAPI and Jinja2: the public website, sign-in, the founder and investor sides, the staff pages, `GET /api/health` for an uptime monitor, and `POST /api/v1/waitlist`, which no page calls since sign-up replaced the form. `service/app/score_engine` holds the IkonetU Score rules (rubric v2), the score calculation, league placement and the "next best actions" list |
| `supabase/migrations` | Database tables, access rules (row level security), the private evidence and pitch buckets, and the rubric seed |
| `supabase/tests` | SQL checks that prove the access rules work |

The mobile app (Expo) and the mentor role come next.

## The website

The public pages were built from the design boards of October 2026 and are served by the same app as sign-in and the dashboard.

| Address | Page |
|---|---|
| `/` | Home |
| `/for-founders` | For founders |
| `/for-investors` | For investors |
| `/readiness-check` | Readiness self-check. The answers stay in the browser and are never sent |
| `/pricing` | Pricing: Free and Premium for founders and for investors |
| `/trust-and-safety` | Trust and safety |
| `/privacy` | Privacy policy |
| `/terms` | Terms |
| `/cookies` | Cookie policy |
| `/complaints` | Reporting and complaints |

The investor interest form was retired on 15 October 2026, when investor accounts opened. Every investor button on the website now leads to account sign-up, and the old address `/investor-interest` redirects to `/for-investors`. The `investor_interest` table keeps the rows it already holds.

The seven product pictures on the website were captured from this app on 15 October 2026, signed in against a local test copy of the database loaded with the website's six sample founders. Each picture carries a "Sample data" label. On 21 October 2026 five of them (the score card, the next three steps, founder search, a piece of evidence and the momentum card) were captured again on the same sample founders, served through a stand-in for Supabase built the way the route tests build theirs, because the IkonetU Score changed what those screens show.

On 21 October 2026 the owner approved the website copy audit. How it works, About and Questions were removed: `/how-it-works` and `/about` redirect to the home page and `/questions` to For founders. The walkthrough video was taken off the website.

IkonetU Technology Limited adopted the privacy policy, the terms and the cookie policy on 15 October 2026. Each page's title and description are in `service/app/pages.py`, which the site map also reads. `/robots.txt` keeps the API, sign-in and the signed-in pages out of search engines.

The page markup lives in `service/app/templates/site/pages` and the styles in `service/app/static/css/site.css`. The behaviour of each page, such as the menu, the pitch player and the readiness self-check, is in `service/app/static/js/ik`. The signed-in pages use the same shared styles, with their own additions in `service/app/static/css/app.css`.

The fonts are kept in `service/app/static/fonts` and served by the app, so no visitor's browser asks Google for them.

## The signed-in app

After sign-in, a new person chooses at `/onboarding` whether they are a founder or an investor. `service/app/session.py` sends each person to their own pages, so a founder cannot open the investor pages and nobody but staff can open the staff pages. The database enforces the same separation through row level security, so a bug in a page cannot widen what a person sees.

**Founders** (`/dashboard`)

| Address | What the founder does |
|---|---|
| `/dashboard` | Sees the IkonetU Score with its league, a chart of the eleven areas, the next three steps and the monthly record; publishes or hides the profile; sees the readiness check investors see; and edits the venture's details and its ask. Investors do not see the score |
| `/dashboard/pitch` | Uploads a pitch within the pitch rules an admin sets, of up to 90 seconds and 50 MB at most, with a typed transcript. The video goes from the browser straight to the founder's folder in the private `pitches` bucket. The captions are made from the transcript |
| `/dashboard/evidence` | Adds evidence with up to three files or a link, and sees each item's status and the reviewer's note or reason |
| `/activity` | Reads the activity feed: every published venture's steps of progress, newest first, with new entries added while the page is open. A founder cannot open another founder's profile from it. `/dashboard/updates`, where founders used to post updates, now leads here |
| `/dashboard/introductions` | Accepts or declines investors' requests. Accepting opens a conversation |
| `/dashboard/preview` | Sees the profile exactly as approved investors see it |

A profile is hidden until the founder publishes it, and it cannot be published without a pitch.

**Investors** (`/investor`)

| Address | What the investor does |
|---|---|
| `/onboarding/investor` | Gives their name, investor type, fund or firm, sectors, stages, countries and cheque size. The account then waits at `/investor/pending` |
| `/investor` | Searches published founders by sector, stage, geography, evidence and recent activity. Each result shows the ask, how many of the last 13 weeks hold an entry in the activity feed and the readiness check, and pointing at a pitch plays a muted preview of five seconds with captions. Results are sorted by company name, never by a score |
| `/investor/ventures/<id>` | Watches the pitch with captions, reads the transcript, the ask, the readiness check with the evidence in each area and its status, Momentum and the venture's own activity, and asks for an introduction with a short note |
| `/activity` | Reads the activity feed, and opens any venture in it |
| `/investor/introductions` | Follows their requests, and withdraws one the founder has not answered |
| `/investor/profile` | Changes their details |

The readiness check is the same on the website and in the app. An area is strong when it holds platform-reviewed or third-party evidence, building when it holds founder-submitted evidence only, and a gap when it holds none. The founder's next three steps come from the score engine's next best actions, leaving out evidence already waiting for a reviewer. Momentum shows how long ago the profile changed, the progress updates in the last 90 days, the evidence added in the last 90 days, and a strip of the last 13 weeks that marks each week with an update. It has no streaks, points or ranks.

An investor sees three statuses for evidence and nothing else about it: "Founder submitted" until a reviewer decides, then "Platform reviewed" or "Third-party evidence available". Rejected, expired and "needs more" evidence, the files, the reviewer's identity and the founder's score are never shown to an investor. `venture_evidence()` and `discover_ventures()` in the migration decide this.

**Both sides** (`/introductions/<id>`): the conversation an accepted request opens. Only the founder and the investor can read it. Each side can report the conversation from its menu with a reason, and the report reaches the IkonetU team on Reports and Evidence with the conversation's reference.

**Staff** (`/admin`)

The admin pages follow the admin design the owner approved on 26 October 2026: a navy sidebar beside every page, which a phone opens behind a Menu button. Each list keeps its filters in the page's address, so a filtered list can be bookmarked and exported as it stands.

| Address | Who | What |
|---|---|---|
| `/admin/signin` | Admins | The admin sign-in, a page of its own with an email address and a password. Any other account is signed out again and told only that the details do not match an admin account. Ten tries in 15 minutes from one address and five for one email address, then a wait. A signed-out visit to any `/admin` page comes here, and signing out of the admin pages returns here |
| `/admin` | Admins | The dashboard: the form responses, the founders and investors on the registers, the pitch videos, the introductions, the messages and the staff; founders and investors by month; what waits for an admin; the latest records; founders by country and the support they asked for; and the newest entries of the audit log. A reviewer who opens it goes to Reports and Evidence |
| `/admin/founders` | Admins | The founder register: one record for each founder who answered the form, with search, filters for country, month joined, support and pitch video, an order, pages of 25 and a CSV. The Accounts tab lists the founders who have an IkonetU account and their ventures, which is all a reviewer sees here. The Sign-ups not finished tab lists accounts that never chose founder or investor, and removes one |
| `/admin/founders/<record>` | Admins | One founder's record, such as `p001`: every response they sent, with the name, phone and university each one gave, their details, their introductions and their pitch video. Delete permanently waits until DELETE is typed |
| `/admin/founders/<venture id>` | Reviewers and admins | Everything one venture in the app holds: who can see it, every piece of evidence in every status, the pitch, the ask, the score, its activity and introductions by status. An admin hides the profile from investors here with a reason the founder reads, or lifts the hold |
| `/admin/investors` | Admins | The investor register with its monthly progression, search, filters for month and account, adding entries by pasting a list, linking an entry to an investor's account or unlinking it, and a CSV. The Accounts tab lists the investor accounts, and Awaiting approval holds the ones to approve or decline |
| `/admin/introductions` | Admins | The introductions made from the registers, with a card for each status, search, a status filter, an order and a CSV. `/admin/introductions/<id>` shows the investor and the founder, changes the status and shows its history |
| `/admin/videos` | Admins | The pitch video files in Google Drive by status. A video is approved once all four checks are ticked (the problem, the solution, the market and the ask), or rejected with one of six reasons, and can return to pending review. A video linked to a founder record is titled with the record's startup and opens the record |
| `/admin/content` | Reviewers and admins | Reports and Evidence. The Reports tab holds the open reports about conversations, each resolved with a note of what was done. The Evidence tab holds the evidence waiting for review and the scores to update |
| `/admin/evidence/<id>` | Reviewers and admins | Review evidence, open its files through links that last five minutes, and approve it with a note of what was compared, ask for more, or reject it. An approval recomputes the founder's score with the score engine |
| `/admin/analytics` | Admins | The registers counted for this year, the last 90 days or the last 30: totals, founders and investors by month or by week, the way from the register to an introduction, founders by country, the support they asked for, their universities and the founders with introductions, with a CSV of the bars. The sample rows are not counted |
| `/admin/database` | Admins | Every table in `public` with what it holds, its exact row count, its row security and its columns, the stored files by bucket and the migrations Supabase recorded. Values are never read, only counted, and the text of messages is never shown |
| `/admin/settings` | Admins | The pitch rules (file types, largest file and longest pitch), the introduction rules (on or off, and the daily limit), the platform's mode and its maintenance message, the admin's own account and password, and the staff list, where an admin adds a reviewer or an admin by the email of an existing account or removes one |
| `/admin/audit` | Admins | The audit log: every response to the founder form, every entry added to the investor register and every staff action, newest first, with a card for each kind, search, dates, an order and a CSV |
| `/admin/people` | Admins | Every account with its email address and last sign-in, with search and filters for role and status. Reached from Settings and from the investor accounts |
| `/admin/people/<id>` | Admins | Change a person's role, suspend the account with a reason or make it active again, and see that account's entries in the audit log |

The register's records, its introductions and the pitch video files are held in the tables of migration `20261027000002_admin_records.sql`. Its rows come from the admin design the owner approved and are loaded by a script kept out of the repository, because they hold founders' personal data. The same script loads the 60 founders of the June list, whose registration date is the list's date. The design's four other founders, its other investor and their four introductions are loaded as ordinary records, as the owner ruled on 27 October 2026, so no page labels them and every count includes them. `supabase/scripts/approve_and_link_videos.sql` approves the 92 pitch videos, links them to the first 92 founder records with a startup name and gives each approval its founder's registration date, after the records are loaded.

Nobody can make themselves staff. An admin who signs in with a password is made in two steps. First the owner adds the user in the Supabase dashboard with the email address and a password of their choosing, so no password passes through anyone else. Then this SQL, run as the database owner, gives that user an admin profile: `insert into public.profiles (user_id, full_name, role, status, confirmed_adult) select id, '<name>', 'admin', 'active', true from auth.users where lower(email) = '<their email>';`. A person who already has a profile is made an admin in one transaction that names the service role, because the profile guard refuses a change of role from the database owner otherwise: `begin; select set_config('request.jwt.claims', '{"role": "service_role"}', true); update public.profiles set role = 'admin', status = 'active' where user_id = (select id from auth.users where email = '<their email>'); commit;`. The update this paragraph gave before 24 October 2026 failed with "role and status can only be changed by an admin", found that day by running it on a local copy. After that, an admin makes reviewers and other admins on Settings, or at `/admin/people`. Nobody can change their own role or status, so a second admin is needed to change the first.

What the admin changes do (migration `20261017000001_admin.sql`):

- **Hiding a profile.** The profile leaves investors' view at once, the founder reads the reason on their dashboard, and the founder cannot publish it again until an admin lifts the hold. Lifting the hold does not publish it; the founder does.
- **Suspending an account.** A suspended founder lands on `/suspended`, their profile leaves investors' view, and the database refuses their writes, their answers to introductions and their messages. Making the account active again does not publish the profile. A suspended investor sees the page that says their account is not approved.
- **Changing a role.** A person becomes a founder only if they have a venture, and an investor only if they have investor details. A founder made a reviewer or an admin leaves investors' view, so staff have no profile in discovery. The mentor role cannot be given, because mentors have no pages yet.
- Every change goes to the audit log with the admin who made it. No email is sent, because IkonetU has no email sender yet.

## Sign-in

"Get started" leads to `/signin`. A founder enters an email, confirms they are 18 or older, and Supabase Auth sends a 6-digit code (PRD A-2, SRD SEC-A1, SEC-A9). The code is entered at `/signin/code`, which turns it into a session cookie. Between the two steps the address is kept in an HTTP-only cookie, never in the URL. The first code creates the account, so sign-up and sign-in are one step.

Phone sign-in by WhatsApp or SMS (PRD A-1) is built and switched off. It needs an SMS and WhatsApp provider configured in Supabase Auth, and then `NEXT_PUBLIC_PHONE_SIGN_IN=on` on Render. With it on, the phone number is asked first and email becomes the fallback, as the sign-in wireframe shows.

Sign-in with Google is built and switched off, as the owner chose on 26 October 2026, after trouble with the email sender. With `GOOGLE_SIGN_IN=on`, Continue with Google stands above the email form. `/signin/google` sends the browser to Supabase's `/auth/v1/authorize` with a PKCE challenge, and Supabase returns it to `/auth/callback` with a one-time code, which becomes a session as the email link does. No email is sent. A first Google sign-in makes the account, and onboarding then asks for the age confirmation that the email form asks for. If the sign-in does not finish, the sign-in page says that signing in with Google did not finish. The email code stays beneath the button for anyone without a Google account. The app's half was run in a browser against the local stand-in, which skips Google's own screens. The real Google screens and Supabase's Google provider have not been run (**unverified**).

To switch it on, in this order. Supabase's guide "Sign in with Google" is the source of steps 1 and 2, and Google's OAuth verification guide of step 3.

1. In the Google Auth Platform console, under Clients, create a client of the type "Web application". Under Authorized JavaScript origins add the public address, `https://ikonetu.com`. Under Authorized redirect URIs add the callback address that Supabase shows on its Google provider page. Keep the client ID and the client secret.
2. In Supabase, on the Google provider page of the dashboard, switch Google on and enter the client ID and the client secret there. The secret goes into the dashboard only, never into a conversation or this repository.
3. On the Audience page of the Google Auth Platform console, set the publishing status to "In production". Google's guides describe the "Testing" status of an app for outside users as limited to the test users listed there.
4. On Render, set `GOOGLE_SIGN_IN` to `on` and restart the service.
5. Sign in once with a real Google account and check that the founder or investor choice appears.

The privacy policy does not yet name Google as a way to sign in, and the legal pack is for the solicitor to review, so its wording is the owner's to approve before the button goes live.

`/onboarding` creates the profile, records the consents (PRD A-4) and creates the first venture, and `/dashboard` shows them. Every query runs as the signed-in founder, so the row level security in `supabase/migrations` decides what each one can read and write. Each signed-in page sends anyone without a session to `/signin`. `/auth/callback` turns the link in Supabase's default email into a session. Supabase's built-in email sender does not let the templates be edited, so until IkonetU has its own email sender the email carries a link rather than the code, and the code screen tells the founder to open it on the same device. The link only works in the browser that asked for it, because the sign-in is bound to a cookie set there.

Supabase Auth needs these settings before sign-in works:

1. Under URL Configuration, the Site URL set to `NEXT_PUBLIC_SITE_URL`, and `<NEXT_PUBLIC_SITE_URL>/auth/callback` under Redirect URLs.
2. Once IkonetU has its own email sender under SMTP Settings, the "Magic Link" and "Confirm signup" email templates should show the code with `{{ .Token }}`. Until then the default email's link is used.
   The owner switched the sender from SendGrid to Brevo on 26 October 2026, in the Supabase dashboard. SendGrid retired its free plans in May 2025. Brevo's free plan allows 300 emails a day and includes its SMTP relay. Read back the same day: `smtp_host` is `smtp-relay.brevo.com`, `smtp_port` is `587`, the SMTP login matches the Brevo login, and both email templates show the code with `{{ .Token }}`. ikonetu.com carries Brevo's verification code, both Brevo DKIM records and a DMARC record. Whether the stored password is the right Brevo SMTP key is **unverified** until a sign-in email arrives.
3. The email code lasting 300 seconds and 6 digits long (SRD SEC-A1).
4. The access token lasting 900 seconds, with refresh token rotation and reuse detection on (SRD SEC-A3).

`docs/DECISIONS.md` lists where this build departs from the PRD, TRD and SRD, and why. `docs/HOSTING.md` describes the Render service, its environment variables and the Supabase settings the public address needs. `docs/OPERATIONS.md` says how to tell that something is wrong, what to do first, how backups are to be checked, and how to turn on Sentry.

## Run it

The app was built and tested with Python 3.13.16.

```sh
cd service
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # 213 tests, 49 of them in the score engine
.venv/bin/uvicorn app.main:app --port 3000    # http://localhost:3000
```

Sign-in answers "not open yet", and the waitlist endpoint answers 503, until Supabase is configured. To connect it, copy `.env.example` to `service/.env`, fill in the values from your Supabase project, and load it before starting the app, as `service/README.md` shows. The service role key must stay on the server and must never be committed.

## Rules the code enforces

- A score only counts approved evidence and the founder's own statements for the three self-declared signals, which count at 60% of their points. The rules are rubric v3, from the Scoring System Specification of March 2026.
- Founders cannot approve their own evidence, change its status or give themselves staff roles. The database blocks these even if the app has a bug.
- Score history and the audit log cannot be edited after they are written.
- The waitlist and the investor interest list cannot be read or written by any signed-in user or visitor. Only the server writes to the waitlist, and nothing writes to the interest list since its form was retired.
- The pitch rules, the introduction rules and the platform's mode are held by the database as well as the app. A pitch that breaks the pitch rules, a request over the daily limit or while requests are switched off, and a setting out of its range are refused there even if a page has a bug. In maintenance mode founders and investors see the maintenance message, and a new sign-in by anyone but staff is signed out again at once. The app reads the settings through `platform_status()` and keeps them for 15 seconds (`service/app/platform.py`).
- The rubric in the database is generated from `service/app/score_engine/rubric.py`. After changing the rubric, run `.venv/bin/python -m app.score_engine.rubric_sql` from `service`. A test fails if the two copies differ.

## How failures are handled

- Every call from the server to Supabase gives up after 15 seconds, or 120 seconds for a file upload (`service/app/supabase.py`).
- Evidence and its file records are saved in one transaction. If saving fails, the files just uploaded are removed.
- Evidence and messages carry a request key made when the form is shown, so a form sent twice is saved once.
- After a decision, the founder's score is recorded with up to three attempts. A score that still fails appears under "Scores to update" on the Evidence tab of `/admin/content`, with a button to recompute it.
- The daily limit on introduction requests takes a lock per investor, so simultaneous requests cannot pass it.
- Each failure is written as one line of JSON (`service/app/log.py`) and, once `SENTRY_DSN` is set, sent to Sentry without cookies, headers, form text or the person's details.

The browser checks of these fixes ran against the local stand-in described below and are not in this repository.

## Not done yet

- Sign-in has not been run end to end with a real email code, because no test inbox was available. The database writes it makes were run under row level security on a local copy of the migrations.
- The in-memory rate limit on the waitlist endpoint only slows casual abuse. Production also needs a limit in front of the app (SRD SEC-W4).
- The About page still shows placeholders for the founders' names, roles and photos, and the privacy policy still shows placeholders for the ICO registration number and the video, analytics and email providers.
- IkonetU sends no email yet, so a founder learns of a new request and an investor of an answer only by signing in. For the same reason the people on the investor interest list have not been told that investor accounts are open. The investor sign-up records whether the person agrees to email for when a sender is set up.
- Messages appear when the conversation page reloads. Nothing pushes them to an open page.
- The captions are timed by the length of each sentence of the founder's transcript, not by listening to the video, so they can run a little ahead or behind.
- The pitch's length is read in the founder's browser before upload. A browser that cannot decode the video cannot upload it, and the page says so.
- The founder and investor journeys were run in a browser against a local stand-in for Supabase (Postgres 16 with these migrations, PostgREST, and a small stand-in for Supabase Auth and Storage), not against a real Supabase project. That stand-in is not in this repository. The first run against the real project is still to come.
- The admin pages read email addresses and last sign-in times from Supabase Auth's `auth.users` through `admin_accounts()`. The stand-in's copy of that table has the same column names, but the real project has not been read, so those two columns are **unverified** until the first run there.
- The admin lists show 25 rows a page and the investor register 15, as the boards did, and the founders, investors, introductions, analytics and audit log export as CSV. Investors read up to 1,000 register entries and the audit log the newest 1,000 staff actions. People and roles still lists fifty a page and exports nothing. The waitlist and the retired investor interest list are counted, and no page lists their rows.
- The admin Introductions page lists the introductions made from the registers. The introductions investors request in the app are on each venture's page, and production held none on 27 October 2026.
- Matching, which the owner asked for on 27 October 2026, is drawn as a design for approval and not built. Its tables wait for that approval too.
- The Database page names its tables in IBM Plex Mono, which the app does not load, so a browser shows its own monospace face.
