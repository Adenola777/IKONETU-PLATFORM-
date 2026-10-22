# IkonetU Security Requirements Document (reconstructed)

## About this document

This document was reconstructed on 19 October 2026 at the owner's request. It is not the SRD of 5 October 2026. That original could not be found in the repository or anywhere this session can reach, so this document was written from the code on `main` at commit `3473aca`, from `docs/DECISIONS.md`, from `README.md`, `docs/HOSTING.md` and `docs/OPERATIONS.md`, from the eight migrations in `supabase/migrations`, and from the published privacy policy.

It describes the security of the system as built. A requirement ID such as **SRD SEC-A1** appears only where the code or the documents cite it, and the original wording behind each ID is unknown. **Unverified** marks anything not checked against the live service. File paths are relative to `service/app/` unless they start with `supabase/` or name a file at the root.

The companion documents are `docs/PRD-reconstructed.md` and `docs/TRD-reconstructed.md`.

## 1. What is known of the original SRD

| ID | What the repository records | Where |
|---|---|---|
| SEC-A1 | The email carries a 6-digit code. The README asks for the code to last 300 seconds and to be 6 digits long. | `docs/DECISIONS.md`; `README.md`; `signin.py:20, 106` |
| SEC-A2 | Five wrong codes lock the phone or email for 30 minutes, and code requests are limited to 5 an hour per address and 20 an hour per IP address. | `docs/DECISIONS.md` |
| SEC-A3 | The README asks for the access token to last 900 seconds, with refresh token rotation and reuse detection on. | `README.md` |
| SEC-A9 | The code cites it for the confirmation that the person is 18 or older. | `signin.py:72` |
| SEC-D4, SEC-D5 | The code cites them for the consents table and the consent choices at onboarding. | `core.sql:110`; `forms.py:67` |
| SEC-E1, SEC-E2, SEC-E5 | The code cites them together for private evidence storage, with files under `<user id>/<random id>` so that a path never carries a name. It cites SEC-E2 alone for evidence links that last five minutes. | `core.sql:330`; `routes/staff.py:201` |
| SEC-I1 | The README and `.env.example` cited it for where keys are kept. | `.env.example:4`; `docs/DECISIONS.md` |
| SEC-I3 | Every table holding user data has row level security. | `core.sql:2` |
| SEC-I5 | The audit log is append-only, and admins read it. | `core.sql:311` |
| SEC-W2 | The code cites it for the security headers. | `security.py:3` |
| SEC-W4 | A rate limit sits in front of the app. | `guards.py:51`; `docs/DECISIONS.md` |

## 2. Status of each cited requirement

| ID | Status | Basis |
|---|---|---|
| SEC-A1 | Partly met, and **unverified** | The app accepts exactly 6 digits. It does not check the code's age itself, so the 300-second life depends on a Supabase Auth setting that has not been read. The default email carries a link rather than a code, which `docs/DECISIONS.md` records as an open departure. |
| SEC-A2 | Not met | The app adds no lockout, because a lockout kept by the app can be bypassed by calling Supabase directly with the public key. Supabase Auth's own rate limits apply. The decision is open and needs a Supabase Auth hook or a confirmed Supabase setting. |
| SEC-A3 | **Unverified** | The token life and refresh rotation are Supabase dashboard settings. The repository holds no Supabase configuration file, so whether they are applied is unknown. |
| SEC-A9 | Met | Sign-in requires the "I am 18 or older." tick and stores it on the account. Onboarding asks again only when sign-in did not record it. |
| SEC-D4, SEC-D5 | Met as recorded consents, with one open decision | Every answer is stored with its policy version. Nothing reads the evidence consent, which `docs/DECISIONS.md` leaves open for the owner. |
| SEC-E1, SEC-E2, SEC-E5 | Met | Both buckets are private. Paths carry ids and no names. Evidence files open through links that last five minutes, and pitches through links that last one hour, as the owner chose. |
| SEC-I1 | Met in the repository | No key is in the repository. Every key is entered in the Render dashboard. Section 10 notes one exposure inside the app. |
| SEC-I3 | Met, with a note | Row level security is enabled on every table. It is not forced, which matters only for the table owner. |
| SEC-I5 | Met, with a note | Triggers refuse UPDATE and DELETE on the audit log. They do not cover TRUNCATE. Only admins read it. |
| SEC-W2 | Partly met | Every response carries the headers except the 500 error page. |
| SEC-W4 | Not met | No limit sits in front of the app. Only the waitlist endpoint has a limit, kept in memory by the app. |

