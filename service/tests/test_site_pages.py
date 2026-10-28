"""The ten website pages: each answers with its own title, description and canonical address."""

from __future__ import annotations

import html
import mimetypes
import re
from pathlib import Path

import pytest

from app.pages import PUBLIC_PAGES

INTERACTIVE = {"home", "founders", "investors", "readiness"}
APP = Path(__file__).resolve().parents[1] / "app"


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_each_page_carries_its_own_head(client, key):
    page = PUBLIC_PAGES[key]
    r = client.get(page["path"])
    assert r.status_code == 200
    title = page["title"] if key == "home" else f"{page['title']} | IkonetU"
    assert f"<title>{title}</title>" in r.text
    description = html.escape(page["description"]).replace("&#x27;", "&#39;")
    assert f'<meta name="description" content="{description}">' in r.text
    canonical = "http://localhost:3000" + ("" if page["path"] == "/" else page["path"])
    assert f'<link rel="canonical" href="{canonical}">' in r.text
    assert 'name="robots"' not in r.text


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_each_page_has_one_main_and_a_header_that_starts_in_the_browser(client, key):
    body = client.get(PUBLIC_PAGES[key]["path"]).text
    assert body.count('id="main"') == 1
    assert 'data-component="header"' in body
    assert '<script type="module" src="/static/js/ik/boot.js"></script>' in body
    slug = re.search(r'class="site pg-([a-z]+)"', body).group(1)
    assert ('data-component="%s"' % slug in body) == (slug in INTERACTIVE)


def test_the_generated_pages_hold_no_jinja_left_to_fill(client):
    # Each page body sits in a raw block, so the board's {{holes}} reach the browser untouched.
    body = client.get("/").text
    assert 'data-a="{&quot;class&quot;: &quot;c7 {{tour.evidence}}&quot;}"' in body


def test_the_not_found_page_has_the_site_header_and_footer(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert 'data-component="header"' in r.text and "<footer" in r.text


@pytest.mark.parametrize("old,new", [("/how-it-works", "/"), ("/about", "/"), ("/questions", "/for-founders")])
def test_the_pages_removed_on_21_october_redirect(client, old, new):
    r = client.get(old)
    assert (r.status_code, r.headers["location"]) == (308, new)


# Lines the copy audit of 21 October 2026 removed from the marketing pages: a slogan with no verb, the placeholders
# of the About page, and claims that the IkonetU Score makes untrue. The legal pages were outside the audit.
RETIRED_COPY = ["made credible", "[NAME]", "[TO CONFIRM", "of 8 areas", "eight areas", "eight questions", "no total and no rank",
                "no streaks, points", "Nobody competes", "Build visibly", "Most founders start here", "walkthrough"]


@pytest.mark.parametrize("key", ["home", "founders", "investors", "trust", "readiness"])
def test_no_marketing_page_carries_the_copy_the_audit_removed(client, key):
    text = html.unescape(re.sub(r"<[^>]+>", " ", client.get(PUBLIC_PAGES[key]["path"]).text))
    assert [line for line in RETIRED_COPY if line.lower() in text.lower()] == []


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_no_page_shows_a_placeholder(client, key):
    # The privacy policy showed "ICO registration number [TO CONFIRM]" until 21 October 2026, when the owner
    # removed the line.
    text = html.unescape(re.sub(r"<[^>]+>", " ", client.get(PUBLIC_PAGES[key]["path"]).text))
    assert re.findall(r"\[(?:TO CONFIRM|NAME|ROLE)[^\]]*\]", text) == []


def test_the_self_check_and_the_samples_count_the_eleven_areas_of_the_score(client):
    assert "of 11</p>" in client.get("/readiness-check").text
    assert client.get("/for-investors").text.count(" of 11 areas, building in") == 7
    assert "Strong in 5 of 11 areas" in client.get("/").text


def test_trust_and_safety_says_what_the_score_is_and_that_investors_do_not_see_it(client):
    body = client.get("/trust-and-safety").text
    assert "The IkonetU Score is a number from 0 to 1,000" in body and "Investors do not see it." in body


# The legal pack of 21 October 2026.
LEGAL = ["privacy", "terms", "cookies", "complaints"]


def _text(client, path):
    # Runs of whitespace collapse to one space, as a browser renders them.
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", client.get(path).text)))


def test_the_cookie_policy_names_every_cookie_and_storage_item_the_code_sets(client):
    # Read from the code, so a new cookie fails this test until the policy names it.
    from app.session import ACCESS_COOKIE, REFRESH_COOKIE
    from app.signin import PENDING_COOKIE, VERIFIER_COOKIE
    from app.web import FLASH_COOKIE
    side = re.search(r'const KEY = "([^"]+)"', (APP / "static/js/ik/side.js").read_text()).group(1)
    body = client.get("/cookies").text
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, PENDING_COOKIE, VERIFIER_COOKIE, FLASH_COOKIE, side, "__cf_bm"):
        assert f"<td>{name}</td>" in body, name
    assert "pixels" not in body


