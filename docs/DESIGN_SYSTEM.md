# The IkonetU design system

The owner approved this system on 21 October 2026, in the design review's steps 2 and 4. It applies to the
website and the signed-in app. Every website page was rebuilt to the approved composition on 21 and 22 October
2026 (see the end of this file).

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
| Founder message | `--founder-bubble` | #FFE3CC | ink text 14.46:1 | The founder's own messages in a conversation. Added on 26 October 2026 with the app frame |
| Founder chosen | `--founder-wash` | #FFFAF5 | ink text 17.11:1, grey text 7.41:1 | The founder card when it is chosen on Founder or investor. Added on 26 October 2026 with the sign-in screens |
| Investor action | `--investor` | #123C7A | white text 10.75:1 | Investor buttons, links, the focus ring |
| Investor tint | `--investor-tint` | #EEF4FF | investor text 9.74:1 | Investor labels and panels |
| Investor chosen | `--investor-wash` | #F7FAFF | ink text 16.96:1, grey text 7.35:1 | The investor card when it is chosen on Founder or investor. Added on 26 October 2026 with the sign-in screens |
| Google button | `--google-line`, `--google-text` | #747775, #1F1F1F | border 4.53:1, text 16.48:1 on white | Continue with Google, in the light theme of Google's sign-in asset bundle, which their branding rules require. Added on 26 October 2026 |
| Admin sidebar | `--side`, `--side-text` | #000000, #FFFFFF | 21.00:1 | The admin sidebar and its links, names and counts. Black with white text since 27 October 2026, when the owner asked for the sidebar to be black and every colour on it very bright; it was the footer navy with #B9C4D6 text |
| Admin sidebar, quiet | `--side-muted` | #E4E7EC | 16.94:1 on black | The sidebar's section names and icons. It was #8FA0BA on the navy |
| Admin sidebar, hover and counts | `--side-line` | #404040 | white text 10.37:1 | A link under the pointer, the counts beside People and the dividers |
| Admin sidebar, open page | `--side-current` | #2563EB | white text 5.17:1 | The link of the page that is open, with a white icon. It was the investor navy with an orange icon |
| Admin sidebar, accent | `--side-accent` | #FF8533 | 8.65:1 on black | The edge of the ADMIN badge and of Sign out. It was the founder orange |
| Admin sample badge | `--sample-on-dark` | #FEC84B | 13.58:1 on black | The Sample data badge in the admin sidebar, shown only while sample rows are held. Added on 27 October 2026 |
| Waiting bar | `--waiting-bar` | #F79009 | 2.35:1 on white | The bar under a count of what waits for review, as the admin boards drew it. It measures under 3:1, so it is decoration only: the card's label and number say the same thing. Added on 27 October 2026 |
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

