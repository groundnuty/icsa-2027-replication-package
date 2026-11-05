"""Model slots from endpoints.json: sticky slot choice, availability."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

API_SLOT = "anthropic-api"
SITE_B_PREFIX = "site_b:"


def site_b_slot(model: str) -> str:
    """site_b has no slots file: one logical slot per model, capped by config."""
    return SITE_B_PREFIX + model


def backend_of(slot: str | None) -> str:
    """anthropic | site_b | site_a, from the slot name the executor receives."""
    if slot == API_SLOT:
        return "anthropic"
    if slot and slot.startswith(SITE_B_PREFIX):
        return "site_b"
    return "site_a"


def read_endpoints(path: str) -> list[dict[str, Any]] | None:
    """The slot list, or None if the file is missing or unreadable (never guess)."""
    try:
        raw = json.loads(Path(path).expanduser().read_text())
    except (OSError, ValueError):
        return None
    if isinstance(raw, dict):
        raw = raw.get("slots")
    if not isinstance(raw, list):
        return None      # valid JSON of another shape (null, a number, a string, no slot list): unreadable, never "no slots", never a crash
    return [s for s in raw if isinstance(s, dict)]


def _age_s(slot: dict[str, Any], now: dt.datetime) -> float | None:
    """Seconds since the entry's own `checked_utc` (the HPC agent's last look at the slot), or None if absent or unreadable."""
    e = slot.get("checked_utc")
    if not e:
        return None
    try:
        t = dt.datetime.fromisoformat(str(e).replace("Z", "+00:00"))
    except ValueError:
        return None
    t = t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)
    return (now - t).total_seconds()


def stale_slots(slots: list[dict[str, Any]] | None, now: dt.datetime, max_age_s: float | None) -> list[str]:
    """Slots whose entry claims `up` but whose `checked_utc` is absent, unreadable, older than `max_age_s` or that far in the
    future. After a reboot the synced file kept saying "up" for 80 minutes with nothing listening, so a claim nobody has
    re-checked recently is never read as healthy. max_age_s None = no freshness rule."""
    if max_age_s is None:
        return []
    out = []
    for s in slots or []:
        if s.get("up") and s.get("slot") is not None:
            age = _age_s(s, now)
            if age is None or age > max_age_s or age < -max_age_s:
                out.append(str(s["slot"]))
    return out


def fresh_endpoints(slots: list[dict[str, Any]] | None, now: dt.datetime, max_age_s: float | None) -> list[dict[str, Any]] | None:
    """The slot list with every stale entry set to not up (a copy; None stays None)."""
    if slots is None or max_age_s is None:
        return slots
    bad = set(stale_slots(slots, now, max_age_s))
    return [{**s, "up": False, "stale": True} if str(s.get("slot")) in bad else s for s in slots]


def _ends_in_s(slot: dict[str, Any], now: dt.datetime) -> float | None:
    e = slot.get("backend_ends_utc")
    if not e:
        return None
    try:
        t = dt.datetime.fromisoformat(str(e).replace("Z", "+00:00"))
    except ValueError:
        return None
    t = t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)
    return (t - now).total_seconds()


def usable_slots(slots: list[dict[str, Any]] | None, endpoint_key: str,
                 now: dt.datetime, min_remaining_s: float) -> list[str]:
    out = []
    for s in slots or []:
        if s.get("model") != endpoint_key or not s.get("up"):
            continue
        rem = _ends_in_s(s, now)
        if rem is not None and rem < min_remaining_s:
            continue
        out.append(str(s["slot"]))
    return out


def pick_slot(candidates: list[str], active: dict[str, int]) -> str | None:
    """Fewest active sessions; ties by slot name for determinism."""
    if not candidates:
        return None
    return min(candidates, key=lambda s: (active.get(s, 0), s))
