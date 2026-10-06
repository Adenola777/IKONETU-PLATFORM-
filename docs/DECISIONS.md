# Decisions that depart from the PRD, TRD and SRD

The PRD, TRD and SRD of 5 October 2026 are the specification. This file records each place where the build departs from them, who decided it, and what remains to close. When the documents are updated to match, the entry moves to "Closed".

## Open

| Date | Area | The documents say | The build does | Decided by, and what closes it |
|---|---|---|---|---|
| 6 Oct 2026 | Landing page and release plan | PRD L-1 and release 1: the landing page carries a waitlist form, and sign-up comes in release 2 | "Get started" replaces both waitlist buttons and leads to sign-up. The waitlist form is off the page. `POST /api/v1/waitlist` and the `waitlist` table remain | The owner, on 6 October. The PRD's L-1 and release plan are to be updated to match |
| 6 Oct 2026 | Sign-in by phone | PRD A-1, TRD sign-in and the wireframe: phone first, with a code by SMS or WhatsApp | Email code first. Phone sign-in is built and switched off by `NEXT_PUBLIC_PHONE_SIGN_IN` | The owner, on 6 October, because no SMS or WhatsApp provider is chosen (PRD open question). Closes when a provider is set up in Supabase and the switch is turned on |
| 6 Oct 2026 | Failed code lockout | SRD SEC-A2: five wrong codes lock the phone or email for 30 minutes, and code requests are limited to 5 an hour per address and 20 an hour per IP address | Supabase Auth's own rate limits apply. The app does not add the 30-minute lockout, because a lockout kept by the app can be bypassed by calling Supabase directly with the public key | Not decided. Needs either a Supabase Auth hook or a confirmed Supabase setting that meets SEC-A2 |
| 6 Oct 2026 | Role at sign-up | PRD A-3: a user picks founder, investor or mentor at sign-up, and investor and mentor accounts stay pending until approved | Sign-up creates founders only. The database's insert rule on `profiles` allows the founder role only | Not built yet. Needs a migration that lets a person create a pending investor or mentor profile, and the investor and mentor tables from the TRD |
| 6 Oct 2026 | Profile photo | PRD P-1: the profile includes a photo | No photo upload yet | Not built yet. Needs a storage bucket for profile photos with its own access rules |
| 6 Oct 2026 | Terms of use | The sign-in wireframe links to terms of use and the privacy notice | The sign-in page links to the privacy notice only | No terms of use exist yet. They are for the owner and counsel to write |
| 6 Oct 2026 | Where profile writes go | TRD: the apps call one API at `/api/v1`, and the API surface lists `PATCH /me`, `POST /me/consents` and `POST /ventures` | The web app writes the profile, consents and first venture through Next.js server actions, as the signed-in user, with row level security deciding each write | Acceptable under the TRD rule that only writes changing a score, Momentum or a status must go through the API. The `/api/v1` endpoints are needed before the mobile app, so both share one set of rules |

## Closed

None yet.