def test_the_privacy_policy_names_a_privacy_contact_and_the_processors_the_app_uses(client):
    text = _text(client, "/privacy")
    assert "Data Protection Officer" not in text and "We have not appointed a data protection officer." in text
    assert "Supabase" in text and "Render" in text
    # Sentry is named in the policy before SENTRY_DSN is set (app/log.py), and it is not set yet.
    assert "Sentry" not in text
    for gone in ("buttons clicked", "payment providers", "pixels"):
        assert gone not in text


def test_the_privacy_policy_explains_the_score_as_profiling(client):
    text = _text(client, "/privacy")
    assert "Data protection law calls this profiling." in text and "Investors do not see it" in text


@pytest.mark.parametrize("anchor", ["terms-use", "terms-founder", "terms-investor", "terms-aup", "risk"])
def test_the_terms_keep_the_anchors_other_pages_link_to(client, anchor):
    assert f'id="{anchor}"' in client.get("/terms").text


def test_the_investor_terms_set_the_condition_for_investors_in_the_united_kingdom(client):
    text = _text(client, "/terms")
    assert "If you are in the United Kingdom, we approve your account only after you give us one of the following." in text
    assert "Statement for investors in the United Kingdom" in text


def test_founders_opt_in_before_their_pitch_is_used_in_marketing(client):
    assert "only if you agree to that use in writing" in _text(client, "/terms")


@pytest.mark.parametrize("key", LEGAL)
def test_each_legal_page_links_to_the_other_three(client, key):
    body = client.get(PUBLIC_PAGES[key]["path"]).text
    nav = re.search(r'<nav aria-label="Legal pages" class="legalnav">(.*?)</nav>', body).group(1)
    assert re.findall(r'href="([^"]+)"', nav) == ["/privacy", "/terms", "/cookies", "/complaints"]
    assert f'href="{PUBLIC_PAGES[key]["path"]}" aria-current="page"' in nav


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_every_footer_links_to_reporting_and_complaints(client, key):
    assert '<a class="flink" href="/complaints">Complaints</a>' in client.get(PUBLIC_PAGES[key]["path"]).text


@pytest.mark.parametrize("key", LEGAL)
def test_no_legal_page_uses_a_dash(client, key):
    text = _text(client, PUBLIC_PAGES[key]["path"])
    main = text[text.index("Skip to content"):]
    assert re.findall("[\u2012\u2013\u2014\u2015]", main) == []


# The owner's ruling of 21 October 2026: the website runs from pitch to introduction, verification is the paid part,
# no line promises that a reviewer will check something, and no sentence takes the form "it is this, it is not that".
MARKETING = ["home", "founders", "investors", "trust", "readiness"]
SCRIPTS = ["home", "founders", "investors", "readiness"]
CONTRAST = re.compile(r"\b(it is not|this is not|is not an?|isn't|does not mean|rather than|instead of|says nothing)\b", re.IGNORECASE)


def _script_text(name):
    return " ".join(re.findall(r'"((?:[^"\\]|\\.){12,})"', (APP / f"static/js/ik/components/{name}.js").read_text()))


@pytest.mark.parametrize("key", [*MARKETING, "pricing"])
def test_no_marketing_page_promises_a_reviewer_check_or_uses_a_contrast_sentence(client, key):
    text = _text(client, PUBLIC_PAGES[key]["path"])
    assert "reviewer" not in text.lower()
    assert CONTRAST.findall(text) == []


