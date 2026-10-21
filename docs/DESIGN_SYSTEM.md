# The IkonetU design system

The owner approved this system on 21 October 2026, in the design review's steps 2 and 4. It applies to the
website and the signed-in app. The page compositions it serves are a separate step, and they are not built
yet (see the end of this file).

## Where it lives

| File | What it holds |
|---|---|
| `service/app/static/css/tokens.css` | Every colour, size, width, space, corner, shadow and timing, as CSS custom properties |
| `service/app/static/css/fonts.css` | IBM Plex Sans at 400 and 600, and the metric-matched Arial fallback |
| `service/app/static/css/site.css` | The shared components and the website's pages |
| `service/app/static/css/app.css` | What the signed-in pages add |
| `service/app/static/css/sign-in.css` | The sign-in pages |
| `service/tests/test_design_tokens.py` | The tests that hold the rules below |

`base.html` loads `tokens.css` first, then the fonts, `globals.css` and `site.css`. No stylesheet writes a colour
out except white text on a filled button and the dark ground behind a video, and a test fails if one does.
`site.css` is the source: the generator its old note named, `tools/gen_next.py`, is not in the repository.

## Colour roles

Each colour has one job. The contrast figures were measured with the WCAG formula, and a test keeps them.

| Role | Token | Value | Contrast | Used for |
|---|---|---|---|---|
| Ink | `--ink` | #101828 | 17.75:1 on white | Headings and text |
| Secondary text | `--text-2` | #475467 | 7.69:1 on white | Introductions, captions, notes |
| Neutral fill | `--fill` | #F2F4F7 | | Chips, the segmented control, hover |
| Control edge | `--line-control` | #858FA1 | 3.26:1 on white | Inputs and outline buttons |
| Divider | `--line` | #E7EAF0 | | Decoration only |
| Founder action | `--founder` | #F26B1D | dark text 5.83:1 | A fill only. As text it measures 3.05:1 on white, so it is never text |
| Founder text and tint | `--founder-text`, `--founder-tint` | #B54708, #FFF1E6 | 4.90:1 | Founder labels and panels |
| Investor action | `--investor` | #123C7A | white text 10.75:1 | Investor buttons, links, the focus ring |
| Investor tint | `--investor-tint` | #EEF4FF | investor text 9.74:1 | Investor labels and panels |
| Verified | `--verified` on `--verified-tint` | #067647 on #ECFDF3 | 5.40:1 | "Platform reviewed", and a Strong area |
| Third party | `--third-party` on `--third-party-tint` | #5925DC on #F4F3FF | 7.02:1 | "Third-party evidence available" |
| Error | `--error` on `--error-tint` | #B42318 on #FEF3F2 | 6.05:1 | Form errors, failed actions, staff danger buttons |
| Warning | `--warning` on `--warning-tint` | #93370D on #FFFAEB | 7.21:1 | Notices that need care |
| Marks | `--mark-on`, `--mark-mid`, `--mark-edge` | #344054, #858FA1, #858FA1 | 10.46, 3.26 and 3.26:1 | The readiness meter and the dated progress strip |

Three rules follow from the roles. A status never borrows a context colour, so a verified piece of evidence is
green and never investor blue. A founder's own page uses founder colours: the league chip, a chosen option and
the founder's own messages take the orange tint. A measure, such as the readiness meter, the progress strip
or the score bars, is neutral.

## Type

IBM Plex Sans is the only typeface, at 400 and 600. Seven sizes set the page text, and each moves smoothly
between its phone and desktop value.

| Token | Phone to desktop | Line height | Used for |
|---|---|---|---|
| `--t-display` | 34 to 56px | 1.08 | The page headline |
| `--t-title` | 27 to 38px | 1.15 | A section heading, and an app page's title |
| `--t-heading` | 20 to 22px | 1.3 | A sub-heading or card title |
| `--t-lead` | 18 to 20px | 1.55 | An introduction |
| `--t-body` | 17px | 1.65 | Text |
| `--t-small` | 15px | 1.5 | Captions and notes |
| `--t-label` | 13px | 1.4 | Eyebrows and chips |

Text inside components uses three fixed sizes as well: `--t-ui-xs` (12px) on thumbnails, `--t-ui-s` (14px) for
hints, errors and table text, and `--t-ui` (16px) in inputs, which keeps phones from zooming into a field.

## Widths, spacing, corners and shadows

