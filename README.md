# IkonetU platform

This repository holds the new IkonetU codebase: the web app, the score engine and the database setup. It follows the PRD, TRD and SRD written in October 2026.

## What is in it

| Folder | Contents |
|---|---|
| `apps/web` | Next.js app with the public website, sign-in, the founder and investor sides, the staff pages, `GET /api/health` for an uptime monitor, and `POST /api/v1/waitlist`, which no page calls since sign-up replaced the form |
| `packages/score-engine` | The IkonetU Score rules (rubric v2), the score calculation, league placement and the "next best actions" list, with tests |
| `packages/ui-tokens` | Brand colours, fonts, spacing and the 44 px touch target |
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
| `/how-it-works` | How it works |
| `/readiness-check` | Readiness self-check. The answers stay in the browser and are never sent |
| `/trust-and-safety` | Trust and safety |
| `/about` | About |
| `/questions` | Questions |
| `/privacy` | Privacy policy |
| `/terms` | Terms |
| `/cookies` | Cookie policy |

The investor interest form was retired on 15 October 2026, when investor accounts opened. Every investor button on the website now leads to account sign-up, and the old address `/investor-interest` redirects to `/for-investors`. The `investor_interest` table keeps the rows it already holds.

The seven product pictures on the website were captured from this app on 15 October 2026, signed in against a local test copy of the database loaded with the website's six sample founders. Each picture carries a "Sample data" label.

IkonetU Technology Limited adopted the privacy policy, the terms and the cookie policy on 15 October 2026. Each page's title and description are in `apps/web/lib/pages.ts`, which the site map also reads. `/robots.txt` keeps the API, sign-in and the signed-in pages out of search engines.

The page markup lives in `apps/web/components/site/views` and the styles in `apps/web/app/site.css`. The behaviour of each page, such as the menu, the pitch player, the walkthrough video and the readiness self-check, is in `apps/web/components/site`. The signed-in pages use the same shared styles, with their own additions in `apps/web/components/app/app.css`.

The fonts are downloaded when the app is built and served by the app, so no visitor's browser asks Google for them.

## The signed-in app

After sign-in, a new person chooses at `/onboarding` whether they are a founder or an investor. `apps/web/lib/session.ts` sends each person to their own pages, so a founder cannot open the investor pages and nobody but staff can open the staff pages. The database enforces the same separation through row level security, so a bug in a page cannot widen what a person sees.

**Founders** (`/dashboard`)

| Address | What the founder does |
|---|---|
| `/dashboard` | Publishes or hides the profile, sees the readiness check and the next three steps, edits the venture's details and its ask, and sees their own score |
| `/dashboard/pitch` | Uploads a pitch of up to 90 seconds and 50 MB, with a typed transcript. The video goes from the browser straight to the founder's folder in the private `pitches` bucket. The captions are made from the transcript |
| `/dashboard/evidence` | Adds evidence with up to three files or a link, and sees each item's status and the reviewer's note or reason |
| `/dashboard/updates` | Posts and removes progress updates |
| `/dashboard/introductions` | Accepts or declines investors' requests. Accepting opens a conversation |
| `/dashboard/preview` | Sees the profile exactly as approved investors see it |

A profile is hidden until the founder publishes it, and it cannot be published without a pitch.

**Investors** (`/investor`)

| Address | What the investor does |
|---|---|
| `/onboarding/investor` | Gives their name, investor type, fund or firm, sectors, stages, countries and cheque size. The account then waits at `/investor/pending` |
| `/investor` | Searches published founders by sector, stage, geography, evidence and recent activity. Each result shows the ask, the updates in the last 90 days and the readiness check, and pointing at a pitch plays a muted preview of five seconds with captions. Results are sorted by company name, never by a score |
| `/investor/ventures/<id>` | Watches the pitch with captions, reads the transcript, the ask, the readiness check with the evidence in each area and its status, Momentum and the progress updates, and asks for an introduction with a short note |
| `/investor/introductions` | Follows their requests, and withdraws one the founder has not answered |
| `/investor/profile` | Changes their details |

