# IkonetU Product Requirements Document (reconstructed)

## About this document

This document was reconstructed on 19 October 2026 at the owner's request. It is not the PRD of 5 October 2026. That original could not be found in the repository or anywhere this session can reach, so this document was written from three sources:

1. The code on `main` at commit `3473aca`, whose tree is identical to `be661d0`.
2. `docs/DECISIONS.md`, which records each place where the build departs from the PRD, TRD and SRD of 5 October 2026.
3. `README.md`, `docs/HOSTING.md`, `docs/OPERATIONS.md` and the eight database migrations in `supabase/migrations`.

It therefore describes the product as built, and not the product as first specified. Four rules apply throughout.

- A requirement ID such as **PRD A-2** appears only where the code or the documents cite it. The original wording behind each ID is unknown, except where `docs/DECISIONS.md` quotes what the original said.
- Where the build departs from the original, the departure is stated with its date and who decided it, as `docs/DECISIONS.md` records it.
- **Unverified** marks anything that has not been checked against the live service.
- Requirements the original held but the code never cites cannot be recovered from the code, so they are missing from this document.

The companion documents are `docs/TRD-reconstructed.md` and `docs/SRD-reconstructed.md`.

## 1. What is known of the original PRD

The repository records the following about the original. Nothing else of its wording survives here.

| ID | What the repository records | Where |
|---|---|---|
| Release plan | Release 1 carried the landing page and its waitlist form, and sign-up came in release 2. The core schema calls itself "release 1 and 2". | `docs/DECISIONS.md`; `core.sql:1` |
| L-1 | The landing page carries a waitlist form. | `docs/DECISIONS.md`; `core.sql:30` |
| A-1 | Sign-in is phone first, with a code by SMS or WhatsApp. | `docs/DECISIONS.md`; `routes/auth.py:75` |
| A-2 | The email carries a 6-digit code. | `docs/DECISIONS.md`; `routes/auth.py:75` |
| A-3 | A user picks founder, investor or mentor at sign-up, and investor and mentor accounts stay pending until approved. | `docs/DECISIONS.md`; `investor_side.sql:5` |
| A-4 | Onboarding records the person's consents. The original wording is unknown. | `forms.py:67`; `README.md` |
| P-1 | The profile includes a photo. | `docs/DECISIONS.md` |
| P-3, O-4 | The code cites both for the "next best actions" list. The original wording is unknown. | `score_engine/engine.py:237` |
| P-4 | The code cites it for a public, non-sensitive founder card that exposes no contact details. | `core.sql:102` |
| S-1 | The score is calculated from approved evidence only. | `score_engine/engine.py:172` |
| S-6 | A venture without approved company registration cannot score above 600. | `score_engine/rubric.py:72` |
| E-1 to E-9 | The code cites the range for evidence, under the rule that founders submit and only the server decides. | `core.sql:183` |
| E-6 | A self-declared claim earns no points. | `score_engine/rubric.py:17` |
| Open question | The original listed the choice of an SMS or WhatsApp provider as an open question. | `docs/DECISIONS.md` |

For several later choices, `docs/DECISIONS.md` says that the PRD was not checked because it was not in the repository. Those choices are the price, whether investors see the score, the readiness check, the founder's ask, notifications, the admin dashboard, hiding a profile, suspension and the north star.

## 2. Purpose

IkonetU connects early-stage founders to investors. The website's title says so, and its footer carries the line "A founder's progress, made credible." The product serves founders in Nigeria, Ghana and Kenya. Founders build a profile around a short pitch video and evidence that IkonetU reviewers check, and approved investors find them and ask for an introduction.

IkonetU Technology Limited, company number 17110122, Leicester, operates the platform. It adopted the privacy policy, the terms and the cookie policy on 15 October 2026. The terms say that access to the platform is currently free, and the app holds no payment code.

IkonetU takes no part in any investment. The investor pages say that IkonetU facilitates discovery and introductions, does not give investment advice, and does not endorse or approve any company.

## 3. People and accounts

