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

"Get started" leads to `/signin`. A founder enters an email and Supabase Auth emails a link; the first link creates the account. The link returns to `/auth/callback`, which turns it into a session cookie. `/onboarding` creates the profile, records the privacy consent and creates the first venture, and `/dashboard` shows them with the score. Every query runs as the signed-in founder, so the row level security in `supabase/migrations` decides what each one can read and write. `middleware.ts` sends anyone without a session from `/dashboard` and `/onboarding` to `/signin`.

Supabase Auth needs two settings, under Authentication, then URL Configuration: the Site URL set to `NEXT_PUBLIC_SITE_URL`, and `<NEXT_PUBLIC_SITE_URL>/auth/callback` listed under Redirect URLs.

## Run it

You need Node 22 and pnpm 10.

```sh
pnpm install
pnpm test          # 77 tests across the score engine and the web app
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

- Sign-in has not been run end to end with a real email, because no test inbox was available. The database writes it makes were run under row level security on a local copy of the migrations.
- The privacy notice is a draft and needs a lawyer's review before sign-up opens to the public. It now describes the account details as well as the waitlist.
- The in-memory rate limit on the waitlist only slows casual abuse. Production also needs Vercel firewall rules.