The readiness check is the same on the website and in the app. An area is strong when it holds platform-reviewed or third-party evidence, building when it holds founder-submitted evidence only, and a gap when it holds none. The founder's next three steps come from the score engine's next best actions, leaving out evidence already waiting for a reviewer. Momentum shows how long ago the profile changed, the progress updates in the last 90 days, the evidence added in the last 90 days, and a strip of the last 13 weeks that marks each week with an update. It has no streaks, points or ranks.

An investor sees three statuses for evidence and nothing else about it: "Founder submitted" until a reviewer decides, then "Platform reviewed" or "Third-party evidence available". Rejected, expired and "needs more" evidence, the files, the reviewer's identity and the founder's score are never shown to an investor. `venture_evidence()` and `discover_ventures()` in the migration decide this.

**Both sides** (`/introductions/<id>`): the conversation an accepted request opens. Only the founder and the investor can read it.

**Staff** (`/admin`)

| Address | Who | What |
|---|---|---|
| `/admin` | Reviewers and admins | The overview: evidence waiting and the age of the oldest, investors waiting for approval, scores to update, the north star for the last 30 days and the last six months, introductions by status, and the counts of founders, ventures, investors, staff, suspended accounts and waiting lists |
| `/admin/founders` | Reviewers and admins | Every venture and its founder, published or not, with search and a filter for published, unpublished and hidden profiles |
| `/admin/founders/<id>` | Reviewers and admins | Everything one venture holds: who can see it, every piece of evidence in every status, the pitch, the ask, the score, recent updates and introductions by status. An admin hides the profile from investors here with a reason the founder reads, or lifts the hold |
| `/admin/evidence` | Reviewers and admins | Review evidence, open its files through links that last five minutes, and approve it with a note of what was compared, ask for more, or reject it. An approval recomputes the founder's score with the score engine |
| `/admin/investors` | Admins | Approve, decline or suspend investor accounts |
| `/admin/people` | Admins | Every account with its email address and last sign-in, with search and filters for role and status |
| `/admin/people/<id>` | Admins | Change a person's role, suspend the account with a reason or make it active again, and see that account's entries in the audit log |
| `/admin/audit` | Admins | Every staff decision, newest first, with who made it, what changed and the reason |

Nobody can make themselves staff. The first admin is set with SQL run as the database owner, after that person has signed in once and created a profile: `update public.profiles set role = 'admin', status = 'active' where user_id = (select id from auth.users where email = '<their email>');`. After that, an admin makes reviewers and other admins at `/admin/people`. Nobody can change their own role or status, so a second admin is needed to change the first.

What the admin changes do (migration `20261017000001_admin.sql`):

- **Hiding a profile.** The profile leaves investors' view at once, the founder reads the reason on their dashboard, and the founder cannot publish it again until an admin lifts the hold. Lifting the hold does not publish it; the founder does.
- **Suspending an account.** A suspended founder lands on `/suspended`, their profile leaves investors' view, and the database refuses their writes, their answers to introductions and their messages. Making the account active again does not publish the profile. A suspended investor sees the page that says their account is not approved.
- **Changing a role.** A person becomes a founder only if they have a venture, and an investor only if they have investor details. A founder made a reviewer or an admin leaves investors' view, so staff have no profile in discovery. The mentor role cannot be given, because mentors have no pages yet.
- Every change goes to the audit log with the admin who made it. No email is sent, because IkonetU has no email sender yet.

## Sign-in

"Get started" leads to `/signin`. A founder enters an email, confirms they are 18 or older, and Supabase Auth sends a 6-digit code (PRD A-2, SRD SEC-A1, SEC-A9). The code is entered at `/signin/code`, which turns it into a session cookie. Between the two steps the address is kept in an HTTP-only cookie, never in the URL. The first code creates the account, so sign-up and sign-in are one step.

