# The IkonetU web app

This folder holds the IkonetU web app: the public website, sign-in, the founder and investor sides and the staff
pages, written in Python with FastAPI and Jinja2. It replaced the Next.js app in `apps/web`, as the owner asked on
17 October 2026. The rebuild was made in seven batches, each committed on its own, and the Next.js app kept serving
until the last batch removed it.

## Where things are

| Path | What it holds |
|---|---|
| `app/main.py` | The app: its middleware, error pages, static files and routes |
| `app/routes/` | One module per part: `site.py` (the website), `auth.py` (sign-in), `founder.py`, `investor.py`, `introductions.py`, `staff.py`, and `system.py` (`/api/health`, the waitlist, `robots.txt` and the site map) |
| `app/templates/` | The pages, in Jinja2. `app/shell.html` is the frame of every signed-in page |
| `app/static/` | Styles, fonts and the browser scripts. `js/ik/` runs the website's pages and `js/app/` the signed-in pages' few scripts |
| `app/public/media/` | The website's pictures and walkthrough video |
| `app/score_engine/` | The IkonetU Score rules (rubric v2), the score, league placement and the next best actions |
| `app/supabase.py` | The calls to Supabase Auth, its database and Storage |
| `app/session.py` | The session cookies, and who may open which page |
| `app/security.py` | The security headers and the check that a form came from this site |
| `app/forms.py`, `app/investor.py`, `app/staff.py`, `app/discovery.py` | The rules each form and filter applies |
| `app/product.py`, `app/jsfmt.py` | The names, statuses and wording the pages share, and the dates and numbers written as the Next.js app wrote them |
| `tests/` | The tests. They need no database, network or credentials |

## Run it

The app was built and tested with Python 3.13.16. Older versions were not tried.

```sh
cd service
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # 201 tests
.venv/bin/uvicorn app.main:app --port 3000
```

Sign-in answers "not open yet", and the waitlist endpoint answers 503, until Supabase is configured. To connect it,
copy `.env.example` from the repository's root to `service/.env`, fill in the values from your Supabase project, and
load it before starting the app with `set -a; . ./.env; set +a`. The service role key must stay on the server and
must never be committed. The app reads its settings when it starts, so a change needs a restart rather than a new
build.

The rubric in the database is generated from `app/score_engine/rubric.py`. After changing the rubric, run
`.venv/bin/python -m app.score_engine.rubric_sql` from this folder. A test fails if the two copies differ.

## How the rebuild was checked

| Batch | What it holds | State |
|---|---|---|
| 1 | The score engine, `app/score_engine` | Done. Its 47 tests pass, and a parity check found the TypeScript and Python engines agree on 2,000 generated profiles |
| 2 | The app core: sign-in, sessions, security headers, health, the waitlist | Done. 107 tests pass, and a browser signed in through the local stand-in |
| 3 | The website pages | Done. The website's functional test passed 144 of 144, as it does on the Next.js app. All twelve routes give the same visible text, title, description, canonical address and element counts as the Next.js app, with no layout shift and no sideways scroll at 320, 390 or 768 pixels |
| 4 | The founder pages | Done. Onboarding, the dashboard, the pitch, evidence, updates, the preview and the suspended page. The founder half of the product journey passes 21 of 21 checks, and a check of the actions it does not reach passes 24 of 24. With the same founder signed in to both apps on the same database, all 27 pages and refused forms compared give the same title, text and element attributes. A parity check found the two apps' form rules give the same answer on 3,600 generated inputs. 174 tests pass |
| 5 | The investor pages and introductions | Done. Investor sign-up, the waiting page, discovery with its filters and muted previews, a founder profile with the request form, the investor's profile and requests, the founder's introductions and the conversation. With the same people signed in to both apps on the same database, all 51 pages, refusals and outcomes compared read the same, apart from one page title recorded below. The interactive checks pass 19 of 19 in both apps. An investor's approval was made in SQL for these runs, because the admin pages came in batch 6. The parity check covered 4,400 generated inputs, including the investor form and the discovery filters. 187 tests pass |
| 6 | The staff and admin pages | Done. The overview, the evidence queue and decisions, investor approvals, founders and the venture view with its hold, people and roles, and the audit log. Every browser suite the Next.js app had passes against this app: the product journey 78 of 78, the admin dashboard 42 of 42 and the resilience checks 12 of 12. With the same admin and reviewer signed in to both apps, all 69 staff pages, refusals and outcomes compared read the same. The parity check covered 5,200 generated inputs, including the staff forms, the audit log's wording and the JavaScript formats. 203 tests pass |
| 7 | The switch-over | Done. `render.yaml` and the CI workflow run this app. `apps/web`, the TypeScript packages and the Node workspace are removed, and the pictures and walkthrough moved to `app/public/media`. Before the removal, the website's functional test passed 144 of 144 on both apps, the sign-in check 11 of 11, and a failure sent to a local stand-in for Sentry arrived with no cookie, token, email address or form text. After it, against this app alone, the product journey passed 78 of 78, the founder actions 24 of 24, the admin dashboard 42 of 42, the resilience checks 12 of 12, the website's functional test 144 of 144 and the sign-in check 11 of 11, with no sideways scroll at any of 36 page widths, and 201 tests pass. The two parity tests could run only while the TypeScript code existed, so they were removed with it, and their last results are in the rows above |

