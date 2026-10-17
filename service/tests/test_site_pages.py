"""The eleven website pages: each answers with its own title, description and canonical address."""

from __future__ import annotations

import html
import re

import pytest

from app.pages import PUBLIC_PAGES

INTERACTIVE = {"home", "founders", "investors", "how", "readiness"}


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