Phone sign-in by WhatsApp or SMS (PRD A-1) is built and switched off. It needs an SMS and WhatsApp provider configured in Supabase Auth, and then `NEXT_PUBLIC_PHONE_SIGN_IN=on` on Render. With it on, the phone number is asked first and email becomes the fallback, as the sign-in wireframe shows.

`/onboarding` creates the profile, records the consents (PRD A-4) and creates the first venture, and `/dashboard` shows them with the score. Every query runs as the signed-in founder, so the row level security in `supabase/migrations` decides what each one can read and write. `middleware.ts` sends anyone without a session from `/dashboard` and `/onboarding` to `/signin`. `/auth/callback` turns the link in Supabase's default email into a session. Supabase's built-in email sender does not let the templates be edited, so until IkonetU has its own email sender the email carries a link rather than the code, and the code screen tells the founder to open it on the same device. The link only works in the browser that asked for it, because the sign-in is bound to a cookie set there.

Supabase Auth needs these settings before sign-in works:

1. Under URL Configuration, the Site URL set to `NEXT_PUBLIC_SITE_URL`, and `<NEXT_PUBLIC_SITE_URL>/auth/callback` under Redirect URLs.
2. Once IkonetU has its own email sender under SMTP Settings, the "Magic Link" and "Confirm signup" email templates should show the code with `{{ .Token }}`. Until then the default email's link is used.
3. The email code lasting 300 seconds and 6 digits long (SRD SEC-A1).
4. The access token lasting 900 seconds, with refresh token rotation and reuse detection on (SRD SEC-A3).

`docs/DECISIONS.md` lists where this build departs from the PRD, TRD and SRD, and why. `docs/HOSTING.md` describes the Render service, its environment variables and the Supabase settings the public address needs. `docs/OPERATIONS.md` says how to tell that something is wrong, what to do first, how backups are to be checked, and how to turn on Sentry.

## Run it

You need Node 22 and pnpm 10.

```sh
pnpm install
pnpm test          # 147 tests: 47 in the score engine and 100 in the web app
pnpm typecheck
pnpm --filter @ikonetu/web dev    # http://localhost:3000
```

Sign-in answers "not open yet", and the waitlist endpoint answers 503, until Supabase is configured. To connect it, copy `.env.example` to `apps/web/.env.local` and fill in the values from your Supabase project. The service role key must stay on the server and must never be committed.

## Rules the code enforces

- A score only counts approved evidence. Self-reported claims add nothing.
- Founders cannot approve their own evidence, change its status or give themselves staff roles. The database blocks these even if the app has a bug.
- Score history and the audit log cannot be edited after they are written.
- The waitlist and the investor interest list cannot be read or written by any signed-in user or visitor. Only the server writes to the waitlist, and nothing writes to the interest list since its form was retired.
- The rubric in the database is generated from `packages/score-engine/src/rubric.ts`. After changing the rubric, run `pnpm --filter @ikonetu/score-engine rubric:sql`. A test fails if the two copies differ.

## How failures are handled

- Every call from the server to Supabase gives up after 15 seconds, or 120 seconds for a file upload (`apps/web/lib/timed-fetch.ts`).
- Evidence and its file records are saved in one transaction. If saving fails, the files just uploaded are removed.
- Evidence, progress updates and messages carry a request key made when the form is shown, so a form sent twice is saved once.
- After a decision, the founder's score is recorded with up to three attempts. A score that still fails appears under "Scores to update" on `/admin/evidence`, with a button to recompute it, and is counted on the overview at `/admin`.
- The daily limit on introduction requests takes a lock per investor, so simultaneous requests cannot pass it.
- Each failure is written as one line of JSON (`apps/web/lib/log.ts`) and, once `SENTRY_DSN` is set, sent to Sentry without cookies, headers, form text or the person's details.

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
- The admin pages list fifty rows a page. A long list of founders, people or audit entries is read page by page, and nothing exports it yet. The waitlist and the retired investor interest list are counted on the overview, and no page lists their rows.
