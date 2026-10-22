"""The component system the owner approved on 21 October 2026: tokens, colour roles and states.

Every stylesheet reads its values from tokens.css, every token a rule names exists, the approved
colour pairs keep their contrast, and the evidence statuses keep colours of their own.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.product import LEVEL, STATUS

APP = Path(__file__).resolve().parents[1] / "app"
CSS = APP / "static" / "css"
SHEETS = ["site.css", "app.css", "sign-in.css", "globals.css"]


def tokens() -> dict[str, str]:
    text = re.sub(r"/\*.*?\*/", "", (CSS / "tokens.css").read_text(), flags=re.DOTALL)
    root = text.split("@media", 1)[0]
    return dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", root))


def luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_page_loads_the_tokens_before_the_other_stylesheets(client):
    links = re.findall(r'<link rel="stylesheet" href="/static/css/([a-z-]+\.css)">', client.get("/").text)
    assert links[:4] == ["tokens.css", "fonts.css", "globals.css", "site.css"]
    assert client.get("/static/css/tokens.css").status_code == 200


@pytest.mark.parametrize("sheet", SHEETS)
def test_stylesheets_take_their_colours_from_the_tokens(sheet):
    text = re.sub(r"/\*.*?\*/", "", (CSS / sheet).read_text(), flags=re.DOTALL)
    # White text on a filled button and the dark ground behind a video are the only colours written out.
    assert set(re.findall(r"#[0-9A-Fa-f]{6}", text)) <= {"#FFFFFF", "#1D2939"}


def test_every_token_a_rule_names_is_defined():
    defined = set(tokens()) | {"--font-serif", "--font-sans"}
    used: set[str] = set()
    for path in [*CSS.glob("*.css"), *(APP / "templates").rglob("*.html"), *(APP / "static" / "js").rglob("*.js")]:
        used |= set(re.findall(r"var\((--[a-z0-9-]+)", path.read_text()))
    assert used - defined == set()


# Each pair the component board names, with the contrast it must keep: 4.5:1 for text, 3:1 for a graphic.
PAIRS = [
    ("--ink", "--founder", 4.5), ("--ink", "--founder-hover", 4.5), ("--investor", "--canvas", 4.5),
    ("--investor-hover", "--canvas", 4.5), ("--investor-press", "--canvas", 4.5), ("--investor", "--investor-tint", 4.5),
    ("--investor", "--investor-tint-press", 4.5), ("--founder-text", "--canvas", 4.5), ("--founder-text", "--founder-tint", 4.5),
    ("--text-2", "--canvas", 4.5), ("--text-3", "--fill", 4.5), ("--verified", "--verified-tint", 4.5),
    ("--third-party", "--third-party-tint", 4.5), ("--error", "--canvas", 4.5), ("--error", "--error-tint", 4.5),
    ("--warning", "--warning-tint", 4.5), ("--footer-text", "--footer", 4.5), ("--text-disabled", "--fill", 4.5),
    ("--line-control", "--canvas", 3.0), ("--mark-on", "--canvas", 3.0), ("--mark-mid", "--canvas", 3.0),
    ("--mark-edge", "--canvas", 3.0), ("--founder", "--canvas", 3.0),
]


@pytest.mark.parametrize(("fore", "back", "minimum"), PAIRS)
def test_approved_colour_pairs_keep_their_contrast(fore, back, minimum):
    t = tokens()
    assert contrast(t[fore], t[back]) >= minimum


def test_orange_is_never_text_on_white():
    # #F26B1D measures 3.05:1 on white, so it only ever fills a shape.
    assert contrast(tokens()["--founder"], "#FFFFFF") < 4.5
    for sheet in SHEETS:
        assert not re.search(r"(?<![-a-z])color:var\(--founder\)", (CSS / sheet).read_text()), sheet


def test_evidence_statuses_have_colours_apart_from_the_founder_and_investor_contexts():
    assert STATUS["reviewed"]["chip"] == "chip-ok"
    assert STATUS["third_party"]["chip"] == "chip-3p"
    assert STATUS["submitted"]["chip"] == "chip-n"
    assert LEVEL["strong"]["chip"] == "chip-ok"
    site = (CSS / "site.css").read_text()
    assert ".site .chip-ok{background:var(--verified-tint);color:var(--verified)}" in site
    assert ".site .chip-3p{background:var(--third-party-tint);color:var(--third-party)}" in site
    for path in [*(APP / "templates").rglob("*.html"), *(APP / "static" / "js").rglob("*.js"), APP / "product.py"]:
        assert "chip-io" not in path.read_text(), path


def test_motion_marks_a_change_of_state_and_stops_under_reduced_motion():
    css = "".join((CSS / s).read_text() for s in ["site.css", "app.css"])
    # The dialog fades in, a changed status fades across, and an opened row slides down a few pixels.
    assert sorted(re.findall(r"@keyframes ([a-z-]+)", css)) == ["fade-in", "pd-in", "row-in"]
    reduced = (CSS / "tokens.css").read_text().split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "--m-quick: 0ms" in reduced and "--m-open: 0ms" in reduced


def test_a_sending_button_keeps_its_colours_and_cannot_be_pressed():
    forms = (APP / "static" / "js" / "forms.js").read_text()
    assert 'setAttribute("aria-busy", "true")' in forms and 'removeAttribute("aria-busy")' in forms
    assert '.site .btn:disabled:not([aria-busy="true"])' in (CSS / "site.css").read_text()


def test_a_pitch_that_cannot_play_says_so():
    template = (APP / "templates" / "app" / "pitch_video.html").read_text()
    assert ('<p class="err" role="status" hidden data-pitch-error>'
            "The pitch could not be played. Try again, or read the transcript below.</p>") in template
    script = (APP / "static" / "js" / "app" / "pitch-video.js").read_text()
    assert "[data-pitch-error]" in script and "NETWORK_NO_SOURCE" in script
