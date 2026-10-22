# IkonetU Technical Requirements Document (reconstructed)

## About this document

This document was reconstructed on 19 October 2026 at the owner's request. It is not the TRD of 5 October 2026. That original could not be found in the repository or anywhere this session can reach, so this document was written from the code on `main` at commit `3473aca`, from `docs/DECISIONS.md`, from `README.md`, `docs/HOSTING.md` and `docs/OPERATIONS.md`, and from the eight migrations in `supabase/migrations`.

It describes the system as built. A reference such as **TRD rule 4** appears only where the code cites it, and the original wording behind it is unknown. **Unverified** marks anything not checked against the live service. File paths are relative to `service/app/` unless they start with `supabase/` or name a file at the root.

The companion documents are `docs/PRD-reconstructed.md` and `docs/SRD-reconstructed.md`.

## 1. What is known of the original TRD

| Topic | What the repository records | Where |
|---|---|---|
| Data model | The core schema calls itself "IkonetU core schema, release 1 and 2 (TRD Data model)". | `supabase/migrations/20261005000001_core.sql:1` |
| API surface | The apps call one API at `/api/v1`. The API surface lists `PATCH /me`, `POST /me/consents` and `POST /ventures`. | `docs/DECISIONS.md` |
| Writes through the API | Only writes that change a score, Momentum or a status must go through the API. | `docs/DECISIONS.md` |
| Sign-in | Phone first, with a code by SMS or WhatsApp. | `docs/DECISIONS.md` |
| Score engine rule 2 | Each piece of evidence carries the lane by which it was verified. | `score_engine/rubric.py:16` |
| Lane weights | The code says its lane weights come from the TRD. | `score_engine/rubric.py:60` |
| Rubric v2 | The code calls rubric v2 "the proposed defaults from the TRD of 5 October 2026". | `score_engine/rubric.py:89` |
| Score order | The code says the rules follow the TRD: lane weight, then the signal cap, then the category cap, then the cap of 600. | `score_engine/engine.py:172` |
| Rule 4 | Revenue in a local currency converts to US dollars with one stated rate. | `score_engine/engine.py:226` |

Two entries in `docs/DECISIONS.md` say the TRD is to be updated: one for hosting on Render, and one for writing the web app in Python. The original's wording on both was never checked, because the TRD was not in the repository.

## 2. Architecture

The system has three parts.

1. **One web service.** A Python app with FastAPI and Jinja2 serves the public website, sign-in, the founder, investor and staff pages, `GET /api/health` and `POST /api/v1/waitlist`. It runs on Render in Frankfurt.
2. **Supabase.** Supabase provides Auth (email sign-in with PKCE), the Postgres database through PostgREST, Storage for pitches and evidence files, and row level security on every table that holds user data.
3. **The browser.** Pages are rendered on the server. The browser runs small scripts from `/static`, and it uploads pitch videos straight to Supabase Storage with the user's own token.

Almost every read and write runs as the signed-in user, so row level security decides what each request may touch. The service role key is used for one thing only: the waitlist insert.

### 2.1 Departures

| Departure | Recorded in `docs/DECISIONS.md` |
|---|---|
| The web app writes the profile, consents and first venture from its own form handlers as the signed-in user, and `/api/v1` holds only the waitlist. | This was judged acceptable under the TRD's rule on writes. The `/api/v1` endpoints are needed before the mobile app. |
| The app runs on Render rather than Vercel. | The owner decided on 15 October 2026. |
| The app is written in Python. The Next.js app, the TypeScript packages and the Node workspace were removed. | The owner decided on 17 October 2026. `service/README.md` records how each part was checked against the Next.js app. |

## 3. Stack

| Part | Version or setting |
|---|---|
| Python | `requires-python >= 3.12`. Render sets 3.13.16, and CI uses 3.13. |
| FastAPI | 0.143.3 |
| Starlette | 1.8.0 |
| Jinja2 | 3.1.6 |
| httpx | 0.28.1 |
| uvicorn | 0.54.0 |
| pydantic | 2.14.1 |
| python-multipart | 0.0.32 |
| ada-url | 4.0.0, for address parsing |
| sentry-sdk | 2.72.0 |
| pytest | 9.1.1, development only |

