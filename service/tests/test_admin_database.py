"""The Database page: every table described and grouped, the search and the rows filter, and the page through HTTP."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import httpx

from app import admin_schema as ad

from .test_investor_register import sign_in

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
TODAY = date(2026, 10, 24)


def table(name: str, rows: int, columns: str, rls: bool = True) -> dict:
    return {"name": name, "rows": rows, "rls": rls, "columns": columns.split(", ")}


DATABASE = {
    "version": "17.11 (Debian 17.11-1)",
    "tables": [table("profiles", 1, "user_id, role, status, full_name"),
               table("introduction_messages", 0, "id, introduction_id, sender_id, body, created_at"),
               table("venture_updates", 0, "id, venture_id, body, created_at"),
               table("investor_register", 53, "register_no, full_name, registered_on"),
               table("a_new_table", 2, "id, created_at")],
    "buckets": [{"id": "evidence", "files": 3}, {"id": "pitches", "files": 1}],
    "migrations": {"count": 12, "latest": "20261024000001", "name": "investor_register"},
}


def test_every_table_the_migrations_create_is_described_and_grouped():
    sql = "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))
    created = set(re.findall(r"create table (?:if not exists )?(?:public\.)?([a-z_]+)", sql, re.I))
    assert created and created <= set(ad.DESCRIBED), sorted(created - set(ad.DESCRIBED))


def test_the_summary_and_the_schema_say_what_the_database_holds():
    db = ad.build(DATABASE, "", False, TODAY)
    assert db["subtitle"] == "Supabase, PostgreSQL 17.11 · live counts read on 24 October 2026"
    assert db["summary"] == [("Tables", "5", "Row security on all 5"), ("Rows in all tables", "56", "Across 5 tables"),
                             ("Stored files", "4", "pitches 1 · evidence 3"), ("Migrations", "12", "Latest 24 October 2026")]
    assert db["latest"] == "20261024000001_investor_register"
    assert [b["holds"] for b in db["buckets"]] == ["Pitch videos", "Evidence documents"]
    assert db["tables_text"] == "5, all with row security on"


def test_tables_are_grouped_as_the_board_grouped_them_and_an_unknown_table_is_still_shown():
    db = ad.build(DATABASE, "", False, TODAY)
    assert [(g["label"], [t["name"] for t in g["tables"]]) for g in db["groups"]] == [
        ("People", ["profiles", "investor_register"]), ("Ventures and Evidence", ["venture_updates"]),
        ("Introductions", ["introduction_messages"]), ("Other tables", ["a_new_table"])]
    assert db["groups"][-1]["tables"][0]["what"] == "Not described yet"
    assert db["groups"][0]["tables"][0]["rows_text"] == "1 row"


def test_a_search_finds_tables_by_column_and_opens_them_with_message_text_marked_private():
    db = ad.build(DATABASE, "Body", False, TODAY)
    shown = {t["name"]: t for g in db["groups"] for t in g["tables"]}
    assert set(shown) == {"introduction_messages", "venture_updates"}
    assert shown["introduction_messages"]["open"] and shown["introduction_messages"]["private"]
    kinds = {c["name"]: c["kind"] for c in shown["introduction_messages"]["columns"]}
    assert kinds["body"] == "private" and kinds["id"] == ""
    assert {c["name"]: c["kind"] for c in shown["venture_updates"]["columns"]}["body"] == "hit"


def test_the_rows_filter_leaves_out_empty_tables_and_a_search_with_no_match_shows_nothing():
    db = ad.build(DATABASE, "", True, TODAY)
    assert [t["name"] for g in db["groups"] for t in g["tables"]] == ["profiles", "investor_register", "a_new_table"]
    assert ad.build(DATABASE, "nothing like this", False, TODAY)["groups"] == []


def test_a_table_without_row_security_and_a_database_without_a_migration_record_are_said_plainly():
    data = {**DATABASE, "tables": [*DATABASE["tables"], table("open_table", 0, "id", rls=False)], "migrations": None}
    db = ad.build(data, "", False, TODAY)
    assert db["summary"][0] == ("Tables", "6", "Row security on 5 of 6")
    assert db["summary"][3] == ("Migrations", "Not recorded", "This database keeps no record of them")
    assert db["tables_text"] == "6, 5 of them with row security on" and db["latest"] is None


# ---------------------------------------------------------------- the page
def test_the_database_page_shows_the_groups_and_the_search(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_database", httpx.Response(200, json=DATABASE))
    body = client.get("/admin/database?q=body").text
    assert '<span class="a-colname a-colname-private">body</span>' in body
    assert "Message text is never shown." in body
    assert '<details class="a-dbt" open>' in body
    assert "investor_register" not in body.split('id="files-h"')[0]
    assert '<a href="/admin/database" class="adm-link" aria-current="page">' in body


def test_the_database_page_says_so_when_it_cannot_be_read(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_database", httpx.Response(500, json={"message": "down"}))
    assert "The database could not be read. Please reload the page." in client.get("/admin/database").text


def test_a_reviewer_cannot_open_the_database_page(client, fake):
    sign_in(client, fake, role="reviewer")
    r = client.get("/admin/database")
    assert r.status_code == 307 and r.headers["location"] == "/admin"
    assert not fake.sent("POST", "/rest/v1/rpc/admin_database")
