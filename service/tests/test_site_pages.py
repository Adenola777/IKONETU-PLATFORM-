"""The eight website pages: each answers with its own title, description and canonical address."""

from __future__ import annotations

import html
import re

import pytest

from app.pages import PUBLIC_PAGES

INTERACTIVE = {"home", "founders", "investors", "readiness"}


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
