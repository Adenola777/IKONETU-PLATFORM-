# Hosting the IkonetU web app

The website and the signed-in app are one Python app in `service`. It runs as one web service on Render in Frankfurt, and it uses Supabase for sign-in and the database. This file lists what has to be set up, in order, before the public address serves it.

Written on 15 October 2026 for the Next.js app, and changed on 17 October 2026, when the app was rebuilt in Python. Render's documentation could not be reached from either session, so every Render detail below is marked **unverified**. On 17 October the build command was run as written into a fresh Python 3.13.16 environment and installed exactly the pinned packages, and the start command was run as written and the app answered on the port given in `PORT`.

## 1. Supabase

1. Apply the four migrations of 15 October to the Supabase project in order, after the three earlier migrations: `20261015000001_investor_interest.sql`, `20261015000002_investor_side.sql`, `20261015000003_venture_ask.sql` and `20261015000004_resilience.sql`. The first creates the `investor_interest` table, which the retired interest form wrote. The second creates the investor side and the private `pitches` storage bucket. The third adds the founder's ask and returns it from `discover_ventures()`. The fourth saves evidence and its files in one transaction, keeps a form sent twice once, holds the daily limit on introduction requests under simultaneous requests, and adds `health()` and the staff list of scores to update. Until the second, third and fourth are applied, the founder, investor and staff pages fail, because they read the tables, columns and functions those create. The SQL checks in `supabase/tests` were run against all seven migrations on a local PostgreSQL 16 on 15 October 2026. Then apply `20261017000001_admin.sql`, which adds the admin pages' functions, the hold on a profile and the rules for suspended accounts. Until it is applied, `/admin`, `/admin/founders`, `/admin/people` and `/admin/audit` fail, and founders cannot reach their dashboard, because it reads the new hold columns. Its checks were run against all eight migrations on a local PostgreSQL 16 on 17 October 2026. Then apply `20261020000001_score_v3.sql` and `20261020000002_rubric_v3.sql`, in that order. The first adds the rubric's categories, the monthly score record, the founder's own statements and the new rules for recording a score. The second seeds rubric v3 and makes it the active rubric. Until both are applied, the founder's dashboard fails, because it reads the monthly record. Their checks, `supabase/tests/05_score_checks.sql`, were run against all ten migrations on a local PostgreSQL 16 on 20 October 2026, and the earlier checks still passed. Then apply `20261024000001_investor_register.sql`, after the migrations above and `20261021000001_any_country.sql`. It adds the investor register that admins read and add to at `/admin/register`. Until it is applied, those two pages fail. Its checks, `supabase/tests/06_register_checks.sql`, were run against all thirteen migrations on a local PostgreSQL 16 on 24 October 2026, and the earlier checks still passed.
2. Under Authentication, URL Configuration, set the Site URL to the public address, for example `https://ikonetu.com`, and add `<that address>/auth/callback` under Redirect URLs.
3. The other Supabase Auth settings are listed in the README under "Sign-in".
4. After the first admin has signed in once, make them an admin with the SQL in the README under "The signed-in app".
5. The `pitches` bucket allows files of up to 50 MB. Whether the Supabase project applies a lower upload limit of its own was not checked (**unverified**). If it does, pitches above that limit are refused, and the founder sees that the upload did not finish.

## 2. Render

`render.yaml` at the root of the repository describes the service. It is **unverified**, because Render's schema for the file could not be read. Render checks the file when a blueprint is created from it and names any field it does not accept.