## 3. Data held and who may read it

| Data | Where | Who may read it |
|---|---|---|
| Email address | Supabase Auth | The person, and admins through `admin_accounts()`. Reviewers and investors cannot. |
| Phone number | Supabase Auth, only if phone sign-in is switched on | The person. Phone sign-in is off. |
| Profile (name, country, city, institution, status, bio) | `profiles` | The person and staff. An approved investor reads a founder's card only while the founder has a published venture. |
| Venture details and the ask | `ventures` | The founder and staff, and approved investors while the venture is published. Other founders cannot. |
| Pitch video and transcript | `pitches`, the `pitches` bucket | The founder and staff, and approved investors while the venture is published |
| Evidence summary and status | `evidence` | The founder and staff. Investors see only the label, the summary, the shown status, the public note and the dates through `venture_evidence()`, and never rejected, expired or "needs more" items. |
| Evidence files | `evidence_files`, the `evidence` bucket | The founder and staff. Investors never. |
| Reviewer and reason | `evidence`, `reviews` | The founder sees the reason. Staff see both. Investors never. |
| Score and score history | `scores`, `score_events` | The founder and staff. No page shows the founder's score. Investors never. |
| Investor details | `investor_profiles` | The investor and staff. A founder sees the name, type and firm copied onto a request. |
| Introductions | `introductions` | The founder, the investor and staff |
| Messages | `introduction_messages` | Only the founder and the investor. Staff cannot. |
| Consents | `consents` | The person |
| Audit log | `audit_log` | Admins |
| Waitlist and investor interest list | `waitlist`, `investor_interest` | No signed-in user or visitor. Only the server's service role writes the waitlist. |

## 4. Authentication

### 4.1 Email sign-in

1. `POST /signin` takes an email of up to 160 characters and the age tick.
2. The server makes a PKCE pair. The verifier is 112 hex characters, and the challenge is its SHA-256 in base64url.
3. The server asks Supabase Auth to send the email, with the challenge and a return address of `<site>/auth/callback`.
4. The server keeps the address in a cookie on the path `/signin` and the verifier in a separate cookie. The address never goes into the URL.
5. The person either types the code at `/signin/code` or opens the link, which returns to `/auth/callback`. The link works only in the browser that holds the verifier cookie.
6. Supabase checks the code or exchanges the link's code, and the server sets the session cookies.

The reply to step 1 is the same whether or not the address already has an account. A wrong code says "That code is wrong or has expired." Supabase's 429 is shown as a request to wait.

### 4.2 Phone sign-in

Phone sign-in is built and switched off. When `NEXT_PUBLIC_PHONE_SIGN_IN` is `on`, the code goes by WhatsApp first and by SMS on request, and the page shows only the last four digits of the number.

### 4.3 Sessions

The session is Supabase's access token and refresh token, held in two cookies. On each request that needs the viewer, the server reads the user from Supabase. It refreshes the session when the token expires within 60 seconds, reading the expiry without checking the signature, and only to time the refresh. A 401 or 403 from Supabase triggers one refresh and one retry. The viewer's identity comes from Supabase's answer to `GET /auth/v1/user`, and not from the token's contents.

### 4.4 Sign-out

`POST /signout` asks Supabase to sign the person out everywhere, deletes both session cookies and returns to the home page. It does not check Supabase's answer.

