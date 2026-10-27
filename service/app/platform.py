"""The settings an admin sets on the Settings page, as founders and investors are held to them.

platform_status() gives the mode, its message and the pitch and introduction rules to anyone, because
nothing in it is private. The answer is kept for a few seconds, so a page does not wait on it, and an
admin's change is read again at once in this process. The database holds every rule as well: the pitch
trigger, the introduction trigger and the admin functions refuse what breaks them, so a stale or a
missing answer here can never let a broken rule through.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .log import log_warn
from .supabase import Supabase

KEEP_SECONDS = 15
TYPE_NAMES = {"video/mp4": "MP4", "video/webm": "WebM", "video/quicktime": "MOV"}
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
STAFF = ("reviewer", "admin")


@dataclass(frozen=True)
class Rules:
    """The defaults are the database's own, used until platform_status() answers."""
    mode: str = "live"
    maintenance_message: str = "IkonetU is being updated and will be back shortly."
    pitch_types: tuple[str, ...] = ("video/mp4", "video/webm", "video/quicktime")
    pitch_max_mb: int = 50
    pitch_max_seconds: int = 90
    introductions_on: bool = True
    introductions_per_day: int = 10

    @property
    def maintenance(self) -> bool:
        return self.mode == "maintenance"

    @property
    def pitch_max_bytes(self) -> int:
        return self.pitch_max_mb * 1024 * 1024

    @property
    def type_names(self) -> list[str]:
        return [TYPE_NAMES[t] for t in self.pitch_types if t in TYPE_NAMES]


_kept: dict = {"at": 0.0, "rules": None}


def forget() -> None:
    """Makes the next page read the settings again, after an admin changes them."""
    _kept["at"], _kept["rules"] = 0.0, None


async def rules(supabase: Supabase | None) -> Rules:
    if supabase is None:
        return Rules()
    now = time.monotonic()
    if _kept["rules"] is not None and now - _kept["at"] < KEEP_SECONDS:
        return _kept["rules"]
    result = await supabase.as_visitor().rpc("platform_status")
    row = result.data[0] if result.ok and isinstance(result.data, list) and result.data else None
    if row is None:
        log_warn("platform.status_failed", {"code": result.error.code if result.error else "empty"})
        found = _kept["rules"] or Rules()
    else:
        found = Rules(
            mode=row["mode"], maintenance_message=row["maintenance_message"], pitch_types=tuple(row["pitch_types"]),
            pitch_max_mb=row["pitch_max_mb"], pitch_max_seconds=row["pitch_max_seconds"],
            introductions_on=row["introductions_on"], introductions_per_day=row["introductions_per_day"])
    _kept["at"], _kept["rules"] = now, found
    return found


def or_list(names: list[str]) -> str:
    """MP4, WebM or MOV."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]


def number_text(n: int) -> str:
    """Ten, as the investor pages wrote the daily limit, and 25 once it is past ten."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def video_article(names: list[str]) -> str:
    """An MP4 video, a WebM video, a MOV video."""
    return "an" if names and names[0] == "MP4" else "a"