### 3.1 Roles

| Role | What the role does today |
|---|---|
| Founder | Builds and publishes a venture profile, adds evidence, posts updates and answers introduction requests. |
| Investor | Signs up, waits for an admin's approval, then searches published founders and asks for introductions. |
| Reviewer | Is staff. A reviewer sees the overview, the founders and the evidence queue, and decides evidence. |
| Admin | Is staff. An admin does everything a reviewer does, and also approves investors, holds profiles, changes roles, suspends accounts and reads the audit log. |
| Mentor | Exists in the database only. No page serves a mentor, and an admin cannot give the role. |

Each account holds exactly one role. A new person chooses founder or investor at `/onboarding`, and the page says "Each account is either a founder account or an investor account."

### 3.2 Account states

| State | Meaning |
|---|---|
| Active | The account works normally. A founder is active from onboarding. |
| Pending | Only an investor waiting for approval is pending. A pending investor can read nothing an investor can. |
| Suspended | An admin suspended the account, or declined an investor. A suspended account can sign in but cannot change anything. |

### 3.3 Where each person lands after sign-in

A person with no profile goes to `/onboarding`. An active investor goes to `/investor`, and any other investor goes to `/investor/pending`. Anyone else who is not active goes to `/suspended`. A reviewer or admin goes to `/admin`, and a founder goes to `/dashboard`. A mentor goes to the home page, because no mentor pages exist.

### 3.4 Departure on roles (PRD A-3)

The original asked for founder, investor or mentor at sign-up, with investors and mentors pending until approved. The build offers founder or investor. Investors wait for approval at `/admin/investors`, which closed the investor half of A-3 on 15 October 2026. The mentor half stays open, because mentors need their own tables and screens.

## 4. Public website

### 4.1 Pages

The website has eleven public pages, served by the same app as sign-in. The owner chose on 15 October 2026 to host the website inside the app, and this replaces the single landing page of PRD L-1.

| Address | Page |
|---|---|
| `/` | Home |
| `/for-founders` | For founders |
| `/for-investors` | For investors |
| `/how-it-works` | How it works |
| `/readiness-check` | Readiness self-check |
| `/trust-and-safety` | Trust and safety |
| `/about` | About |
| `/questions` | Questions |
| `/privacy` | Privacy policy |
| `/terms` | Terms, including the founder and investor terms, the acceptable use policy and the pitch licence |
| `/cookies` | Cookie policy |

Every sign-up button leads to `/signin`. The seven product pictures are screens of this app, captured with sample founders against a local test database and labelled as sample data. The About page still shows placeholders for the founders' names, roles and photos, and the privacy policy still shows a placeholder for the ICO registration number.

### 4.2 Readiness self-check

The self-check asks eight questions, one for each readiness area. A visitor answers each with "Not yet", "Partly" or "Yes, and I can show it". The page says "Nothing you choose is saved or sent, and you do not need an account." The form has no action, so nothing leaves the browser.

### 4.3 Waitlist and investor interest

The owner replaced both waitlist buttons with "Get started" on 6 October 2026, and the waitlist form left the page. `POST /api/v1/waitlist` and the `waitlist` table remain, but no page calls the endpoint. The investor interest form was retired on 15 October 2026, when investor accounts opened. `/investor-interest` now redirects to `/for-investors`, and the `investor_interest` table keeps the rows it holds. The people on that list have not been told that accounts are open, because IkonetU has no email sender.

## 5. Sign-in and onboarding

### 5.1 Sign-in (PRD A-1, A-2)

Sign-in and sign-up are one step. A person enters an email address and ticks "I am 18 or older.", and Supabase Auth sends a message. The first code creates the account. The reply is the same whether or not the address already has an account.

| Rule | As built |
|---|---|
| Email | It must be valid and at most 160 characters. |
| Age | The "I am 18 or older." tick is required, and it is stored on the account, so onboarding does not ask again. |
| Code | It is exactly 6 digits, and spaces are ignored. The code page counts down from 5 minutes. |
| Link | Supabase's default email carries a sign-in link that returns to `/auth/callback`. The link works only in the browser that asked for it. |
| Wrong code | The page says "That code is wrong or has expired." |
| Too many requests | The page shows Supabase's refusal as "Too many codes were requested" or "Too many attempts". |