`service/requirements.txt` pins every runtime package exactly, with everything they pull in. `requirements-dev.txt` pins only pytest, and its own dependencies are unpinned.

## 4. Configuration

The app reads every variable once at start (`config.py`), so a change needs a restart and not a rebuild.

| Variable | Default | Effect |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | None | The base for Auth, REST and Storage. Its origin goes into the CSP's `media-src` and `connect-src`. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | None | It is sent as the `apikey` on every call. Without the URL and this key, sign-in says "Sign-up is not open yet", and health and the waitlist answer 503. |
| `SUPABASE_SERVICE_ROLE_KEY` | None | It is used only for the waitlist insert. Without it the waitlist answers 503. |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3000` | It sets the email link's return address, the canonical tags, robots.txt and the sitemap. Cookies get `Secure` only when it starts with `https://`. |
| `NEXT_PUBLIC_PHONE_SIGN_IN` | Off | Phone sign-in turns on only when the value is exactly `on`. |
| `TRUSTED_PROXY_HOPS` | 1 | It sets which `X-Forwarded-For` entry, counted from the end, is the caller. |
| `CLIENT_IP_HEADER` | None | When set, this one header names the caller instead. |
| `SENTRY_DSN` | None | Sentry starts only when it is set. |
| `SENTRY_ENVIRONMENT` | `production` | It names Sentry's environment. |
| `APP_ENV` | `production` | It sets `settings.production`, which nothing reads. |
| `PORT` | Set by the host | The start command passes it to uvicorn. |

The `NEXT_PUBLIC_` names were kept from the Next.js app so that the variables already on Render still work.

## 5. Application structure

### 5.1 Startup

On start the app initialises Sentry when a DSN is set and creates one shared `httpx.AsyncClient`. The OpenAPI, docs and ReDoc routes are switched off.

### 5.2 Middleware, outermost first

1. Starlette's `ServerErrorMiddleware`, which holds the app's handler for unhandled exceptions.
2. FastAPI's exception telemetry middleware, which observes and re-raises.
3. `SecurityMiddleware` (`security.py`), which adds the security headers and checks the Origin of form posts.
4. `session_cookies` (`main.py`), which writes refreshed session cookies.
5. Starlette's `ExceptionMiddleware`, which holds the handlers for HTTP errors and redirects.
6. The router.

### 5.3 Errors and redirects

A guard redirect answers 303 to a POST and 307 to a GET. A 404 renders `not_found.html` with `noindex`. An unhandled exception is logged as `request.failed`, sent to Sentry, and rendered as `error.html` with status 500.

### 5.4 Routers

The routers are included in this order: system, auth, site, founder, investor, introductions, staff. The site router registers the eleven public pages from `pages.py`. `/static`, `/media` and `/icon.svg` are served by the app.

### 5.5 Templates

Jinja2 autoescapes every template, and no template uses `|safe`. No template has an inline script or an inline event handler. Templates hold 129 inline `style` attributes, which is why the CSP allows inline styles. Every rendered page is sent with `Cache-Control: private, no-cache, no-store, max-age=0, must-revalidate`.

### 5.6 Forms

A form that saves answers 303 back to its page with a one-time confirmation in a short-lived cookie. Lengths are counted in UTF-16 units after trimming, the way the browser counts them (`validate.py`).

## 6. Calls to Supabase

### 6.1 Who calls

| Caller | Credentials | Used for |
|---|---|---|
| The signed-in user | `apikey` plus the user's access token | Every signed-in read and write, under row level security |
| A visitor | `apikey` used as the bearer as well | The health call only |
| The service role | The service role key | The waitlist insert only |
| The browser | The user's access token | Uploading the pitch straight to Storage |

### 6.2 Auth calls

| Call | Purpose |
|---|---|
| `POST /auth/v1/otp` | Sends the email with a PKCE challenge and `create_user: true` |
| `POST /auth/v1/verify` | Checks a typed code |
| `POST /auth/v1/token?grant_type=pkce` | Exchanges the email link's code |
| `POST /auth/v1/token?grant_type=refresh_token` | Refreshes the session |
| `GET /auth/v1/user` | Reads the viewer, once per request |
| `POST /auth/v1/logout?scope=global` | Signs out everywhere |

