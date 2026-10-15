# Hosting the IkonetU web app

The website and the signed-in app are one Next.js app in `apps/web`. It runs as one web service on Render in Frankfurt, and it uses Supabase for sign-in and the database. This file lists what has to be set up, in order, before the public address serves it.

Written on 15 October 2026. Render's documentation could not be reached from the session that wrote it, so every Render detail below is marked **unverified**. The build and start commands were run as written on Node 22, and the app answered on the port given in `PORT`.

## 1. Supabase

1. Apply `supabase/migrations/20261015000001_investor_interest.sql` to the Supabase project, after the three earlier migrations. Until it is applied, the investor interest form answers "Registration is not open yet" and stores nothing. The SQL checks in `supabase/tests` were run against all four migrations on a local PostgreSQL 16 on 15 October 2026.
2. Under Authentication, URL Configuration, set the Site URL to the public address, for example `https://ikonetu.com`, and add `<that address>/auth/callback` under Redirect URLs.
3. The other Supabase Auth settings are listed in the README under "Sign-in".

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
| `SUPABASE_SERVICE_ROLE_KEY` | `POST /api/v1/waitlist` and `POST /api/v1/investor-interest` | Server only. It bypasses row level security, so it must never be committed or sent to a browser |
| `NEXT_PUBLIC_PHONE_SIGN_IN` | The sign-in page | Leave unset until an SMS and WhatsApp provider is set up in Supabase Auth |

Variables whose names start with `NEXT_PUBLIC_` are written into the browser code when the app is built. A change to one of them therefore needs a new build, not only a restart.

## 4. The domain

The domain's DNS records point it at the Render service. Render shows the records to add when the custom domain is added to the service (**unverified**). Who holds the DNS for `ikonetu.com` was not established in the session that wrote this file.

## 5. Checks after the first deployment

1. The home page, `/privacy`, `/terms` and `/cookies` load at the public address.
2. `/robots.txt` and `/sitemap.xml` name the public address, which shows `NEXT_PUBLIC_SITE_URL` was set before the build.
3. A test registration on `/investor-interest` shows the confirmation, and the row appears in `investor_interest` in Supabase.
4. A sign-in at `/signin` sends the email, and its link returns to `/auth/callback` on the public address.
5. The response headers carry the Content-Security-Policy set in `apps/web/next.config.ts`.

## What the app does not need

- The fonts are downloaded when the app is built and served by the app itself, so no request goes to Google Fonts.
- The walkthrough video, its poster and the product screens are in `apps/web/public/media` and are served by the app.
- The app sets no analytics or advertising cookies.

## Rate limiting

The waitlist and investor interest endpoints limit each IP address in memory. Each running instance keeps its own count, so the limit only slows casual abuse. SRD SEC-W4 asks for a limit in front of the app as well. Which of Render's features can provide it is **unverified**.
