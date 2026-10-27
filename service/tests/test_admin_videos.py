"""The Pitch videos page: the cards, linked videos titled by their startup, and the decisions through HTTP.

The names below are made up. The real files and founder records are kept out of the repository.
"""

from __future__ import annotations

import json

import httpx

from .test_investor_register import ORIGIN, sign_in

ALL_FOUR = {"problem": True, "solution": True, "market": True, "ask": True}


def video(video_id: str, file_name: str, status: str = "pending", record: dict | None = None) -> dict:
    return {"video_id": video_id, "file_name": file_name, "file_type": "MOV", "size_text": "47.9 MB", "folder": "All_Videos",
            "added_on": "2026-10-25", "drive_url": f"https://drive.google.com/file/d/{video_id}/view", "transcript": None,
            "record_id": record["record_id"] if record else None, "status": status, "reason": None,
            "decided_at": "2026-10-27T07:57:00Z" if status != "pending" else None,
            "decided_by_name": "Ada Admin" if status != "pending" else None,
            "startup": record["startup"] if record else None, "founder_name": record["founder_name"] if record else None,
            "sector": record["sector"] if record else None}


LINKED = video("t01", "Gateway 4.MOV", "approved", {"record_id": "p008", "startup": "Kola Pay", "founder_name": "Kemi Bello",
                                                     "sector": "Fintech"})
LOOSE = video("t02", "Envoy Video.mp4")


def videos_signed_in(client, fake, rows: list[dict] | None = None, role: str = "admin"):
    sign_in(client, fake, role=role)
    fake.on("POST", "/rest/v1/rpc/admin_pitch_videos", httpx.Response(200, json=rows if rows is not None else [LINKED, LOOSE]))


def test_a_linked_video_is_titled_by_its_startup_with_the_founder_and_sector(client, fake):
    videos_signed_in(client, fake)
    body = client.get("/admin/videos?tab=all&video=t01").text
    assert '<span class="a-vname">Kola Pay</span>\n<span>Kemi Bello · Fintech</span>' in body
    assert "Gateway 4.MOV · MOV · 47.9 MB · All_Videos · added to Google Drive 25 Oct 2026" in body
    assert '<a href="/admin/founders/p008" class="a-go">Open the founder record</a>' in body


def test_a_video_with_no_founder_record_keeps_its_file_name(client, fake):
    videos_signed_in(client, fake)
    body = client.get("/admin/videos").text
    assert '<span class="a-vname">Envoy Video.mp4</span>\n<span>All_Videos folder · MOV · 47.9 MB</span>' in body
    assert "Open the founder record" not in body
    assert "1 video waits for review · 2 videos in all" in body


def test_approving_sends_the_four_checks_and_names_the_startup(client, fake):
    videos_signed_in(client, fake, [video("t01", "Gateway 4.MOV", "pending", {"record_id": "p008", "startup": "Kola Pay",
                                                                             "founder_name": "Kemi Bello", "sector": "Fintech"})])
    fake.on("POST", "/rest/v1/rpc/admin_pitch_video_decide", httpx.Response(204))
    r = client.post("/admin/videos/t01/approve", data={"problem": "on", "solution": "on", "market": "on", "ask": "on"},
                    headers=ORIGIN)
    assert r.status_code == 303
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_pitch_video_decide")[0].content) == {
        "p_id": "t01", "p_decision": "approved", "p_checks": ALL_FOUR}
    assert "Approved the Kola Pay pitch video." in client.get(r.headers["location"]).text


def test_a_check_left_unticked_is_refused_with_the_boards_words(client, fake):
    videos_signed_in(client, fake, [LOOSE])
    fake.on("POST", "/rest/v1/rpc/admin_pitch_video_decide", httpx.Response(400, json={
        "code": "22023", "message": "tick all four checks to approve"}))
    r = client.post("/admin/videos/t02/approve", data={"problem": "on", "solution": "on", "market": "on"}, headers=ORIGIN)
    assert "Tick all four to approve." in client.get(r.headers["location"]).text


def test_rejecting_needs_one_of_the_six_reasons(client, fake):
    videos_signed_in(client, fake, [LOOSE])
    r = client.post("/admin/videos/t02/reject", data={"reason": "I did not like it."}, headers=ORIGIN)
    assert "reason=missing" in r.headers["location"] and not fake.sent("POST", "/rest/v1/rpc/admin_pitch_video_decide")
    fake.on("POST", "/rest/v1/rpc/admin_pitch_video_decide", httpx.Response(204))
    r = client.post("/admin/videos/t02/reject", data={"reason": "The pitch does not name the ask."}, headers=ORIGIN)
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_pitch_video_decide")[0].content)["p_reason"] == \
        "The pitch does not name the ask."


def test_a_reviewer_cannot_open_the_pitch_videos(client, fake):
    videos_signed_in(client, fake, role="reviewer")
    r = client.get("/admin/videos")
    assert r.status_code == 307 and r.headers["location"] == "/admin"
