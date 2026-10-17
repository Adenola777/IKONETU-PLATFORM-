# Hosting the IkonetU web app

The website and the signed-in app are one Next.js app in `apps/web`. It runs as one web service on Render in Frankfurt, and it uses Supabase for sign-in and the database. This file lists what has to be set up, in order, before the public address serves it.

Written on 15 October 2026. Render's documentation could not be reached from the session that wrote it, so every Render detail below is marked **unverified**. The build and start commands were run as written on Node 22, and the app answered on the port given in `PORT`.

## 1. Supabase

1. Apply the four migrations of 15 October to the Supabase project in order, after the three earlier migrations: `20261015000001_investor_interest.sql`, `20261015000002_investor_side.sql`, `20261015000003_venture_ask.sql` and `20261015000004_resilience.sql`. The first creates the `investor_interest` table, which the retired interest form wrote. The second creates the investor side and the private `pitches` storage bucket. The third adds the founder's ask and returns it from `discover_ventures()`. The fourth saves evidence and its files in one transaction, keeps a form sent twice once, holds the daily limit on introduction requests under simultaneous requests, and adds `health()` and the staff list of scores to update. Until the second, third and fourth are applied, the founder, investor and staff pages fail, because they read the tables, columns and functions those create. The SQL checks in `supabase/tests` were run against all seven migrations on a local PostgreSQL 16 on 15 October 2026. Then apply `20261017000001_admin.sql`, which adds the admin pages' functions, the hold on a profile and the rules for suspended accounts. Until it is applied, `/admin`, `/admin/founders`, `/admin/people` and `/admin/audit` fail, and founders cannot reach their dashboard, because it reads the new hold columns. Its checks were run against all eight migrations on a local PostgreSQL 16 on 17 October 2026.
2. Under Authentication, URL Configuration, set the Site URL to the public address, for example `https://ikonetu.com`, and add `<that address>/auth/callback` under Redirect URLs.
3. The other Supabase Auth settings are listed in the README under "Sign-in".
4. After the first admin has signed in once, make them an admin with the SQL in the README under "The signed-in app".
5. The `pitches` bucket allows files of up to 50 MB. Whether the Supabase project applies a lower upload limit of its own was not checked (**unverified**). If it does, pitches above that limit are refused, and the founder sees that the upload did not finish.

## 2. Render

`render.yaml` at the root of the repository describes the service. It is **unverified**, because Render's schema for the file could not be read. Render checks the file when a blueprint is created from it and names any field it does not accept.

| Setting | Value |
|---|---|
| Service type | Web service, Node |
| Region | Frankfurt |
| Build command | `corepack enable && pnpm install --frozen-lockfile && pnpm --filter @ikonetu/web build` |
| Start command | `pnpm --filter @ikonetu/web start` |
| Health check path | `/` |
| Node version | 22, set through `NODE_VERSION` (**unverified** as Render's way of choosing it) |

`next start` reads the port from `PORT`. Render sets `PORT` for a web service (**unverified**).

## 3. Environment variables

Each value is entered in the Render dashboard. None is written in this repository, and none is pasted into a conversation.

| Variable | Where it is used | Notes |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | Page metadata, the site map, the sign-in email link | The public address with `https://` and no trailing slash |
| `NEXT_PUBLIC_SUPABASE_URL` | Sign-in and the signed-in pages | Safe in the browser |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Sign-in and the signed-in pages | Safe in the browser |
| `SUPABASE_SERVICE_ROLE_KEY` | `POST /api/v1/waitlist` | Server only. It bypasses row level security, so it must never be committed or sent to a browser |
| `NEXT_PUBLIC_PHONE_SIGN_IN` | The sign-in page | Leave unset until an SMS and WhatsApp provider is set up in Supabase Auth |
| `TRUSTED_PROXY_HOPS` | The waitlist's rate limit | The number of proxies in front of the app, 1 in `render.yaml`. **Unverified** for Render: see check 8 below |
| `CLIENT_IP_HEADER` | The waitlist's rate limit | Optional. A single header the edge sets with the caller's address, used instead of `X-Forwarded-For` |
| `SENTRY_DSN` | Error reports from the server | Server only. Leave unset until Sentry is named in the privacy policy; `docs/OPERATIONS.md` has the steps |
| `SENTRY_ENVIRONMENT` | Error reports | Optional, `production` unless set |

Variables whose names start with `NEXT_PUBLIC_` are written into the browser code when the app is built. A change to one of them therefore needs a new build, not only a restart. `NEXT_PUBLIC_SUPABASE_URL` must be set before the build for another reason too: the Content-Security-Policy allows the browser to upload pitches to that address and to play them from it, and the policy is fixed at build time.

## 4. The domain

The domain's DNS records point it at the Render service. Render shows the records to add when the custom domain is added to the service (**unverified**). Who holds the DNS for `ikonetu.com` was not established in the session that wrote this file.

## 5. Checks after the first deployment

1. The home page, `/privacy`, `/terms` and `/cookies` load at the public address.
2. `/robots.txt` and `/sitemap.xml` name the public address, which shows `NEXT_PUBLIC_SITE_URL` was set before the build.
3. `/investor-interest` redirects to `/for-investors`.
4. A test founder uploads a short pitch at `/dashboard/pitch` and it plays back, which shows the browser can reach Supabase Storage under the Content-Security-Policy.
5. A test investor signs up, an admin approves them at `/admin/investors`, and the investor finds the test founder at `/investor` once the founder has published.
6. A sign-in at `/signin` sends the email, and its link returns to `/auth/callback` on the public address.
7. The response headers carry the Content-Security-Policy set in `apps/web/next.config.ts`.
8. The rate limit reads the right address. Send six requests to `POST /api/v1/waitlist` from one computer, each with a different made-up `X-Forwarded-For` value, for example `curl -X POST -H 'content-type: application/json' -H 'x-forwarded-for: 10.0.0.1' -d '{}' <address>/api/v1/waitlist`. The sixth must answer 429. If it does not, the address the app reads is still the one the caller wrote, and `CLIENT_IP_HEADER` must name the header in which Render passes the caller's address. Within ten minutes, send one request from a phone on a different network. It must not answer 429. If it does, every caller shares one count, because the app is reading the address of one of Render's own proxies, and `TRUSTED_PROXY_HOPS` must be raised by one.
9. `GET /api/health` answers 200 with `"supabase":"ok"`. Point an uptime monitor at it, as `docs/OPERATIONS.md` describes.

## What the app does not need

- The fonts are downloaded when the app is built and served by the app itself, so no request goes to Google Fonts.
- The walkthrough video, its poster and the product screens are in `apps/web/public/media` and are served by the app.
- The app sets no analytics or advertising cookies.

## Health checks

Render's health check stays on `/`, which is a static page and does not depend on Supabase. `/api/health` checks Supabase and is meant for an uptime monitor, so an outage at Supabase is reported without making the app look broken to Render.

## Rate limiting

The waitlist endpoint limits each IP address in memory. It reads the address the nearest proxy added to `X-Forwarded-For`, because the start of that header is whatever the caller wrote; reading the start let a caller choose a new address for every request, which a test on 15 October 2026 confirmed. Each running instance keeps its own count, so the limit only slows casual abuse. SRD SEC-W4 asks for a limit in front of the app as well. Which of Render's features can provide it is **unverified**.