Two departures apply. The owner chose email first on 6 October 2026, because no SMS or WhatsApp provider is chosen. Phone sign-in by WhatsApp, with SMS on request, is built and switched off by `NEXT_PUBLIC_PHONE_SIGN_IN`. The email carries a link rather than a code, because Supabase's built-in sender does not allow the templates to be edited. That closes when IkonetU has its own sender and the templates show the code.

**Unverified**: sign-in has not been run end to end with a real email code.

### 5.2 Choosing founder or investor

A new person sees "How will you use IkonetU?" with two choices: "I am a founder" and "I am an investor". The investor card says that an IkonetU admin checks each investor account before it can browse.

### 5.3 Founder onboarding (PRD A-4)

The form says: "Nobody sees your profile until you publish it, and then only approved investors see it. Nobody else can see your email or phone number."

| Field | Rule |
|---|---|
| Full name | 2 to 120 characters |
| Country | Nigeria, Ghana or Kenya. The venture takes the founder's country. |
| City | Optional, up to 80 characters |
| University or institution | Optional, up to 120 characters |
| Student or graduate status | Optional, up to 80 characters |
| Short bio | Optional, up to 600 characters |
| Venture name | 1 to 120 characters |
| Sector | Fintech, Agritech, Edtech, Health or Other |
| Stage | Idea, First version, Earning revenue or Scaling |
| What it does | Optional, up to 280 characters |
| The ask | Optional, empty or 5 to 160 characters |
| Website, LinkedIn, X, Instagram | Optional, up to 200 characters each, http or https |

The form offers two optional choices under "Your choices": checking the evidence the founder submits, and notifications. Every answer, including a no, is stored with the policy version of 15 October 2026. A "profile" consent is always recorded as granted. The founder must tick "I have read the privacy policy." The owner removed the registry and bank check choices on 17 October 2026, because those checks are not built.

LinkedIn, X and Instagram are stored and never shown or editable.

## 6. Founder requirements, as built

### 6.1 The venture

A founder has one venture, and the app always uses the first one. The founder edits the name, sector, stage, description, ask and website on the dashboard. The website may be up to 300 characters there, against 200 at onboarding. The country and the social links cannot be changed. A sector stored before the fixed list existed is shown with a request to choose the closest.

### 6.2 The ask

The ask is an optional line of 5 to 160 characters that says how much the founder is raising and what for. Investors see it on the profile and on the discovery card, and staff see it on the venture page. The owner added it on 15 October 2026.

### 6.3 Publishing

A profile is hidden until the founder publishes it. "Hide my profile" takes it out of search at once. The database refuses to publish in two cases: when the venture has no pitch, and while IkonetU holds the profile. Both rules apply when a venture is created as well as when it changes.

The profile leaves investors' view automatically in four cases:

1. The founder removes the pitch.
2. An admin holds the profile.
3. An admin suspends the founder.
4. An admin makes the founder a reviewer or an admin.

Lifting a hold or ending a suspension does not republish the profile. The founder publishes it again.

### 6.4 Readiness check

The readiness check covers eight areas: Identity, Legal, Financial, Product, Market, Team, Media and presence, and Operations. They are the score engine's categories. An area is **strong** when it holds platform-reviewed or third-party evidence, **building** when it holds founder-submitted evidence only, and a **gap** when it holds none. The owner set this rule on 15 October 2026. The website, the founder's dashboard and the investor's view use the same rule and read the same data.

### 6.5 The next three steps (PRD P-3, O-4)

The dashboard shows three steps that would strengthen the profile most. They come from the score engine's next best actions across all 23 evidence types, and they leave out any type whose evidence already waits for a reviewer. Each step links to the evidence form and says why it matters. No points are shown.

### 6.6 Pitch