### 6.3 Database calls

Reads and writes go to `/rest/v1/<table>` with filters, ordering, limits and `Prefer` headers. The app calls these database functions:

| Function | Caller |
|---|---|
| `health` | `GET /api/health` |
| `venture_evidence` | The founder's dashboard and every founder profile |
| `discover_ventures` | Investor discovery |
| `submit_evidence` | The evidence form |
| `record_score` | After each evidence decision and on a manual recompute |
| `decide_evidence`, `decide_investor` | Staff decisions |
| `admin_overview`, `admin_ventures`, `admin_accounts`, `ventures_with_stale_scores` | Staff pages |
| `admin_hide_venture`, `admin_lift_hold`, `admin_set_role`, `admin_set_status` | Admin actions |

### 6.4 Storage calls

Uploads send the raw body with `x-upsert: false`. Pitch links are signed for 3,600 seconds and evidence links for 300 seconds. A removal is a DELETE with the object's path.

### 6.5 Timeouts, retries and request keys

| Mechanism | As built |
|---|---|
| Timeouts | 15 seconds per call, 120 seconds for an upload, and 5 seconds for the health call. A network error becomes an `ApiError` with code `network`. |
| Retries | No call is retried at the HTTP level. `with_retry` makes three attempts, 0.25 seconds and then 0.5 seconds apart, and only score recording uses it. |
| Request keys | Each form render carries a fresh UUID. Evidence, progress updates and messages store it, and a unique index keeps a second copy out. The app treats Postgres error 23505 on the key as "already saved". |
| Compensation | If saving evidence fails after its files are uploaded, the app removes the files. |

## 7. Data model

The database is Postgres on Supabase. The schema is in eight migrations, applied in filename order.

| Migration | What it adds |
|---|---|
| `20261005000001_core.sql` | Enums, profiles, consents, ventures, the rubric tables, evidence, evidence files, verification checks, reviews, scores, score events, the audit log, the waitlist, the private `evidence` bucket and the first policies |
| `20261005000002_rubric_v2.sql` | The rubric v2 seed, generated from `score_engine/rubric.py` |
| `20261005000003_lock_public_profiles.sql` | Closes three gaps Supabase's security advisor found on 5 October 2026 |
| `20261015000001_investor_interest.sql` | The `investor_interest` table, now written by nothing |
| `20261015000002_investor_side.sql` | Investor profiles, pitches, updates, introductions, messages, the private `pitches` bucket, publishing and the investor functions |
| `20261015000003_venture_ask.sql` | The venture's ask, returned by discovery |
| `20261015000004_resilience.sql` | Request keys, atomic evidence, the lock on the daily limit, `health()` and the stale score list |
| `20261017000001_admin.sql` | The hold on a profile, the suspension rules and the admin functions |

### 7.1 Enums

| Enum | Values |
|---|---|
| `user_role` | founder, investor, mentor, reviewer, admin |
| `account_status` | active, pending, suspended |
| `country_code` | NG, GH, KE |
| `product_stage` | idea, mvp, revenue, scaling |
| `evidence_status` | submitted, checking, needs_review, needs_more, approved, rejected, expired |
| `evidence_lane` | government, source, ai, human, human_confirmed, self |
| `league` | EARLY, RISING, INVESTABLE, ELITE |
| `waitlist_role` | founder, investor, mentor |
| `introduction_status` | pending, accepted, declined, withdrawn |

### 7.2 Tables

