"""The ten website pages: each answers with its own title, description and canonical address."""

from __future__ import annotations

import html
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
    return html.unescape(re.sub(r"<[^>]+>", " ", client.get(path).text))


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
    assert "Premium is not on sale yet." in text and "nobody is charged today" in text
    for path in ("/", "/for-founders", "/for-investors", "/trust-and-safety", "/terms"):
        assert "Premium is not on sale yet" in _text(client, path), path


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