| Rule | As built |
|---|---|
| Format | MP4, WebM or MOV |
| Size | Up to 50 MB |
| Length | More than 0 and up to 90 seconds |
| Transcript | Required, 20 to 2,000 characters |
| Captions | Made from the typed transcript and timed by the length of each sentence. Viewers are told the captions may run a little ahead of or behind the speech. |
| Playback | Through signed links that last one hour |

The browser reads the video's length and uploads it straight to the founder's folder in the private `pitches` bucket. A new pitch replaces the old one and deletes the old file. The founder can change the transcript alone. Without JavaScript the page cannot send a video.

### 6.7 Evidence (PRD E-1 to E-9)

A founder adds evidence of one of the 23 types of rubric v2.

| Area | Evidence types |
|---|---|
| Identity | Company registration matched to the founder; government ID verified; months operating |
| Legal | Tax registration; legal documents such as IP filings, contracts or licences |
| Financial | Verified revenue for the last 12 months; months of verified financial records; a verified business bank or mobile money account; verified financial statements |
| Product | Product stage with evidence; customer evidence such as signed orders or usage data |
| Market | Documented customer interviews; signed pilot or intent letters; a market research document |
| Team | Verified team members; verified team credentials; student or graduate status verified; a recognised programme completed |
| Media | Live website, checked automatically; a verified social profile; a one-pager or pitch deck; verified press coverage |
| Operations | Operational evidence such as supplier contracts, premises or tools |

Each piece of evidence carries a description of 10 to 280 characters and either up to three files or a link of up to 300 characters. Each file is a PDF, JPEG or PNG of up to 10 MB. Only the founder and IkonetU reviewers can open the files, and investors never see them. No route lets a founder edit or delete evidence. "Live website, checked automatically" is a label only, because no automatic check exists.

The founder sees each item's state:

| State | The founder reads | Investors see |
|---|---|---|
| Approved from a government record or another outside source | "Approved from an outside source." | Third-party evidence available |
| Approved by a reviewer | "Approved by an IkonetU reviewer." | Platform reviewed |
| Waiting | "Waiting for a reviewer." | Founder submitted |
| Needs more | The reviewer's request, and a note that investors do not see the item | Nothing |
| Rejected | "Not accepted. Investors do not see this item." | Nothing |
| Expired | "Expired. Investors no longer see this item." | Nothing |

The founder also sees "What the reviewer compared:" and "The reviewer said:".

### 6.8 Progress updates

An update is 10 to 600 characters. The founder can remove one. The page says that updates show investors the founder is still building, and that "Updates never rank you against anyone." Investors see the latest 20.

### 6.9 Momentum

The investor's view shows Momentum: how long ago the profile changed, the updates in the last 90 days, the evidence added in the last 90 days, and a strip of the last 13 weeks. It says "There are no streaks, points or ranks."

### 6.10 Preview

The founder can see the profile exactly as approved investors see it, with a banner that says whether it is published.

### 6.11 Hold

When an admin holds a profile, the dashboard gives the date, the admin's reason and info@ikonetu.com as the contact. The founder cannot publish until an admin lifts the hold.

### 6.12 Suspension

A suspended founder lands on `/suspended`. The page says that investors cannot see the profile, and that the founder cannot change it, answer introductions or send messages.

## 7. Investor requirements, as built

### 7.1 Sign-up and approval (PRD A-3)

| Field | Rule |
|---|---|
| Full name | 2 to 120 characters |
| Investor type | Individual investor, angel investor or fund investor |
| Fund or firm | Up to 120 characters, required for a fund investor |
| Website or LinkedIn | Optional, up to 200 characters |
| Based in | Nigeria, Ghana, Kenya or somewhere else |
| Sectors | At least one of the five sectors |
| Stages | Optional, any of the four stages |
| Countries | Optional, any of the three countries |
| Typical cheque size | Under $25,000; $25,000 to $100,000; $100,000 to $500,000; over $500,000; or prefer not to say |
| What you look for | Optional, up to 600 characters. Founders never see it. |