Paragraphs are justified on every website page, as the owner chose on 22 October 2026, and hyphenated in British
English, so a line has straight edges on both sides. A paragraph in a centred block keeps its last line centred.
Headings, questions, labels, buttons, chips and table cells are never justified, and the signed-in app keeps its own
alignment. On a phone a justified line can open wide gaps between words.

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
| Example tag | `chip chip-n` reading Example | One on each showcase of made-up founders, and one on each app screen, in place of every sentence that said sample data |
| Status chip | `chip chip-n`, `chip-ok`, `chip-3p`, `chip-none` | Founder submitted, Platform reviewed, Third-party evidence available, Not added yet. Each carries its icon and its words |
| Context label | `chip chip-f`, `chip-i` | For founders, For investors, and the founder's league |
| Recency | `chip chip-n` with `dot` | A clock in the text colour. It never pulses |
| Segmented control | `seg` | The selected segment is white with `--shadow-raised`. Hover darkens the ground |
| Row that opens | `modbtn`, `areabtn` | `aria-expanded`, with a chevron that turns in 200ms |
| Header menu on a phone | `menubtn`, `hdr-nav` | `aria-expanded` and `aria-controls`. The button carries the word Menu alone, and while the menu is open it takes the pressed fill. Escape closes the menu and returns focus to the button |
| Pitch dialog | `dialog.pd` | It fades in over 150ms with its backdrop. The website's player plays captions only, so it has no loading or video error state |
| Pitch video in the app | `pitch_video.html` | A video that cannot play shows "The pitch could not be played. Try again, or read the transcript below." |
| Meter and progress strip | `rmeter`, `meter`, `ameter`, `weeks`, `wk`, `weeks-row` | Filled `--mark-on`, building `--mark-mid`, empty white with a `--mark-edge` outline. The words beside each one carry the same count |
| Product frame | `frame` | The home page's sample profile sits in it, with `--r-frame` and `--shadow-frame`. When the view changes, its status chips fade across |
| Step tabs | `tabs`, `tab`, `stage`, `shot` | A tab list over four app screens. A click or the arrow keys, Home and End choose a step, focus moves to the chosen tab, and its screen fades in over the last. On a phone the tabs sit two by two and each screen is the phone capture |
| Founder and investor panels | `side side-f`, `side side-i` | The founder tint or the investor tint, each with an app screen. Hover lifts a panel 2px with `--shadow-raised`, and under reduced motion it does not move |
| Price cards | `price-duo`, `price-side`, `price-rows` | The home page's prices: a card in each side's tint, with Free and Premium as rows of name, price and one sentence. The cards sit one above the other below 600px
| Hero | `hero-c`, `hero-solo`, `hero-note`, `acts` | The label, headline, introduction, actions and note are centred. `hero-solo` adds space below a hero that has a bordered section after it. On a phone the main action fills the width and the second sits beneath it as a link |
| Section opening | `intro-c` | The heading and a short introduction are centred over a composition. Paragraphs longer than three lines, lists, tables and forms stay start-aligned |
| Reading column | `read`, `doc`, `doc-lead`, `rows`, `risk-box`, `qa`, `faq-c` | Long text at 680px, start-aligned in the middle of the page: the legal pages, Trust and safety, the readiness check and every set of questions. A table in a legal page may run to 960px so its columns stay readable |
| Timeline | `timeline`, `timeline-3`, `num` | Numbered steps across the page, joined by a line, and down the page below 760px |
| App screen | `screen` | An app capture at 960px with its caption, and a 624 by 780 phone capture that a browser below 600px loads in its place |
| Plan card | `plan-pair`, `plan`, `plan-hi`, `feat-list`, `plan-wait` | Each side's Free and Premium side by side, one above the other below 760px. A plan shows its name and a chip, the price, one sentence of value, its action, a note and a ticked list of what it includes. Premium carries a border and a wash in its side's colour, and while it is not on sale a dashed box saying when it opens stands where its button will go. On wide screens the two cards share their rows, so the prices, the actions and the lists line up. Redesigned on 28 October 2026 |
| Trust band | `trust`, `trust-list`, `trust-art` | The pricing page's dark band under its hero, on `--ink`: a chip, a heading, one sentence, three items each with an icon tile and a chip saying when it arrives or that it is live now, and a drawing of face verification on a phone with a padlock. The drawing sits beside the text, and below it under 900px. Its text colours are the `--band` tokens, each tested at 4.5:1 on `--ink`. Added on 28 October 2026 |
| Activity feed | `act`, `act-ico`, `act-meta`, `act-plain` | One bordered list, newest first. Each entry has a round icon in `--fill`, or in the tint of its status for evidence (`act-3p` third-party, `act-ok` platform reviewed) and in the side's tint for an accepted introduction, the sentence, and a line with the sector and country, the time and, for an investor, View profile. `act-plain` drops the border on a profile's Activity card. An entry the live check adds looks the same and is announced once in a polite live region |
| Status table | `tbl legend-tbl` | Each status chip beside what it means. On a phone each row stacks, with the table's roles written into the markup |
| Showcase heading | `show-head` | A short centred title over a showcase that needs one, as on For investors |

An icon appears for one of two reasons: it marks a status, as on the status chips and the captions mark on a
pitch preview, or it is a control's only visible label, as with the play mark, a closing cross or the chevron
of a row that opens. A control that carries its own words, such as Play, Captions or Transcript, has no icon.
Every website page keeps to this. A selected filter's tick and a muted preview's mark show the state of a control,
so they stay.

## Motion

| What changes | Duration |
|---|---|
| Button, link and control colours | `--m-quick`, 150ms |
| Opening a row, the chevron, the readiness bar | `--m-open`, 200ms |
| The pitch dialog and its backdrop | `--m-quick`, a fade |
| A status chip when the sample profile changes view | `--m-quick`, a fade |
| A row's panel as it opens | `--m-open`, a fade and 4px slide |
| A step's screen replacing the last | `--m-quick`, a fade |
| A founder or investor panel under the pointer | `--m-quick`, a 2px lift |

Nothing animates when a page loads, and nothing waits for the visitor to scroll. Under the reduced motion
setting both durations are 0ms, so every change happens at once. A test allows three keyframe animations:
the dialog's fade (`pd-in`), a changed status's fade (`fade-in`) and an opened row's slide (`row-in`).

## Adding to the system

A new value goes into `tokens.css` first, with its role, and its contrast goes into `PAIRS` in the tests when it
carries text or a graphic. A rule then names the token. A test fails if a rule names a token that does not exist,
or writes a colour out.

## What is not built yet

Step 6 rebuilt the home page on 21 October 2026 and the other pages on 22 October 2026, each to the composition
the plan gave it.

Three things are not built:

- The progress strips are drawn filled. They do not fill as they come into view, because nothing on the site waits
  for the visitor to scroll.
- On the home page a pitch preview does not play on hover. For investors keeps its muted preview of the captions,
  because that page had it before.
- The website's sample pitch shows its captions over a drawn figure, because it has no video to play. The founder
  search on For investors draws the same figure on each thumbnail.