### 4.5 Cookies

| Cookie | Path | Life | Flags | Holds |
|---|---|---|---|---|
| `ik_access` | `/` | 400 days | HttpOnly, SameSite Lax, Secure with an https site address | The access token |
| `ik_refresh` | `/` | 400 days | The same | The refresh token |
| `ik_pending_sign_in` | `/signin` | 600 seconds | The same | Unsigned base64url JSON with the email or phone, the channel and the time sent |
| `ik_pkce` | `/` | 600 seconds | The same | The PKCE verifier |
| `ik_flash` | `/` | 60 seconds | The same | A one-time confirmation message |

The browser's local storage holds one item, `ikonetu-side`. The app sets no analytics or advertising cookies.

## 5. Authorisation

### 5.1 Two layers

Each signed-in page passes a guard in `session.py`. A visitor goes to `/signin`. `require_founder` needs an active founder with a venture. `require_investor` needs an active investor. `require_staff` needs an active reviewer or admin, and its admin option limits a page to admins.

Every query then runs as the signed-in user, so row level security in the database decides each read and write again. The README states the reason: a bug in a page cannot widen what a person sees.

### 5.2 Rules the database enforces

| Rule | Where |
|---|---|
| Nobody changes their own role or status. Only an admin or the service role can. | `profiles_guard_privileges` trigger; `admin_set_role`; `admin_set_status` |
| A new profile is either an active founder or a pending investor. | Insert policy on `profiles` |
| A pending or suspended account reads nothing an approved account can, because the role helpers count active accounts only. | `app_role()` |
| A suspended founder, or one whose role changed, reads and writes nothing through `owns_venture()`. | `owns_venture()` |
| A founder submits evidence only as `submitted`, with no lane, decider, note, reason or expiry. | Insert policy on `evidence` |
| Nobody decides evidence on their own venture. | `decide_evidence()` |
| A venture cannot be published without a pitch, or while held. | `ventures_guard_publish` |
| Only an admin or the service role can hold a profile or lift a hold. | `ventures_guard_publish` |
| An introduction's status moves once, from pending. The founder accepts or declines, and the investor withdraws. No other column changes. | `introductions_guard_update` |
| An investor sends at most ten requests in a rolling day, under a lock per investor. | `introductions_prepare` |
| Messages are sent only on an accepted introduction, and only by its two people. | Insert policy on `introduction_messages` |
| Score history, the audit log and messages cannot be updated or deleted. | Append-only triggers |
| The admin functions refuse anyone but an admin, and the staff functions anyone but staff. | Each function's first check |

### 5.3 Function rights

Every SECURITY DEFINER function sets `search_path = public`. Execute rights are revoked from `public` and `anon` and granted to `authenticated`. The only function a visitor may call is `health()`, which reads nothing. `submit_evidence()` runs as the caller, so the policies on evidence and its files decide each insert.

### 5.4 The public profile view

`public_profiles` runs with its owner's rights and filters its rows itself: the caller's own card, staff, or an approved investor reading a founder with a published venture. Migration `20261005000003` closed a gap in which Supabase's defaults let a visitor read, rename and delete founder profiles through this view. Visitors now have no right on it, and signed-in users may only select.

## 6. File storage (SEC-E1, SEC-E2, SEC-E5)

| Rule | Evidence | Pitches |
|---|---|---|
| Bucket | Private | Private |
| Path | `<user id>/<random id>` | `<user id>/<random id>.<ext>` |
| Size and type | Up to 10 MB; PDF, JPEG or PNG | Up to 50 MB; MP4, WebM or QuickTime |
| Upload | The founder, into their own folder only | The founder, into their own folder only, straight from the browser |
| Read | Staff, through links that last five minutes. The founder may see a file only until it is recorded. | The founder, staff, and approved investors of a published founder, through links that last one hour |
| Delete | The founder, only a file not yet recorded | The founder, in their own folder |