The investor must confirm that the chosen type is true and that they will not misrepresent their type, capacity, regulatory status or affiliation. An optional tick agrees to email about the account, which IkonetU does not send yet. The account then waits at `/investor/pending` until an admin approves or declines it. A declined or suspended investor sees "Your investor account is not approved".

### 7.2 Discovery

An approved investor searches published founders by sector, stage, geography, evidence and last update. The evidence filter offers "Revenue reviewed", "Registry record" and "Any reviewed evidence". The last update filter offers any time, 30 days or 90 days. Choices inside one filter widen the list, and filters in different groups narrow it. Results are sorted by company name and never by a score. A page holds 24 founders.

Each card shows the pitch thumbnail, which plays a muted five-second preview with captions, the venture and founder, the place, sector and stage, the updates in 90 days, the description, the ask and the readiness meter. Only published ventures of active founders appear.

### 7.3 Founder profile

The profile shows the pitch with captions and transcript, the description and bio, the ask, the website, the readiness check area by area, Momentum and the latest 20 updates. Each piece of evidence shows one of three statuses and what that status means:

| Status | What it means, as the page says |
|---|---|
| Third-party evidence available | An outside source backs it. The outside source has not assessed the company. |
| Platform reviewed | An IkonetU reviewer compared it with its source. A review is not an audit, a valuation or an endorsement. |
| Founder submitted | IkonetU has not checked it. Treat it as the founder's own statement. |

Investors never see the files, the reviewer, the reason, rejected or expired items, items needing more, or the score.

### 7.4 Asking for an introduction

The investor writes a note of 20 to 600 characters saying why they want to talk. The founder sees the note with the investor's name, type and firm. Three limits apply, chosen during the build on 15 October 2026:

1. An investor may send ten requests in a rolling 24 hours, whatever their outcome.
2. An investor may hold one pending, accepted or declined request per venture. A declined request is final, and a withdrawn one can be sent again.
3. The venture must be published.

An investor can withdraw a request while it is pending. The investor's list shows each request as waiting, accepted, declined or withdrawn.

### 7.5 Profile edit

An investor can change the same details later. A request already sent keeps the details it was sent with.

## 8. Introductions and conversations

The founder sees requests under "Waiting for your answer", "Conversations" and "Closed", and accepts or declines without giving a reason. The page says that accepting opens a conversation on IkonetU, shares no email or phone number, and does not mean the investor will invest.

An accepted request opens a conversation that only the founder and the investor can read. Staff see counts only. A message is 1 to 2,000 characters, cannot be edited or deleted, and appears when the page reloads. Each side can report the conversation through a link that opens an email to info@ikonetu.com with the conversation's reference filled in, because IkonetU has no email sender.

## 9. Staff requirements, as built

### 9.1 Overview

The overview at `/admin` shows counts only. It shows evidence waiting and the age of the oldest item, investors waiting, scores to update, the north star, introductions by status for the last 30 days, and the counts of founders, ventures, investors, staff, suspended accounts and the two lists.

### 9.2 The north star

The overview counts introductions a founder accepted when their profile already held evidence that an IkonetU reviewer or an outside source had confirmed. It shows the last 30 days and each of the last six months. This definition was proposed on 16 October 2026, and the owner has not set a north star, so it changes when the owner sets one.

### 9.3 Evidence review

The queue lists waiting evidence, oldest first. A reviewer opens files through links that last five minutes and is warned when the same file is attached to other evidence. Nobody can decide evidence on their own venture.

| Decision | What it needs |
|---|---|
| Approve | A lane (platform reviewed, a government record, or another outside source), a note of 5 to 280 characters that investors read, and a figure where the evidence type needs one |
| Ask for more | A reason of 5 to 600 characters that the founder reads |
| Reject | A reason of 5 to 600 characters that the founder reads |

Each decision goes to the audit log, and the founder's score is recomputed with up to three attempts. A score that still fails appears under "Scores to update".

### 9.4 Investors (admins only)