@pytest.mark.parametrize("name", SCRIPTS)
def test_no_page_script_promises_a_reviewer_check_or_uses_a_contrast_sentence(name):
    text = _script_text(name)
    assert "reviewer" not in text.lower()
    assert CONTRAST.findall(text) == []


# The owner set the prices on 21 October 2026. Every page that states a price states one of these two.
PRICES = {"$5 a month", "$29 a month"}


@pytest.mark.parametrize("key", [*MARKETING, "pricing", "terms"])
def test_every_page_that_states_a_price_states_the_owners_prices(client, key):
    text = _text(client, PUBLIC_PAGES[key]["path"])
    assert set(re.findall(r"[£$€]\s?\d+(?:\.\d\d)? (?:a|per) (?:month|year)", text)) <= PRICES


def test_the_pricing_page_has_two_plans_for_each_side_and_says_premium_is_not_on_sale(client):
    text = _text(client, "/pricing")
    for plan in ("Founder Free", "Founder Premium", "Investor Free", "Investor Premium"):
        assert plan in text
    assert "$5 a month" in text and "$29 a month" in text
    assert "Premium goes on sale in December 2026. Nobody is charged today." in text
    for path in ("/", "/for-founders", "/for-investors", "/trust-and-safety", "/terms"):
        assert "Premium is not on sale yet" in _text(client, path), path


# The owner set Premium's opening for December 2026 on 28 October 2026. The pricing page says so in its opening
# note, on both Premium cards and in its answer on when Premium can be bought.
def test_the_pricing_page_says_premium_opens_in_december_2026(client):
    text = _text(client, "/pricing")
    assert "Premium goes on sale in December 2026. Nobody is charged today." in text
    assert text.count("Premium opens in December 2026.") == 2
    assert "Premium goes on sale in December 2026, together with face verification and anti-money-laundering checks." in text
    assert "payments are ready" not in text and "can take payments" not in text


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_every_header_links_to_pricing(client, key):
    body = client.get(PUBLIC_PAGES[key]["path"]).text
    assert '<a class="navlink" href="/pricing"' in body and '<a class="flink" href="/pricing">Pricing</a>' in body


def test_the_tour_music_waits_for_the_visitor(client):
    body = client.get("/").text
    assert '<audio data-ref="audioRef" src="/media/tour-music.mp3" preload="none" loop></audio>' in body
    assert "autoplay" not in body
    r = client.get("/media/tour-music.mp3")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"


def test_screens_and_fonts_carry_their_types_without_the_systems_list(client, monkeypatch):
    # On Vercel, Python 3.12 runs with no /etc/mime.types, so only Python's own table and the app's names apply.
    from app import main

    monkeypatch.setattr(mimetypes, "knownfiles", [])
    mimetypes.init()
    try:
        main.name_file_types()
        assert client.get("/media/screen-pitch.webp").headers["content-type"] == "image/webp"
        assert client.get("/static/fonts/ibm-plex-sans-latin-400-normal.woff2").headers["content-type"] == "font/woff2"
    finally:
        monkeypatch.undo()
        mimetypes.init()
        main.name_file_types()


# The owner's ruling of 21 October 2026: IkonetU is for student founders in any country.
@pytest.mark.parametrize("key", [*MARKETING, "pricing"])
def test_no_marketing_page_limits_founders_to_three_countries(client, key):
    text = _text(client, PUBLIC_PAGES[key]["path"])
    assert "Nigeria, Ghana and Kenya" not in text and "Nigeria, Ghana or Kenya" not in text


def test_the_website_says_ikonetu_is_for_student_founders_in_any_country(client):
    assert "For student founders" in _text(client, "/")
    assert "<title>IkonetU | Connecting student founders to investors</title>" in client.get("/").text
    founders = _text(client, "/for-founders")
    assert "Student founders aged 18 or over can join from any country." in founders
    assert "or graduated from one in the last three years." in founders
    assert "Student founders aged 18 or over join free, from any country." in _text(client, "/pricing")


def test_the_founder_terms_and_the_privacy_policy_state_the_student_founder_rule(client):
    terms = _text(client, "/terms")
    assert "IkonetU is for student founders." in terms and "You can be in any country." in terms
    assert "based in Nigeria, Ghana or Kenya" not in terms
    assert "when you confirmed being a student founder" in _text(client, "/privacy")