| Table | Key columns and rules |
|---|---|
| `profiles` | One row per Supabase Auth user. Role defaults to founder and status to active. Name is 2 to 120 characters and bio up to 600. A trigger blocks changes to role or status except by an admin or the service role. |
| `consents` | One row per answer, with the consent type (profile, evidence_processing, registry_check, bank_check, notifications or marketing), whether it was granted, and the policy version. |
| `ventures` | The founder, name (1 to 120), sector (one of five, checked for new rows), stage, country, website, social links, description (up to 280), ask (5 to 160 or null), `published_at`, and the hold columns `hidden_at`, `hidden_reason` (5 to 280) and `hidden_by`. |
| `rubric_versions`, `rubric_signals` | The rubric. Only one version can be active. |
| `evidence` | The venture, the signal code, the status, the lane, the figures, the summary (up to 280), the public note (up to 280), the reason, the decider, the expiry and the request key. |
| `evidence_files` | The storage path (unique), the SHA-256, the type (PDF, JPEG or PNG) and the size (up to 10 MB). |
| `verification_checks` | Rows for outside checks. Nothing writes them yet. |
| `reviews` | One row per staff decision. |
| `scores` | The current score per venture: total 0 to 1,000, league, categories and rubric version. |
| `score_events` | Score history. It is append-only. |
| `audit_log` | Every staff decision with its actor, entity, before and after. It is append-only. |
| `waitlist` | The waitlist. No signed-in user or visitor can read or write it. |
| `investor_interest` | The retired interest list. No signed-in user or visitor can read or write it. |
| `investor_profiles` | Investor type, firm, website, base, sectors, stages, countries, cheque size, thesis (up to 600) and the confirmed statement. |
| `pitches` | One per venture: the storage path, type, size (up to 50 MB), duration (up to 90 seconds) and transcript (20 to 2,000). |
| `venture_updates` | Progress updates of 10 to 600 characters, with a request key. |
| `introductions` | The investor, venture and founder, the note (20 to 600), the status, and the names and firm copied at the time of the request. One pending, accepted or declined request is allowed per investor and venture. |
| `introduction_messages` | Messages of 1 to 2,000 characters with a request key. They are append-only. |

### 7.3 Database functions

| Function | Rule |
|---|---|
| `app_role()`, `is_staff()`, `is_admin()`, `is_approved_investor()` | They read the caller's role, counting active accounts only. |
| `owns_venture(v)` | It is true when the caller owns the venture and is an active founder. |
| `venture_visible_to_investor(v)`, `founder_visible_to_investor(f)` | They are true for an approved investor and a published venture. |
| `venture_evidence(v)` | It returns evidence with one of three shown statuses, and never files, the reviewer, the reason or AI results. |
| `discover_ventures(...)` | It returns published ventures of active founders, filtered and sorted by name, 1 to 100 per call. |
| `submit_evidence(...)` | It saves evidence and its file records in one transaction, as the calling founder. |
| `decide_evidence(...)` | Staff only. It refuses the caller's own venture, decides a waiting item, and writes a review row and an audit row. |
| `decide_investor(...)` | Admins only. Approve sets active, decline sets suspended, and both write an audit row. |
| `record_score(...)` | Staff only. It writes the current score and, when the total changes, a history row. |
| `ventures_with_stale_scores()` | Staff only. It lists ventures decided after their score was computed. |
| `admin_hide_venture`, `admin_lift_hold` | Admins only. They hold or release a profile with a reason and an audit row. |
| `admin_set_role`, `admin_set_status` | Admins only. They refuse the caller's own account and write an audit row. |
| `admin_overview()`, `admin_ventures(...)` | Staff only. They return counts and the venture list. |
| `admin_accounts(...)` | Admins only. It is the only function that reads email addresses from `auth.users`. |
| `health()` | It returns true. It is the only function a visitor may call. |

### 7.4 Triggers

| Trigger | Rule |
|---|---|
| `*_updated_at` | It stamps `updated_at` on profiles, ventures, evidence, investor profiles and pitches. |
| `profiles_guard_privileges` | It blocks role and status changes by anyone but an admin or the service role. |
| `ventures_guard_publish` | It refuses to publish without a pitch or while held, on insert and on update. Only an admin or the service role may set the hold columns. |
| `introductions_prepare` | It checks the venture is published and the caller is an approved investor, enforces ten requests a day under a per-investor advisory lock, and copies the names. |
| `introductions_guard_update` | It allows only a status change from pending: the founder accepts or declines, and the investor withdraws. |
| `*_append_only` | It refuses updates and deletes on score events, the audit log and messages. |

### 7.5 Storage buckets

| Bucket | Access | Limits |
|---|---|---|
| `evidence` | Private. A founder uploads to their own folder and may see or remove a file only until it is recorded. Staff read through five-minute links. | 10 MB; PDF, JPEG or PNG |
| `pitches` | Private. A founder uploads to and deletes from their own folder. Staff and approved investors of a published founder may read. | 50 MB; MP4, WebM or QuickTime |