Admins approve, decline or suspend investor accounts. The page asks admins to check that the person, and any fund or firm named, exist. Decline and suspend both set the account to suspended, and an admin can approve it later.

### 9.5 Founders and ventures

Staff can list every venture with search and a filter for published, unpublished and hidden. The venture page shows who can see the profile, all evidence in every state, the latest updates, the founder, the pitch, the ask, the score and the introductions by status.

### 9.6 Holding a profile (admins only)

An admin holds a profile with a reason of 5 to 280 characters, which the founder reads. The owner chose "Yes, with a reason" on 17 October 2026. Investors with an accepted introduction keep their conversation.

### 9.7 People, roles and suspension (admins only)

Admins list every account with its email address and last sign-in, change a person's role, and suspend or reactivate an account. A suspension needs a reason of 5 to 280 characters and sends no email. Nobody can change their own role or status. A person becomes a founder only with a venture, and an investor only with investor details. The first admin is made with SQL. Reviewers do not see email addresses.

### 9.8 Audit log (admins only)

The audit log lists every staff decision, newest first, with who made it, what changed and the reason. Nobody can change or remove an entry.

## 10. IkonetU Score

The score engine still records a score from 0 to 1,000 with four leagues: Early, Rising, Investable and Elite. Only approved, unexpired evidence counts (PRD S-1). A self-declared claim earns nothing (PRD E-6). A venture without approved company registration cannot score above 600 (PRD S-6).

The owner chose on 15 October 2026 that investors see evidence by area and never a score, a league or a ranking. On 17 October 2026 the owner approved removing the score from the founder's dashboard as well. Staff see the score on the venture page with the words "Investors never see it." The database lets the founder read their own score, but no page shows it. The full rules are in `docs/TRD-reconstructed.md`.

## 11. Notifications and email

IkonetU sends no email or message. A founder learns of a request, and an investor of an answer, by signing in. The onboarding and investor sign-up forms record whether the person agrees to notifications for when a sender exists. This closes when IkonetU has its own email sender.

## 12. Not built, switched off or deferred

| Item | State |
|---|---|
| Phone sign-in (PRD A-1) | Built and switched off. It needs an SMS and WhatsApp provider. |
| The code in the email (PRD A-2) | The email carries a link until IkonetU has its own sender. |
| Mentor role (PRD A-3) | No pages exist, and the role cannot be given. |
| Profile photo (PRD P-1) | Not built. It needs a storage bucket with its own access rules. |
| Notifications | Not sent. |
| Registry and bank checks | Not built. The database still accepts their consents. |
| Automatic website check | Not built. The evidence type exists as a label. |
| AI evidence checks | Not built. The lanes exist in the database, and no screen sets them. |
| Evidence expiry | The status and date exist and are shown, and nothing in the app sets them. |
| Editing or deleting evidence | Not built. |
| More than one venture per founder | Not built. |
| Showing social links | Not built. |
| Account deletion in the app | Not built. An account is deleted on request to privacy@ikonetu.com. |
| Live messages | Not built. Messages appear on reload. |
| Exporting staff lists | Not built. |
| Mobile app | Not built. The README says the Expo app comes next. |
| Payments | None. Access is free. |

## 13. Open decisions recorded in `docs/DECISIONS.md`

| Area | What is open |
|---|---|
| Evidence consent | Nothing reads the founder's answer to "Check the evidence I submit". The owner must decide whether to enforce it or make checking part of the service and drop the choice. |
| North star | The owner has not set one. |
| Email addresses on staff pages | Whether the privacy policy covers admins seeing email addresses is the owner's to confirm. |
| Error tracking | Sentry is built and off. It closes when the privacy policy names Sentry and the key is set. |
| Mentors | Mentors need their own tables and screens. |
| Profile photo | Not built. |
| Email sender | Several items close when IkonetU has its own sender: the code in the email, notifications, and telling the investor interest list. |
| Landing page and release plan | The PRD's L-1 and release plan are to be updated to match the build. |
| Hosting and language | The TRD is to be updated to name Render and Python. |