# The owner chose IBM Plex Sans on 21 October 2026 in place of Fraunces and Plus Jakarta Sans.
def test_every_font_the_site_names_is_ibm_plex_sans_and_is_served(client):
    css = re.sub(r"/\*.*?\*/", "", client.get("/static/css/fonts.css").text, flags=re.DOTALL)
    assert "Fraunces" not in css and "Jakarta" not in css
    assert set(re.findall(r'font-family:"([^"]+)"', css)) == {"IBM Plex Sans", "IBM Plex Sans Fallback"}
    for path in set(re.findall(r"url\((/static/fonts/[^)]+)\)", css)):
        assert client.get(path).status_code == 200, path
    preloads = re.findall(r'<link rel="preload" href="(/static/fonts/[^"]+)"', client.get("/").text)
    assert preloads == ["/static/fonts/ibm-plex-sans-latin-400-normal.woff2", "/static/fonts/ibm-plex-sans-latin-600-normal.woff2"]
    assert all(client.get(p).status_code == 200 for p in preloads)
    assert "SIL OPEN FONT LICENSE" in client.get("/static/fonts/IBM-Plex-Sans-LICENSE.txt").text.upper()


# The owner's answers of 21 October 2026 on the rebuilt home page: centred openings, larger app screens as the only
# pictures, and icons only where they mark a status or are a control's only label.
HOME_ICONS = {"shield-check", "link", "upload", "circle-dashed", "circle-check", "circle-alert", "clock", "captions", "play",
              "chevron-down", "x"}


def test_the_home_page_centres_its_hero_and_the_opening_of_each_section(client):
    body = client.get("/").text
    assert '<section aria-labelledby="hero-title" class="hero-c">' in body
    assert '<div class="wrap intro-c"><h2 id="why-title" class="h2">Investors back what they can check.</h2>' in body
    css = (APP / "static" / "css" / "site.css").read_text()
    assert ".site .hero-c{padding-top:clamp(40px,6vw,88px);text-align:center}" in css
    assert ".site .intro-c{display:flex;flex-direction:column;align-items:center;text-align:center}" in css


def test_the_home_page_pictures_are_app_screens_with_a_phone_capture_for_each(client):
    body = client.get("/").text
    pictures = re.findall(r'<picture><source media="\(max-width: 599px\)" srcset="(/media/phone-[a-z]+\.webp)"[^>]*>'
                          r'<img src="(/media/screen-[a-z]+\.webp)"', body)
    assert [p[0].split("-")[1] for p in pictures] == [p[1].split("-")[1] for p in pictures]
    assert {p[0][len("/media/phone-"):-len(".webp")] for p in pictures} == {"pitch", "evidence", "score", "intro", "next", "discover"}
    for phone, desktop in pictures:
        assert client.get(phone).headers["content-type"] == "image/webp", phone
        assert client.get(desktop).headers["content-type"] == "image/webp", desktop
    assert body.count("<img ") == len(pictures)


def test_the_home_page_has_no_decorative_icons(client):
    body = client.get("/").text
    assert set(re.findall(r'class="lucide lucide-([a-z-]+)"', body)) <= HOME_ICONS
    for label in ("Captions", "Transcript"):
        assert f'</svg>{label}</button>' not in body, label
    assert '<button type="button" class="ctrl" data-on="click:togglePlay"><ik-t data-t="playLabel">Play</ik-t></button>' in body


def test_the_home_page_explains_the_evidence_labels_once(client):
    assert _text(client, "/").count("The founder added it, and IkonetU has not verified it yet.") == 1


def test_the_home_page_sets_its_plans_as_a_card_for_each_side(client):
    body = client.get("/").text
    cards = re.findall(r'<div class="price-side price-([fi])"><span class="chip chip-\1">([^<]+)</span><dl class="price-rows">(.*?)</dl></div>', body, re.DOTALL)
    assert [(side, label) for side, label, _ in cards] == [("f", "For founders"), ("i", "For investors")]
    rows = [re.findall(r"<dt>([^<]+)</dt><dd class=\"price-amt\">([^<]+)</dd>", c) for _, _, c in cards]
    assert rows == [[("Founder Free", "$0"), ("Founder Premium", "$5 a month")], [("Investor Free", "$0"), ("Investor Premium", "$29 a month")]]
    assert '<table class="tbl plans"' not in body


