"""The Analytics page: its ranges and bars, the figures it counts, and the page and CSV through HTTP.

The founders below are made up. The dates of the ranges are the board's own, which counted to 24 October 2026.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone

import httpx

from app import admin_analytics as aa

from .test_investor_register import sign_in

BOARD_DAY = date(2026, 10, 24)


def founder(record_id: str, joined: str, country: str = "Ghana", university: str = "University of Ghana",
            support: list[str] | None = None) -> dict:
    return {"record_id": record_id, "joined_at": joined, "country": country, "university": university,
            "support": support or []}


def intro(intro_id: str, record_id: str, made_on: str, status: str = "pending", sample: bool = False,
          investor_no: str | None = "001") -> dict:
    return {"intro_id": intro_id, "record_id": record_id, "made_on": made_on, "status": status, "sample": sample,
            "investor_no": None if sample else investor_no, "investor_name": "Ife Adeyemi" if sample else "Ada Okafor",
            "founder_name": "Name " + record_id, "startup": "", "founder_sample": sample}


# ---------------------------------------------------------------- ranges and bars
def test_the_three_ranges_end_today_and_say_their_dates_as_the_board_did():
    assert aa.range_text("year", *aa.window("year", BOARD_DAY)) == "1 January to 24 October 2026"
    assert aa.range_text("d90", *aa.window("d90", BOARD_DAY)) == "27 July 2026 to 24 October 2026"
    assert aa.range_text("d30", *aa.window("d30", BOARD_DAY)) == "25 September 2026 to 24 October 2026"
    assert [aa.button_label(k, BOARD_DAY) for k in aa.RANGES] == ["2026 so far", "Last 90 days", "Last 30 days"]
    assert [aa.slug(k, BOARD_DAY) for k in aa.RANGES] == ["2026-so-far", "last-90-days", "last-30-days"]


def test_the_year_has_a_bar_a_month_up_to_this_month():
    bars = aa.periods("year", *aa.window("year", BOARD_DAY))
    assert [b["label"] for b in bars] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"]
    assert bars[0]["period"] == "January 2026" and bars[-1]["end"] == BOARD_DAY


def test_the_shorter_ranges_have_a_bar_a_week_ending_on_saturday_with_the_first_week_cut_at_the_start():
    bars = aa.periods("d90", *aa.window("d90", BOARD_DAY))
    assert len(bars) == 13
    assert (bars[0]["label"], bars[0]["period"]) == ("1 Aug", "27 July 2026 to 1 August 2026")
    assert (bars[-1]["label"], bars[-1]["period"]) == ("24 Oct", "18 October 2026 to 24 October 2026")
    short = aa.periods("d30", *aa.window("d30", BOARD_DAY))
    assert [b["label"] for b in short] == ["26 Sep", "3 Oct", "10 Oct", "17 Oct", "24 Oct"]
    assert short[0]["period"] == "25 September 2026 to 26 September 2026"


def test_a_week_not_yet_over_keeps_its_saturday_as_the_label_and_ends_today():
    tuesday = date(2026, 10, 27)
    last = aa.periods("d30", *aa.window("d30", tuesday))[-1]
    assert (last["label"], last["period"]) == ("31 Oct", "25 October 2026 to 27 October 2026")


# ---------------------------------------------------------------- the figures
SOURCE = {
    "founders": [
        founder("p001", "2026-01-13T21:16:55+00:00", "Ghana", "University of Ghana", ["Financial support", "Legal support"]),
        founder("p002", "2026-01-20T08:00:00+00:00", "Ghana", "university of ghana ", ["Financial support"]),
        founder("p003", "2026-02-02T08:00:00+00:00", "Nigeria", "UNIVERSITY OF GHANA", ["Mentorship support"]),
        founder("p004", "2026-10-20T08:00:00+00:00", "Kenya", "University of Nairobi", ["Financial support"]),
    ],
    "investors": ["2026-07-01", "2026-10-22"],
    "introductions": [{"record_id": "p001", "made_on": "2026-10-24", "status": "accepted"},
                      {"record_id": "p004", "made_on": "2026-10-23", "status": "pending"}],
    "videos": ["2026-10-25"],
}
INTROS = [intro("n001", "p001", "2026-10-24", "accepted", investor_no="002"), intro("n002", "p004", "2026-10-23"),
          intro("s001", "s01", "2026-07-12", "accepted", sample=True)]


def test_the_year_counts_founders_investors_and_introductions_and_leaves_the_video_after_today_out():
    a = aa.build(SOURCE, INTROS, "year", BOARD_DAY)
    assert a["kpis"] == [("Founders joined", 4), ("Investors added to the register", 2), ("Pitch videos", 0),
                         ("Introductions made", 2), ("Introductions accepted", 1)]
    assert [(b["label"], b["f"], b["i"]) for b in a["bars"]][:2] == [("Jan", 2, 0), ("Feb", 1, 0)]
    assert (a["bars"][-1]["f"], a["bars"][-1]["i"]) == (1, 1)
    assert a["bars"][0]["f_style"] == "height:170px" and a["bars"][1]["f_style"] == "height:85px"
    assert a["chart_label"].startswith("Founders and investors by month: January 2026, 2 founders, 0 investors; ")


def test_the_way_to_an_introduction_counts_the_founders_who_joined_in_the_range():
    year = aa.build(SOURCE, INTROS, "year", BOARD_DAY)
    assert [(f["label"], f["n"]) for f in year["funnel"]] == [
        ("Joined the register", 4), ("Introduced to an investor", 2), ("Introduction accepted", 1)]
    assert year["funnel"][1]["style"] == "width:50%"
    month = aa.build(SOURCE, INTROS, "d30", BOARD_DAY)
    assert [f["n"] for f in month["funnel"]] == [1, 1, 0]
    assert month["kpis"][3] == ("Introductions made", 2)


def test_countries_support_and_universities_are_counted_for_the_founders_in_the_range():
    a = aa.build(SOURCE, INTROS, "year", BOARD_DAY)
    assert [(c["label"], c["n"]) for c in a["countries"]] == [("Ghana", 2), ("Kenya", 1), ("Nigeria", 1)]
    assert [(c["label"], c["n"]) for c in a["support"]] == [("Financial support", 3)]
    assert [(c["label"], c["n"]) for c in a["universities"]] == [("University of Ghana", 3), ("University of Nairobi", 1)]
    assert a["universities"][1]["style"] == "width:33%"
    assert not a["no_founders"]


def test_a_range_with_no_founder_says_so_and_still_counts_the_investors():
    source = {**SOURCE, "founders": SOURCE["founders"][:3]}
    a = aa.build(source, INTROS, "d30", BOARD_DAY)
    assert a["no_founders"] and a["countries"] == [] and a["funnel"][0]["style"] == "width:0%"
    assert a["kpis"][1] == ("Investors added to the register", 1)


def test_the_table_lists_the_register_introductions_made_in_the_range_by_register_number():
    a = aa.build(SOURCE, INTROS, "year", BOARD_DAY)
    assert [(n["investor"], n["made"], n["chip"]) for n in a["table"]] == [
        ("001 · Ada Okafor", "23 Oct 2026", "Pending"), ("002 · Ada Okafor", "24 Oct 2026", "Accepted")]
    assert a["table"][0]["startup"] == "Not given"
    assert aa.build(SOURCE, INTROS, "d30", date(2026, 12, 31))["table"] == []


def test_the_csv_has_a_line_for_each_bar():
    a = aa.build(SOURCE, INTROS, "d30", BOARD_DAY)
    assert a["csv_name"] == "ikonetu-analytics-last-30-days.csv"
    assert a["csv_rows"][-1] == ["18 October 2026 to 24 October 2026", 1, 1]


# ---------------------------------------------------------------- the page
def today_source() -> dict:
    today = datetime.now(timezone.utc).date()
    return {"founders": [founder("p001", f"{today.isoformat()}T00:30:00+00:00", "Ghana", "University of Ghana",
                                 ["Financial support", "Financial support"])],
            "investors": [today.isoformat()], "introductions": [], "videos": [(today - timedelta(days=200)).isoformat()]}


def sign_in_with_analytics(client, fake, role: str = "admin"):
    sign_in(client, fake, role=role)
    fake.on("POST", "/rest/v1/rpc/admin_analytics_source", httpx.Response(200, json=today_source()))
    fake.on("POST", "/rest/v1/rpc/admin_register_introductions", httpx.Response(200, json=[]))


def test_the_analytics_page_shows_the_range_its_totals_and_the_buttons(client, fake):
    sign_in_with_analytics(client, fake)
    r = client.get("/admin/analytics?range=d30")
    assert r.status_code == 200
    body = r.text
    assert '<a href="/admin/analytics?range=d30" aria-current="true">Last 30 days</a>' in body
    assert '<a href="/admin/analytics">' in body and 'href="/admin/analytics.csv?range=d30"' in body
    assert '<span class="a-kpi-label">Founders joined</span><span class="a-kpi-value">1</span>' in body
    assert '<span class="a-kpi-label">Pitch videos</span><span class="a-kpi-value">0</span>' in body
    assert "No introduction was made in this range." in body
    assert '<a href="/admin/analytics" class="adm-link" aria-current="page">' in body


def test_an_unknown_range_shows_the_year(client, fake):
    sign_in_with_analytics(client, fake)
    body = client.get("/admin/analytics?range=forever").text
    assert f'aria-current="true">{datetime.now(timezone.utc).year} so far</a>' in body


def test_the_csv_has_the_boards_columns_and_a_line_for_each_bar(client, fake):
    sign_in_with_analytics(client, fake)
    r = client.get("/admin/analytics.csv?range=d30")
    assert r.status_code == 200 and r.headers["content-disposition"] == 'attachment; filename="ikonetu-analytics-last-30-days.csv"'
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows[0] == ["Period", "Founders joined", "Investors added to the register"]
    assert rows[-1][1:] == ["1", "1"]


def test_the_page_says_so_when_the_figures_cannot_be_read(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_analytics_source", httpx.Response(500, json={"message": "down"}))
    fake.on("POST", "/rest/v1/rpc/admin_register_introductions", httpx.Response(200, json=[]))
    assert "The analytics could not be read. Please reload the page." in client.get("/admin/analytics").text
    assert client.get("/admin/analytics.csv").status_code == 503


def test_a_reviewer_cannot_open_the_analytics(client, fake):
    sign_in_with_analytics(client, fake, role="reviewer")
    for path in ("/admin/analytics", "/admin/analytics.csv"):
        r = client.get(path)
        assert r.status_code == 307 and r.headers["location"] == "/admin", path
    assert not fake.sent("POST", "/rest/v1/rpc/admin_analytics_source")