The server takes a SHA-256 of each evidence file, and the review page warns when the same file is attached to other evidence. The file type is the one the browser declares, and the app does not inspect the content. For a pitch, the server checks that the path is in the founder's own folder and records the size, type and duration the browser reports. It does not inspect the stored video.

## 7. Web protections

### 7.1 Security headers (SEC-W2)

Every response except the 500 error page carries:

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; media-src 'self' blob: <supabase origin>; connect-src 'self' <supabase origin>; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

No template holds an inline script or event handler, so `script-src 'self'` holds without exceptions. Inline styles are allowed because the templates hold 129 `style` attributes.

### 7.2 Cross-site form posts

`SecurityMiddleware` refuses a POST, PUT, PATCH or DELETE outside `/api/` whose `Origin` names another host, with 403 "This form must be sent from the IkonetU site." An `Origin` of `null` is refused, and a missing `Origin` passes. The host compared is the first value of `X-Forwarded-Host`, or `Host`. The session cookies are SameSite Lax as well.

### 7.3 Rate limits (SEC-W4)

| Path | Limit |
|---|---|
| `POST /api/v1/waitlist` | 5 requests per 10 minutes per address, held in memory per process. The address is the `X-Forwarded-For` entry `TRUSTED_PROXY_HOPS` places from the end, or the `CLIENT_IP_HEADER` value. Callers whose address cannot be read share one count. |
| Sign-in | No limit in the app. Supabase Auth's own limits apply, and its 429 is shown to the person. |
| Introduction requests | Ten a day per investor, enforced by the database. |
| Everything else | No limit. |

**Unverified**: whether `TRUSTED_PROXY_HOPS` of 1 matches Render's proxies. Check 8 in `docs/HOSTING.md` describes the test.

### 7.4 Input and output

Every form is parsed by a strict parser with length limits counted in UTF-16 units, and ids must have the UUID shape. The waitlist accepts JSON only, refuses unknown keys, refuses text above 4,096 characters, and answers a filled honeypot or a duplicate with the normal success. Jinja2 escapes every value, and no template marks a value as safe. Each form that writes evidence, an update or a message carries a request key, so a form sent twice is saved once.

## 8. Privacy and consent

### 8.1 Consents (SEC-D4, SEC-D5)

| Consent | Recorded when |
|---|---|
| profile | Always granted at onboarding and at investor sign-up |
| evidence_processing | A founder's optional choice at onboarding |
| notifications | An optional choice for founders and investors. IkonetU sends nothing yet. |
| registry_check, bank_check, marketing | The database accepts them, and no form asks for them |

Every answer, including a no, is stored with the policy version `2026-10-15`. The consents table has no update policy, so a person changes an answer by writing to privacy@ikonetu.com.

### 8.2 The privacy policy

IkonetU Technology Limited adopted the privacy policy on 15 October 2026. It names Render (hosting, Frankfurt) and Supabase (sign-in, sign-in emails, the database and stored files) as the only sub-processors, and says IkonetU uses no analytics or payment provider. Its ICO registration number still reads "[TO CONFIRM]".

The policy sets retention: account data while the account is active and for one year after it closes, founder profile and pitch data for one year after deletion, and introduction, support and security records for one year. No code or migration deletes data on a schedule, so retention is not enforced by the system. Accounts are closed on request to privacy@ikonetu.com, and the app has no deletion feature.

The policy lists some data the app does not collect, such as a profile photo and click-level technical data.

### 8.3 Open privacy items

| Item | State |
|---|---|
| Sentry | The privacy policy must name Sentry before `SENTRY_DSN` is set. |
| Email addresses on staff pages | Whether the policy covers admins seeing email addresses is the owner's to confirm. |
| Evidence consent | The answer is recorded and not enforced. The owner decides. |

### 8.4 Age