# The owner's approval of 21 October 2026 for the other pages ("approved, do the other pages"): each page takes the
# composition the approved plan gave it, and the icon rule of the home page holds on every page.
# A status icon, or the only label of a control: a selected filter's tick, a muted preview and a row that opens.
SITE_ICONS = HOME_ICONS | {"plus", "check", "volume-x"}


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_every_page_centres_its_hero(client, key):
    body = client.get(PUBLIC_PAGES[key]["path"]).text
    h1 = body.index("<h1")
    hero = body.rfind('class="hero-c', 0, h1)
    assert hero != -1 and "</section>" not in body[hero:h1]


# The owner asked on 28 October 2026 for real icons on the pricing page, so each feature there carries a Lucide icon of
# its own and the trust band carries three. The rule above still holds on every other page.
PRICING_ICONS = {"user-round", "video", "file-text", "message-square-quote", "gauge", "activity", "search", "messages-square",
                 "file-check", "trending-up", "calendar-check", "list-filter", "user-check", "circle-play", "file-search",
                 "clipboard-check", "badge-check", "sliders-horizontal", "scan-face", "shield-check", "lock-keyhole"}


@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_no_page_carries_a_decorative_icon(client, key):
    body = client.get(PUBLIC_PAGES[key]["path"]).text
    allowed = SITE_ICONS | (PRICING_ICONS if key == "pricing" else set())
    assert set(re.findall(r'class="lucide lucide-([a-z-]+)"', body)) <= allowed
    assert body.count("Menu</button>") == 1


def test_the_header_menu_button_shows_its_word_alone_and_marks_when_it_is_open(client):
    for path in ("/", "/terms", "/no-such-page"):
        assert "lucide-menu" not in client.get(path).text, path
    assert '.site .menubtn[aria-expanded="true"]{background:var(--fill-pressed)}' in (APP / "static" / "css" / "site.css").read_text()


@pytest.mark.parametrize("key", LEGAL)
def test_a_legal_page_centres_its_title_and_date_over_a_reading_column(client, key):
    body = client.get(PUBLIC_PAGES[key]["path"]).text
    assert '<section aria-labelledby="l-title" class="hero-c legal-hero">' in body
    assert '<p class="small legal-date">' in body
    assert '<div class="wrap sec narrow doc">' not in body and body.count('<div class="wrap sec read doc">') >= 3


def test_the_pricing_page_sets_free_beside_premium_for_each_side(client):
    body = client.get("/pricing").text
    pairs = re.findall(r'<div class="plan-pair">(.*?)</div></div></section>', body, re.DOTALL)
    assert len(pairs) == 2
    for pair, side in zip(pairs, ("Founder", "Investor")):
        assert re.findall(r'<h3 class="h3" id="[a-z-]+">([^<]+)</h3>', pair) == [f"{side} Free", f"{side} Premium"]
    assert body.count('<div class="qa">') == 1



# Redesigned on 28 October 2026: each plan shows its price, one sentence of value, its action and a list of what it includes,
# each feature with its own Lucide icon, and Premium's action waits for December 2026.
def test_each_plan_states_its_price_value_action_and_features_with_icons(client):
    body = client.get("/pricing").text
    plans = re.findall(r'<article class="card plan plan-[fi][^"]*" aria-labelledby="([a-z-]+)">(.*?)</article>', body, re.DOTALL)
    assert [key for key, _ in plans] == ["founder-free", "founder-premium", "investor-free", "investor-premium"]
    for key, card in plans:
        assert '<p class="plan-price"><span class="plan-amt">$' in card, key
        assert card.count('<p class="plan-value">') == 1, key
        items = re.findall(r'<li><span class="feat-icon" aria-hidden="true"><svg class="lucide lucide-([a-z-]+)"[^>]*>.*?</svg></span>'
                           r'<span>([^<]+)</span></li>', card)
        assert len(items) >= 4, key
        assert 'class="tick"' not in card, key
        if key.endswith("premium"):
            assert '<p class="plan-cta plan-wait">Premium opens in December 2026.</p>' in card and "plan-hi" in body
        else:
            assert re.search(r'<a class="btn btn-[fi] plan-cta" href="/signin">', card), key


