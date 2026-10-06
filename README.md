# IkonetU platform

This repository holds the new IkonetU codebase: the web app, the score engine and the database setup. It follows the PRD, TRD and SRD written in October 2026.

## What is in it

| Folder | Contents |
|---|---|
| `apps/web` | Next.js app with the landing page, founder sign-in by emailed link, the profile and first venture form, the founder dashboard, the draft privacy notice and the `POST /api/v1/waitlist` endpoint, which no page calls since sign-up replaced the form |
| `packages/score-engine` | The IkonetU Score rules (rubric v2), the score calculation, league placement and the "next best actions" list, with tests |
| `packages/ui-tokens` | Brand colours, fonts, spacing and the 44 px touch target |
| `supabase/migrations` | Database tables, access rules (row level security), the private evidence bucket and the rubric seed |
| `supabase/tests` | SQL checks that prove the access rules work |

The mobile app (Expo), evidence upload and the rest of the signed-in founder screens come next.

## Sign-in

"Get started" leads to `/signin`. A founder enters an email, confirms they are 18 or older, and Supabase Auth sends a 6-digit code (PRD A-2, SRD SEC-A1, SEC-A9). The code is entered at `/signin/code`, which turns it into a session cookie. Between the two steps the address is kept in an HTTP-only cookie, never in the URL. The first code creates the account, so sign-up and sign-in are one step.

Phone sign-in by WhatsApp or SMS (PRD A-1) is built and switched off. It needs an SMS and WhatsApp provider configured in Supabase Auth, and then `NEXT_PUBLIC_PHONE_SIGN_IN=on` on Vercel. With it on, the phone number is asked first and email becomes the fallback, as the sign-in wireframe shows.

`/onboarding` creates the profile, records the consents (PRD A-4) and creates the first venture, and `/dashboard` shows them with the score. Every query runs as the signed-in founder, so the row level security in `supabase/migrations` decides what each one can read and write. `middleware.ts` sends anyone without a session from `/dashboard` and `/onboarding` to `/signin`. `/auth/callback` turns the link in Supabase's default email into a session. Supabase's built-in email sender does not let the templates be edited, so until IkonetU has its own email sender the email carries a link rather than the code, and the code screen tells the founder to open it on the same device. The link only works in the browser that asked for it, because the sign-in is bound to a cookie set there.

Supabase Auth needs these settings before sign-in works:

1. Under URL Configuration, the Site URL set to `NEXT_PUBLIC_SITE_URL`, and `<NEXT_PUBLIC_SITE_URL>/auth/callback` under Redirect URLs.
2. Once IkonetU has its own email sender under SMTP Settings, the "Magic Link" and "Confirm signup" email templates should show the code with `{{ .Token }}`. Until then the default email's link is used.
3. The email code lasting 300 seconds and 6 digits long (SRD SEC-A1).
4. The access token lasting 900 seconds, with refresh token rotation and reuse detection on (SRD SEC-A3).

`docs/DECISIONS.md` lists where this build departs from the PRD, TRD and SRD, and why.

## Run it

You need Node 22 and pnpm 10.

```sh
pnpm install
pnpm test          # 95 tests across the score engine and the web app
pnpm typecheck
pnpm --filter @ikonetu/web dev    # http://localhost:3000
```

Sign-in answers "not open yet" and the waitlist endpoint answers 503 until Supabase is configured. To connect it, copy `.env.example` to `apps/web/.env.local` and fill in the values from your Supabase project. The service role key must stay on the server and must never be committed.

## Rules the code enforces

- A score only counts approved evidence. Self-reported claims add nothing.
- Founders cannot approve their own evidence, change its status or give themselves staff roles. The database blocks these even if the app has a bug.
- Score history and the audit log cannot be edited after they are written.
- The waitlist cannot be read by any signed-in user. Only the server writes to it.
- The rubric in the database is generated from `packages/score-engine/src/rubric.ts`. After changing the rubric, run `pnpm --filter @ikonetu/score-engine rubric:sql`. A test fails if the two copies differ.

## Not done yet

- Sign-in has not been run end to end with a real email code, because no test inbox was available. The database writes it makes were run under row level security on a local copy of the migrations.
- The privacy notice is a draft and needs a lawyer's review before sign-up opens to the public. It now describes the account details as well as the waitlist.
- The in-memory rate limit on the waitlist only slows casual abuse. Production also needs Vercel firewall rules.
