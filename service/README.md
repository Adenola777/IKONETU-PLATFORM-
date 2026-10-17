# The IkonetU web app, in Python

This folder holds the Python rebuild of `apps/web`, which the owner asked for on 17 October 2026. It is being
built in batches, each committed on its own, and `apps/web` keeps serving until the last batch switches over.

| Batch | What it holds | State |
|---|---|---|
| 1 | The score engine, `app/score_engine` | Done. Its 47 tests pass, and a parity check found the TypeScript and Python engines agree on 2,000 generated profiles |
| 2 | The app core: sign-in, sessions, security headers, health, the waitlist | Done. 107 tests pass, and a browser signed in through the local stand-in |
| 3 | The website pages | Not started |
| 4 | The founder pages | Not started |
| 5 | The investor pages and introductions | Not started |
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

## How it differs from the Next.js app

- **The session cookies are HTTP-only.** supabase-js in the browser needed to read them, so the Next.js app could
  not make them HTTP-only. Here the server makes every Supabase call except the pitch upload, which asks the
  server for the access token just before it starts.
- **Scripts may only come from this site.** The Content-Security-Policy no longer allows inline scripts, which
  Next.js needed to start React.
- **A form sent from another site is refused.** Next.js checked this for its server actions. This app checks the
  Origin header of every form, and the session cookies are SameSite=Lax.
- **The requests to Supabase repeat what supabase-js 2.117.2 sends**, read from its source on 17 October 2026:
  the one-time code with its PKCE challenge, the code exchange, the token refresh, the REST queries and the
  storage calls. They have run against the local stand-in and against recorded replies in the tests. **They have
  not run against a real Supabase project**, which this session cannot reach.