The platform is for people aged 18 or older. Sign-in, onboarding where needed, and the waitlist each require the confirmation (SEC-A9).

## 9. Audit (SEC-I5)

The database writes an audit row for every staff decision: investor approval and decline, evidence decisions, holds and lifts, role changes, suspensions and reactivations. Each row holds the actor, the entity, the before and after values and the reason. Only admins read the log, at `/admin/audit`, with times in UTC. Triggers refuse UPDATE and DELETE on it.

## 10. Secrets and keys (SEC-I1)

| Key | Where it lives | Who holds it |
|---|---|---|
| Supabase publishable key | Render's dashboard | The server, and the pitch page, which needs it for the upload. It is safe in the browser. |
| Supabase service role key | Render's dashboard | The server only. It bypasses row level security, and the app uses it only for the waitlist insert. |
| Sentry DSN | Not set | Nobody yet |

No key is in the repository, and `.env` files are ignored. Two facts about the app bear on this rule:

1. The whole settings object, including the service role key and the Sentry DSN, is a Jinja global. No template references it.
2. `POST /dashboard/pitch/token` returns the founder's access token to page script by design, so the browser can upload the pitch to Storage.

## 11. Logging and error reporting

Each failure is one line of JSON carrying the time, level, event name, ids and codes. The logging module says fields carry ids and error codes only, but some fields named `code` carry Supabase's message text.

Sentry starts only when `SENTRY_DSN` is set. It sends no personal data, no traces and no breadcrumbs, and `scrub()` cuts every event down to the request's method and path without the query string, and drops the user and the breadcrumbs. A check on 17 October 2026 against a stand-in for Sentry found no cookie, token, email or form text in the event. The same check on the earlier Next.js app found that Sentry's library sent the sign-in cookies and the form text unless they were removed.

## 12. Operations

| Item | State recorded in `docs/OPERATIONS.md` |
|---|---|
| On call | The owner, until IkonetU has staff |
| Access holders | GitHub is held by Adenola777. Render and Supabase are not recorded. No Sentry project exists. |
| Uptime monitor | Not set up. It should call `/api/health` and alert after two failures. |
| Backups | The plan, daily backups, point-in-time recovery and Storage coverage have not been checked. No restore has been tried. |
| Incidents | A short note goes in `docs/incidents/` within a week, without blame. |

## 13. Known security gaps

These are facts found in the code and migrations on 19 October 2026. Items 1 to 9 were read in the code, and item 1 was also run in memory.

1. **The 500 page carries no security headers.** The handler for unhandled exceptions runs in Starlette's outermost middleware, outside `SecurityMiddleware`. A test in memory showed the 500 response without CSP or `X-Frame-Options`, while the 404, 403 and 200 responses had them.
2. **No request body limit exists.** Starlette's form parser spools file parts to temporary files with no size limit, and the evidence and update forms are parsed before the sign-in check.
3. **A failed refresh signs the person out**, including after a network error or a timeout.
4. **The pending sign-in cookie is unsigned** and holds the email or phone in clear. It is HttpOnly and lasts ten minutes.
5. **The settings object, with the service role key, is a Jinja global.** No template uses it.
6. **`record_score()` has no own-venture check.** It requires staff, and unlike `decide_evidence()` it does not refuse a staff member's own venture.
7. **A suspended founder can open a conversation page by its address.** The route skips the status check for the founder, and the read policies on introductions and messages test only that the caller is one of the two people. This was read from the migrations and was not run. The database refuses a suspended founder's messages.
8. **The append-only triggers do not cover TRUNCATE.**
9. **Row level security is enabled and not forced.**
10. **SEC-A2 is not met**, and sign-in relies on Supabase Auth's own limits.
11. **SEC-W4 is not met**, and the waitlist limiter is per process and in memory.
12. **SEC-A1 and SEC-A3 depend on Supabase settings that have not been read.**
13. **Backups have not been checked**, and no restore has been tried.