The browser checks and the local stand-in for Supabase they ran against (PostgreSQL 16 with the migrations,
PostgREST, and a small stand-in for Supabase Auth and Storage) are not in this repository.

## The website pages

The pages in `app/templates/site/pages` were generated on 17 October 2026 from the design boards by a script that ran
in the session, beside the one that generated the Next.js views. Neither the boards nor the scripts are in this
repository. Each page is drawn in its first state, so it reads in full before any script runs. Its `data-`
attributes and `<template>` blocks carry the bindings the boards declared, and `static/js/ik/runtime.js` keeps them
in step with the page's state. The state and its handlers are in `static/js/ik/components`, ported from the React
hooks of the Next.js app. A change to a page's wording can be made in its template, in both the drawn state and any
`<template>` block that repeats it.

## How it differs from the Next.js app

- **The session cookies are HTTP-only.** supabase-js in the browser needed to read them, so the Next.js app could
  not make them HTTP-only. Here the server makes every Supabase call except the pitch upload, which asks the
  server for the access token just before it starts.
- **Scripts may only come from this site.** The Content-Security-Policy no longer allows inline scripts, which
  Next.js needed to start React.
- **A form that saved sends the browser back to its page** with a one-time confirmation, so reloading the page
  does not send the form again. A refused form shows the page again with the errors and what was typed, as
  the React forms did. A form's request key is made by the server when the page is drawn, rather than in the
  browser after it loads, so a form sent before its script runs still carries one.
- **A web address is read by ada**, the URL parser inside Node.js (`ada-url` 4.0.0), so an address is accepted
  or refused exactly as `new URL()` did in the Next.js app.
- **A page that is not found is titled "Page not found".** When a Next.js page called `notFound()`, the
  not-found page kept that page's own title, such as "Conversation | IkonetU". Its text was the same.
- **The discovery filters fetch the new results and put them in place** of the old ones, so focus stays on
  the box that changed, as the Next.js router did.
- **Requests to Supabase carry JSON as `JSON.stringify` writes it**, so a whole number is sent as 18000
  rather than 18000.0 and a numeric column stores what it stored before.
- **Dates and numbers the staff pages show are written as Node 22 wrote them** (`app/jsfmt.py`), for example
  "Sept" for September and "17 October 2026 at 00:05" in the audit log.
- **A form sent from another site is refused.** Next.js checked this for its server actions. This app checks the
  Origin header of every form, and the session cookies are SameSite=Lax.
- **A change to a setting needs a restart, not a build.** The Next.js app wrote the `NEXT_PUBLIC_` values into
  the browser code when it was built. This app reads every setting when it starts.
- **The requests to Supabase repeat what supabase-js 2.117.2 sends**, read from its source on 17 October 2026:
  the one-time code with its PKCE challenge, the code exchange, the token refresh, the REST queries and the
  storage calls. They have run against the local stand-in and against recorded replies in the tests. **They have
  not run against a real Supabase project**, which this session cannot reach.