# The owner announced on 28 October 2026 that face verification and anti-money-laundering checks launch in December
# 2026. The pricing page carries it as a pre-launch announcement in a brand navy band with a drawing of face verification and a
# padlock, and marks what is live now apart from what is coming.
def test_the_pricing_page_announces_the_checks_for_december_2026(client):
    body = client.get("/pricing").text
    assert '<section aria-labelledby="p-trust" class="trust">' in body
    assert '<svg class="trust-art" role="img" aria-label="A drawing of face verification on a phone, with a padlock"' in body
    text = _text(client, "/pricing")
    assert "Coming in December 2026 Know exactly who is on the other side." in text
    assert "Face verification December 2026" in text and "Anti-money-laundering checks December 2026" in text
    assert "Private evidence Live now" in text
    assert body.count('<span class="trust-when trust-live">Live now</span>') == 1


def test_the_founders_page_puts_the_example_dashboard_beneath_the_hero_and_the_steps_on_a_timeline(client):
    body = client.get("/for-founders").text
    after_hero = body[body.index("</section>", body.index('aria-labelledby="f-title"')):]
    assert after_hero.startswith('</section><section id="readiness" aria-labelledby="f-ready" class="show">')
    assert '<div class="frame dash" role="group" aria-label="Example founder dashboard">' in body
    timeline = re.search(r'<ol class="timeline">(.*?)</ol>', body, re.DOTALL).group(1)
    assert len(re.findall(r'<li><span class="num num-f">\d</span><h3 class="h3">', timeline)) == 4


def test_the_investors_page_puts_the_search_beneath_the_hero_and_shows_an_introduction_in_three_steps(client):
    body = client.get("/for-investors").text
    after_hero = body[body.index("</section>", body.index('aria-labelledby="inv-title"')):]
    assert after_hero.startswith('</section><section id="discover" aria-labelledby="disc-title" class="show">')
    steps = re.findall(r'<li><span class="num num-i">\d</span><h3 class="h3">([^<]+)</h3>', body)
    assert steps == ["Send a short note", "The founder decides", "Talk on IkonetU"]
    for name in ("evidence", "intro"):
        assert f'<source media="(max-width: 599px)" srcset="/media/phone-{name}.webp"' in body


def test_the_readiness_check_marks_a_strong_area_in_the_verified_colour(client):
    body = client.get("/readiness-check").text
    assert '<div class="hero-c rc-hero"><p class="lbl lbl-f">Readiness self-check</p>' in body
    assert 'color:var(--verified)">Already strong</h3>' in body and "#123C7A;margin-top:3px" not in body




# The owner's edits of 22 October 2026: no "sample data" wording, one Example tag on each showcase, no stories or
# explanatory notes, and justified paragraphs.
@pytest.mark.parametrize("key", list(PUBLIC_PAGES))
def test_no_page_says_sample(client, key):
    assert not re.search(r"\bsample\b", _text(client, PUBLIC_PAGES[key]["path"]), re.IGNORECASE)


@pytest.mark.parametrize(("path", "tags"), [("/", 1), ("/for-founders", 2), ("/for-investors", 1)])
def test_each_showcase_carries_one_example_tag(client, path, tags):
    assert client.get(path).text.count('<span class="chip chip-n">Example</span>') == tags


def test_the_home_page_says_its_central_message_without_the_story(client):
    text = _text(client, "/")
    assert "Many founders build real businesses" not in text and "investors spend their time" not in text
    assert "IkonetU puts the founder's evidence beside the pitch, so investors see the proof before they ask to meet." in text
    assert "Measures" not in text and "A filled week has a progress update" not in text


def test_website_paragraphs_are_justified_and_hyphenated(client):
    css = (APP / "static" / "css" / "site.css").read_text()
    assert ".site:not(.pg-app) :is(p, dd, figcaption, .rows > li, .plan-list > li){text-align:justify;-webkit-hyphens:auto;hyphens:auto}" in css
    assert "text-align-last:center" in css
    assert '<html lang="en-GB">' in client.get("/").text