Paths are `<user id>/<random id>`, so a path never carries a file name.

## 8. Score engine

The score engine is in `score_engine/`. It was ported from TypeScript on 17 October 2026.

### 8.1 Rubric v2

| Category | Cap | Signals (mode, points, maximum, expected lane) |
|---|---|---|
| Identity | 100 | company_registration (fixed, 50, 50, source); government_id (fixed, 30, 30, source); operating_tenure (months, 1, 20, ai) |
| Legal | 100 | tax_registration (fixed, 50, 50, ai); legal_documents (per item, 10, 50, ai) |
| Financial | 200 | revenue (revenue, 1 per $100, 80, human); financial_records (months, 4, 40, ai); business_account (fixed, 50, 50, source); financial_statements (per item, 10, 30, ai) |
| Product | 200 | product_stage (stage, 0, 130, ai, with idea 0, mvp 50, revenue 90 and scaling 130); customer_evidence (per item, 10, 70, ai) |
| Market | 100 | customer_interviews (per item, 5, 40, ai); pilot_letters (per item, 10, 40, ai); market_research (fixed, 20, 20, ai) |
| Team | 150 | team_members (per item, 5, 40, ai); team_credentials (per item, 15, 60, ai); student_status (fixed, 20, 20, ai); programme_completed (per item, 15, 30, ai) |
| Media | 100 | website_live (fixed, 20, 20, source); social_profile (fixed, 20, 20, ai); pitch_deck (fixed, 20, 20, ai); press_coverage (per item, 10, 40, ai) |
| Operations | 50 | operational_evidence (per item, 10, 50, ai) |

The caps total 1,000. The seed migration is generated from `rubric.py`, and a test fails if the two differ.

### 8.2 Lane weights (TRD Score engine rule 2)

| Lane | Weight |
|---|---|
| government | 1.0 |
| source | 0.95 |
| human_confirmed | 0.95 |
| ai | 0.85 |
| human | 0.85 |
| self | 0 (PRD E-6) |

The review form offers only the human, government and source lanes.

### 8.3 Calculation (PRD S-1)

1. An item counts only when it is approved, its lane weight is above 0, and it has not expired.
2. Each item earns points by mode, multiplied by its lane weight. A fixed item earns its points. A per-item signal earns points per item. A months signal earns points per whole month. A revenue signal earns a point per $100. A stage signal earns the stage's points.
3. Per-item signals sum their items. Every other mode takes its best single item.
4. Each result rounds to two decimals. Each signal is capped at its maximum, and each category at its cap.
5. The total is the floor of the sum. Without countable company registration, a total above 600 becomes 600 (PRD S-6).
6. The league follows from the total: Early from 0, Rising from 301, Investable from 601 and Elite from 851.

### 8.4 Currency (TRD rule 4)

`convert_to_usd` multiplies a local amount by one stated rate, which must be positive and finite, and rounds to cents. The caller stores the rate with the result.

### 8.5 Next best actions (PRD P-3, O-4)

For each signal the engine estimates the gain from one more piece of evidence at the signal's expected lane, limited by the room left under the signal and category caps. It keeps gains above 0, sorts them by gain and then by code, and returns five by default. The founder's dashboard asks for three and leaves out signals with evidence already waiting. The engine does not consider the cap of 600.

## 9. Health and observability

### 9.1 Health

`GET /api/health` calls `health()` as a visitor with a five-second limit. It answers 200 `{"status":"ok","supabase":"ok"}` when the database answers, and 503 with `degraded` otherwise. It checks neither Auth nor Storage. Render's own health check uses `/`, which makes no Supabase call, so a Supabase outage does not make Render restart the app.

### 9.2 Logs

Each event is one line of JSON with the time, level, event name and fields. Information goes to standard output, and warnings and errors go to standard error. Some fields named `code` carry Supabase's message text rather than a code.

### 9.3 Sentry

Sentry starts only when `SENTRY_DSN` is set, with personal data off, no tracing and no breadcrumbs. Every event is cut down to its name, codes, ids, and the request's method and path. A check on 17 October 2026 against a stand-in found no cookie, token, email or form text in the event. `docs/OPERATIONS.md` records that no Sentry project exists.

## 10. Tests and CI