| Token | Value | Used for |
|---|---|---|
| `--w-page` | 1200px | The header, the footer and the product showcase |
| `--w-wide` | 960px | Legends, plans, the timeline, the founder and investor panels |
| `--w-read` | 680px | Long text, questions, legal pages and forms |
| `--w-intro` | 640px | A centred introduction |
| `--s-1` to `--s-10` | 4, 8, 12, 16, 24, 32, 48, 64, 96 and 128px | All spacing |
| `--r-control` | 12px | Buttons, inputs, the segmented control's segments |
| `--r-panel` | 16px | Panels inside a frame, video and pictures, the segmented control |
| `--r-frame` | 24px | Cards, the showcase frame and dialogs |
| `--r-pill` | 999px | Chips and filter chips |
| `--r-mark` | 3px | The cells of the meter and the progress strip |
| `--shadow-raised` | 0 1px 3px | Menus, the selected segment, the search panel |
| `--shadow-frame` | 0 24px 48px | The showcase frame and dialogs |

## Components and their states

| Component | Classes | States |
|---|---|---|
| Founder button | `btn btn-f` | Hover #E05A0E (4.76:1). Pressed keeps the hover colour and sinks with an inset shadow, because a darker orange falls below 4.5:1 |
| Investor button | `btn btn-i` | Hover `--investor-hover`, pressed `--investor-press` |
| Investor outline | `btn btn-io` | Hover `--investor-tint`, pressed `--investor-tint-press` |
| Neutral outline | `btn btn-n`, `ctrl`, `menubtn` | Hover `--fill`, pressed `--fill-pressed` |
| Text link | `tlink` | Hover and pressed underline in `--investor-hover` |
| Every button | | Keyboard focus is a 3px investor-blue ring 3px outside, white on the navy footer. While a form sends, `forms.js` sets `aria-busy` and the form's own wording, such as "Sending…": the button keeps its colours and cannot be pressed. Any other disabled button is #667085 on #F2F4F7 |
| Input, select, text area | `input` | The edge is `--line-control`. Focus is the 3px ring 2px out. An error has a 2px `--error` edge and a message under the field that names what to fix, joined to it by `aria-describedby` |
| Option card | `opt` | A founder's choice takes the founder tint, an investor's the investor tint, and any other a neutral fill |
| Status chip | `chip chip-n`, `chip-ok`, `chip-3p`, `chip-none` | Founder submitted, Platform reviewed, Third-party evidence available, Not added yet. Each carries its icon and its words |
| Context label | `chip chip-f`, `chip-i` | For founders, For investors, and the founder's league |
| Recency | `chip chip-n` with `dot` | A clock in the text colour. It never pulses |
| Segmented control | `seg` | The selected segment is white with `--shadow-raised`. Hover darkens the ground |
| Row that opens | `modbtn`, `areabtn` | `aria-expanded`, with a chevron that turns in 200ms |
| Header menu on a phone | `menubtn`, `hdr-nav` | `aria-expanded` and `aria-controls`. Escape closes the menu and returns focus to the button |
| Pitch dialog | `dialog.pd` | It fades in over 150ms with its backdrop. The website's player plays captions only, so it has no loading or video error state |
| Pitch video in the app | `pitch_video.html` | A video that cannot play shows "The pitch could not be played. Try again, or read the transcript below." |
| Meter and progress strip | `rmeter`, `meter`, `ameter`, `weeks`, `wk` | Filled `--mark-on`, building `--mark-mid`, empty white with a `--mark-edge` outline. The words beside each one carry the same count |

## Motion

| What changes | Duration |
|---|---|
| Button, link and control colours | `--m-quick`, 150ms |
| Opening a row, the chevron, the readiness bar | `--m-open`, 200ms |
| The pitch dialog and its backdrop | `--m-quick`, a fade |

Nothing animates when a page loads, and nothing waits for the visitor to scroll. Under the reduced motion
setting both durations are 0ms, so every change happens at once. A test allows one keyframe animation, the
dialog's fade.

## Adding to the system

A new value goes into `tokens.css` first, with its role, and its contrast goes into `PAIRS` in the tests when it
carries text or a graphic. A rule then names the token. A test fails if a rule names a token that does not exist,
or writes a colour out.

## What is not built yet

The page compositions of the design review (a centred hero with the product showcase beneath it, the label
legend, the timeline, the context panels and the plans table) are step 6, and they wait on the owner's approval.
Until then, two headlines keep their old sizes: the home page's headline is set to 69px inside its own
template, and the readiness check's headline uses a style of its own.
