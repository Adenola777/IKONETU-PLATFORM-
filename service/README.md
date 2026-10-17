# The IkonetU web app, in Python

This folder holds the Python rebuild of `apps/web`, which the owner asked for on 17 October 2026. It is being
built in batches, each committed on its own, and `apps/web` keeps serving until the last batch switches over.

| Batch | What it holds | State |
|---|---|---|
| 1 | The score engine, `app/score_engine` | Done. Its 47 tests pass, and a parity check found the TypeScript and Python engines agree on 2,000 generated profiles |
| 2 | The app core: sign-in, sessions, security headers, health, the waitlist | Done. 107 tests pass, and a browser signed in through the local stand-in |
| 3 | The website pages | Done. The website's functional test passed 144 of 144, as it does on the Next.js app. All twelve routes give the same visible text, title, description, canonical address and element counts as the Next.js app, with no layout shift and no sideways scroll at 320, 390 or 768 pixels |
| 4 | The founder pages | Done. Onboarding, the dashboard, the pitch, evidence, updates, the preview and the suspended page. The founder half of the product journey passes 21 of 21 checks, and a check of the actions it does not reach passes 24 of 24. With the same founder signed in to both apps on the same database, all 27 pages and refused forms compared give the same title, text and element attributes. A parity check found the two apps' form rules give the same answer on 3,600 generated inputs. 174 tests pass |
| 5 | The investor pages and introductions | Done. Investor sign-up, the waiting page, discovery with its filters and muted previews, a founder profile with the request form, the investor's profile and requests, the founder's introductions and the conversation. With the same people signed in to both apps on the same database, all 51 pages, refusals and outcomes compared read the same, apart from one page title recorded below. The interactive checks pass 19 of 19 in both apps. An investor's approval was made in SQL for these runs, because the admin pages come in batch 6. The parity check now covers 4,400 generated inputs, including the investor form and the discovery filters. 187 tests pass |
| 6 | The staff and admin pages | Not started |
| 7 | The switch-over: Render runs this app, and `apps/web` is removed | Not started |

## Run it

You need Python 3.12 or later.

```sh
cd service
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # the tests need no database, network or credentials
.venv/bin/uvicorn app.main:app --port 3000
```

The app reads the same environment variables as `apps/web`, with the same names, so the values entered on
Render keep working. `docs/HOSTING.md` lists them. The server reads them when it starts, so a change needs a
restart rather than a new build.

## The website pages

The pages in `app/templates/site/pages` were generated on 17 October 2026 from the design boards by a script
that ran in the session, beside the one that generated the Next.js views. Neither the boards nor the scripts are in
this repository. Each page is drawn in its first state, so it reads in full before any script runs. Its
`data-` attributes and `<template>` blocks carry the bindings the boards declared, and `static/js/ik/runtime.js`
keeps them in step with the page's state. The state and its handlers are in `static/js/ik/components`, ported
from the React hooks of `apps/web/components/site`. A change to a page's wording can be made in its template,
in both the drawn state and any `<template>` block that repeats it.

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
- **A form sent from another site is refused.** Next.js checked this for its server actions. This app checks the
  Origin header of every form, and the session cookies are SameSite=Lax.
- **The requests to Supabase repeat what supabase-js 2.117.2 sends**, read from its source on 17 October 2026:
  the one-time code with its PKCE challenge, the code exchange, the token refresh, the REST queries and the
  storage calls. They have run against the local stand-in and against recorded replies in the tests. **They have
  not run against a real Supabase project**, which this session cannot reach.
