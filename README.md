# IkonetU platform

This repository holds the new IkonetU codebase: the web app, the score engine and the database setup. It follows the PRD, TRD and SRD written in October 2026.

## What is in it

| Folder | Contents |
|---|---|
| `apps/web` | Next.js app with the landing page, the waitlist form, the draft privacy notice and the `POST /api/v1/waitlist` endpoint |
| `packages/score-engine` | The IkonetU Score rules (rubric v2), the score calculation, league placement and the "next best actions" list, with tests |
| `packages/ui-tokens` | Brand colours, fonts, spacing and the 44 px touch target |
| `supabase/migrations` | Database tables, access rules (row level security), the private evidence bucket and the rubric seed |
| `supabase/tests` | SQL checks that prove the access rules work |

The mobile app (Expo) and the signed-in founder screens come next.

## Run it

You need Node 22 and pnpm 10.

```sh
pnpm install
pnpm test          # 68 tests across the score engine and the web app
pnpm typecheck
pnpm --filter @ikonetu/web dev    # http://localhost:3000
```

The waitlist endpoint answers 503 until Supabase is configured. To connect it, copy `.env.example` to `apps/web/.env.local` and fill in the values from your Supabase project. The service role key must stay on the server and must never be committed.

## Rules the code enforces

- A score only counts approved evidence. Self-reported claims add nothing.
- Founders cannot approve their own evidence, change its status or give themselves staff roles. The database blocks these even if the app has a bug.
- Score history and the audit log cannot be edited after they are written.
- The waitlist cannot be read by any signed-in user. Only the server writes to it.
- The rubric in the database is generated from `packages/score-engine/src/rubric.ts`. After changing the rubric, run `pnpm --filter @ikonetu/score-engine rubric:sql`. A test fails if the two copies differ.

## Not done yet

- No Supabase or Vercel project exists yet. Nothing is deployed.
- The privacy notice is a draft and needs a lawyer's review before the waitlist opens.
- The in-memory rate limit on the waitlist only slows casual abuse. Production also needs Vercel firewall rules.