| Suite | What it covers | Last recorded result |
|---|---|---|
| `service/tests`, 9 files, 201 cases | Forms, guards, the waitlist, investor rules, product rules, the score engine (47 cases), sign-in and sessions, the eleven pages, staff rules and the system routes | All 201 passed on Python 3.13.16 on 19 October 2026 |
| `supabase/tests/01_rls_checks.sql` | 25 checks of basic row level security | Passed on 15 October 2026 |
| `supabase/tests/02_investor_checks.sql` | 77 checks of the investor side | Passed on 15 October 2026 |
| `supabase/tests/03_resilience_checks.sql` | 13 checks of atomic evidence, request keys, stale scores and the daily limit | Passed on 15 October 2026 |
| `supabase/tests/04_admin_checks.sql` | 43 checks of the admin migration | Passed on 17 October 2026 |
| `supabase/tests/race_introductions.sh` | Two simultaneous requests at nine leave ten | Passed on 15 October 2026 |

The SQL checks run on a plain PostgreSQL 16 with a stub of Supabase's roles and functions. The live project runs PostgreSQL 17.11, and the checks have not been run there.

The founder, investor, introduction and staff routes are tested through their parsers and formatters, not through HTTP.

CI runs on every pull request and every push to `main`. It installs `requirements-dev.txt` on Python 3.13 and runs pytest in `service`. It runs no lint and no SQL checks.

## 11. Deployment

### 11.1 Blueprint

`render.yaml` describes one Python web service named `ikonetu-web` in Frankfurt. The build command is `pip install -r service/requirements.txt`. The start command is `cd service && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. The health check path is `/`.

### 11.2 Live state

| Item | State, as checked |
|---|---|
| Render service | `srv-db9not7btjjs73cdf950`, Frankfurt, free plan, at `https://ikonetu-platform.onrender.com`. It served the Python app on 18 October 2026. |
| Variables on Render | `PYTHON_VERSION`, `TRUSTED_PROXY_HOPS`, `NEXT_PUBLIC_SITE_URL` (the onrender address), `NEXT_PUBLIC_SUPABASE_URL`, the publishable key and the service role key were set on 18 October 2026. `SENTRY_DSN` is not set. |
| Supabase project | `ybqzzydefcaczjqpgwvh`, PostgreSQL 17.11. All eight migrations were applied by 18 October 2026, and each file's objects were confirmed afterwards. |
| Health | `GET /api/health` answered 200 `{"status":"ok","supabase":"ok"}` on 19 October 2026. The first request that day timed out after 20 seconds, and the second answered in 11 seconds. |
| `HEAD /` | It answered 405 on 18 October 2026. |
| Custom domain | Render refused `ikonetu.com` with 409 "This domain already exists on another site". A support request was drafted, and the matter is unresolved. |
| Supabase Auth URL configuration | Setting the Site URL and the redirect URL for `/auth/callback` was still open on 18 October 2026. |
| First admin | Making the first admin with SQL was still open on 18 October 2026. |

**Unverified**: whether `TRUSTED_PROXY_HOPS` of 1 matches Render's proxies (check 8 in `docs/HOSTING.md`), whether the Supabase project applies an upload limit lower than 50 MB, and the Supabase Auth settings for the code length, code life and token life.

## 12. Known technical gaps

These are facts found in the code on 19 October 2026. They are recorded here so that the next change can be checked against them.

1. `APP_ENV` is read and nothing uses it.
2. `score_engine/engine.py` cites `tests/test_score_engine_parity.py`, which is not in the repository, because the TypeScript engine it compared against was removed.
3. `requirements-dev.txt` pins only pytest.
4. No request body limit exists. The evidence and update forms are parsed before the sign-in check.
5. Static files are served with no `Cache-Control` header.
6. Some log fields named `code` carry message text, which contradicts `log.py`.
7. The queue page still says that a stale score means its founder sees an out-of-date score, although founders no longer see a score.
8. No migration or app code sets the evidence statuses `checking` and `expired`, the AI lanes, `expires_at`, or any `verification_checks` row, although they are read and shown.
9. `rubric_signals.expiry_days` is never seeded and never read.
10. `evidence.signal_code` has no foreign key to the rubric.
11. The CI does not run the SQL checks.