| Setting | Value |
|---|---|
| Service type | Web service, Python |
| Region | Frankfurt |
| Build command | `pip install -r service/requirements.txt` |
| Start command | `cd service && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/` |
| Python version | 3.13.16, set through `PYTHON_VERSION` (**unverified** as Render's way of choosing it) |

The start command reads the port from `PORT`. Render sets `PORT` for a web service (**unverified**).

A service already created from the Next.js blueprint keeps its old runtime and commands until they are changed in the Render dashboard or the blueprint is applied again (**unverified**: how Render applies a changed blueprint to a service it already runs). Its environment variables keep working, because the Python app reads the same names.

## 3. Environment variables

Each value is entered in the Render dashboard. None is written in this repository, and none is pasted into a conversation.

| Variable | Where it is used | Notes |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | Page metadata, the site map, the sign-in email link | The public address with `https://` and no trailing slash |
| `NEXT_PUBLIC_SUPABASE_URL` | Sign-in and the signed-in pages | Safe in the browser |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Sign-in and the signed-in pages | Safe in the browser |
| `SUPABASE_SERVICE_ROLE_KEY` | `POST /api/v1/waitlist`, and recording a founder's score after their own statement | Server only. It bypasses row level security, so it must never be committed or sent to a browser |
| `NEXT_PUBLIC_PHONE_SIGN_IN` | The sign-in page | Leave unset until an SMS and WhatsApp provider is set up in Supabase Auth |
| `TRUSTED_PROXY_HOPS` | The waitlist's rate limit | The number of proxies in front of the app, 1 in `render.yaml`. **Unverified** for Render: see check 8 below |
| `CLIENT_IP_HEADER` | The waitlist's rate limit | Optional. A single header the edge sets with the caller's address, used instead of `X-Forwarded-For` |
| `SENTRY_DSN` | Error reports from the server | Server only. Leave unset until Sentry is named in the privacy policy; `docs/OPERATIONS.md` has the steps |
| `SENTRY_ENVIRONMENT` | Error reports | Optional, `production` unless set |

The names starting with `NEXT_PUBLIC_` are kept from the Next.js app, which wrote them into the browser code when it was built. The Python app reads every variable when it starts, so a change needs a restart rather than a new build. The Content-Security-Policy allows the browser to upload pitches to `NEXT_PUBLIC_SUPABASE_URL` and to play them from it, so that address must be right before pitches can be uploaded.

## 4. The domain

The domain's DNS records point it at the Render service. Render shows the records to add when the custom domain is added to the service (**unverified**). Who holds the DNS for `ikonetu.com` was not established in the session that wrote this file.

## 5. Checks after the first deployment

1. The home page, `/pricing`, `/privacy`, `/terms`, `/cookies` and `/complaints` load at the public address.
2. `/robots.txt` and `/sitemap.xml` name the public address, which shows `NEXT_PUBLIC_SITE_URL` was set when the app started.
3. `/investor-interest` redirects to `/for-investors`.
4. A test founder uploads a short pitch at `/dashboard/pitch` and it plays back, which shows the browser can reach Supabase Storage under the Content-Security-Policy.
5. A test investor signs up, an admin approves them at `/admin/investors`, and the investor finds the test founder at `/investor` once the founder has published.
6. A sign-in at `/signin` sends the email, and its link returns to `/auth/callback` on the public address.
7. The response headers carry the Content-Security-Policy set in `service/app/security.py`.
8. The rate limit reads the right address. Send six requests to `POST /api/v1/waitlist` from one computer, each with a different made-up `X-Forwarded-For` value, for example `curl -X POST -H 'content-type: application/json' -H 'x-forwarded-for: 10.0.0.1' -d '{}' <address>/api/v1/waitlist`. The sixth must answer 429. If it does not, the address the app reads is still the one the caller wrote, and `CLIENT_IP_HEADER` must name the header in which Render passes the caller's address. Within ten minutes, send one request from a phone on a different network. It must not answer 429. If it does, every caller shares one count, because the app is reading the address of one of Render's own proxies, and `TRUSTED_PROXY_HOPS` must be raised by one.
9. `GET /api/health` answers 200 with `"supabase":"ok"`. Point an uptime monitor at it, as `docs/OPERATIONS.md` describes.

## What the app does not need

- The fonts are in `service/app/static/fonts` and are served by the app itself, so no request goes to Google Fonts.
- The product screens are in `service/app/public/media` and are served by the app.
- The app sets no analytics or advertising cookies.

## Health checks

Render's health check stays on `/`, which is drawn from a template and makes no call to Supabase. `/api/health` checks Supabase and is meant for an uptime monitor, so an outage at Supabase is reported without making the app look broken to Render.

## Rate limiting

The waitlist endpoint limits each IP address in memory. It reads the address the nearest proxy added to `X-Forwarded-For`, because the start of that header is whatever the caller wrote; reading the start let a caller choose a new address for every request, which a test on 15 October 2026 confirmed. Each running instance keeps its own count, so the limit only slows casual abuse. SRD SEC-W4 asks for a limit in front of the app as well. Which of Render's features can provide it is **unverified**.

## Vercel

On 22 October 2026 the owner chose to have Vercel build the Python app as well, beside Render. The Vercel project `ikonetu-platform` was still set up for the Next.js app removed on 17 October, so every build after that failed with "The specified Root Directory "apps/web" does not exist." The same day its Root Directory was set to `service` and its Framework to FastAPI.

`service/vercel.json` holds the two settings the build needs. Both were found by running `vercel build` from Vercel CLI 65.0.0 on commit ea89564 on 22 October 2026. That command builds locally and deploys nothing.

- `installCommand` installs `requirements.txt`. Without it, Vercel installed from `pyproject.toml`, which lists no packages, so the bundle held no FastAPI, Starlette, Jinja2 or httpx and the app could not start.
- `includeFiles` keeps `app/public` in the bundle. Without it, Vercel left out all 14 files in that folder, and the app stopped at start with "Directory '.../app/public/media' does not exist", because it serves `/media` from there.

With both settings the bundle was rebuilt and run locally under Python 3.12, which Vercel chose from `requires-python`. Every website page, the stylesheet, a product screen, the tour music and the icon answered 200, and an unknown path answered 404. All 401 tests pass under Python 3.12. Render runs Python 3.13.16.

The first deployment on Vercel, `dpl_C9kv43QVFQa5BMQLzUmDHbhkkqfn` from e4c6019 on 22 October 2026, was built by Vercel CLI 64.7.0 under Python 3.12 and installed the pinned packages. Through Vercel sign-in, its home page, the icon, the font licence and `/api/health` answered 200, and the health check reported `"supabase":"ok"`. A product screen also answered 200, but as `application/octet-stream`, because Python 3.12's own table of file types has no `.webp` or `.woff2` and Vercel's machines supply no `/etc/mime.types`. Since that day the app names both types itself in `name_file_types()` in `service/app/main.py`, and a test strips the system's list to reproduce Vercel's conditions.

Vercel holds `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SERVICE_ROLE_KEY` for production and preview, and `NEXT_PUBLIC_SITE_URL` for production alone, as listed on 22 October 2026. Vercel Authentication covers the project's preview deployments, so a preview asks for a Vercel sign-in first.

**Unverified** on Vercel: sign-in on a Vercel address, which needs `<that address>/auth/callback` under Supabase's Redirect URLs; and the waitlist's rate limit, which reads `TRUSTED_PROXY_HOPS` and was set for Render's proxies, so the check in step 8 above has to be repeated on Vercel.
