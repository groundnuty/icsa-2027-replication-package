"""Endpoint concurrency changes live, with its time and source (amendment 41(b)).

"Endpoint concurrency follows what the serving admins state a deployment can carry ... It changes only when they state a new figure or a deployment joins or
leaves, never on study outcomes ... each change is logged with its time and source." A dispatcher restart costs the runs in flight, so the caps have to change
while it runs. The launch file's `site_b_caps` (per model) and `site_a_slot_caps` (per endpoint key, sessions one slot holds) are the starting values; this record
in the campaign store (meta key `endpoint_caps`) is an OVERRIDE merged over them: a key it does not name keeps its launch value. The dispatcher re-reads it at
every dispatch round and at start (so a restart keeps it); `python -m icsa.campaign caps-set` writes it from a shell.

    {"site_b": {<model>: <int>}, "site_a_slot": {<endpoint key>: <int>}, "set_utc": <UTC>, "source": <who said so, where>, "who": <who set it>}

The record is the LAST change's (its time, source and who); the log of every change is the `endpoint_caps_set` events (the command) and `endpoint_caps_changed`
events (the dispatcher, with the old and new value of every key that moved).
"""
from __future__ import annotations

import json
from typing import Any

META = "endpoint_caps"
FIELDS = ("site_b", "site_a_slot", "set_utc", "source", "who")
KINDS = ("site_b", "site_a_slot")      # the two cap tables the record can change, as the launch file names them (site_b_caps, site_a_slot_caps)


def _is_cap(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def problems_in(site_b: Any, site_a_slot: Any, open_models: dict[str, str]) -> list[str]:
    """Why these two tables cannot be caps: a model that is not among the open models, a key that is not an open model's endpoint key, a value that is not an int >= 0
    (a bool or a float is not one)."""
    out: list[str] = []
    keys = set(open_models.values())
    for kind, table, allowed, what in (("site_b", site_b, set(open_models), "an open model"), ("site_a_slot", site_a_slot, keys, "an endpoint key of an open model")):
        if not isinstance(table, dict):
            out.append(f"{kind} is not an object")
            continue
        for k, v in table.items():
            if k not in allowed:
                out.append(f"{kind}: {k!r} is not {what} ({', '.join(sorted(allowed)) or 'none'})")
            if not _is_cap(v):
                out.append(f"{kind}: {k!r} = {v!r} is not an integer >= 0")
    return out


def check(raw: str | None, open_models: dict[str, str]) -> tuple[dict | None, list[str]]:
    """(the record, []) for a record that may be applied, (None, the reasons) for one that may not, and (None, []) for no record at all."""
    if raw is None:
        return None, []
    try:
        rec = json.loads(raw)
    except ValueError as e:
        return None, [f"not JSON ({e})"]
    if not isinstance(rec, dict):
        return None, ["not an object"]
    out = [f"unknown field {k!r}" for k in rec if k not in FIELDS]
    out += [f"{k} is missing or empty" for k in ("source", "who", "set_utc") if not (isinstance(rec.get(k), str) and rec[k].strip())]
    out += problems_in(rec.get("site_b", {}), rec.get("site_a_slot", {}), open_models)
    return (None, out) if out else (rec, [])


def effective(launch_site_b: dict[str, int], launch_site_a: dict[str, int], rec: dict | None) -> tuple[dict[str, int], dict[str, int]]:
    """The launch tables with the record's keys over them."""
    rec = rec or {}
    return {**launch_site_b, **rec.get("site_b", {})}, {**launch_site_a, **rec.get("site_a_slot", {})}


def diff(old: tuple[dict, dict], new: tuple[dict, dict]) -> list[str]:
    """One "kind key: old -> new" per cap that differs ("none" = the key had no entry)."""
    out = []
    for kind, o, n in zip(KINDS, old, new):
        for k in sorted(set(o) | set(n)):
            if o.get(k) != n.get(k):
                out.append(f"{kind} {k}: {o.get(k, 'none')} -> {n.get(k, 'none')}")
    return out


def parse_pairs(items: list[str] | None, flag: str) -> dict[str, int]:
    """`NAME=N` arguments as a table; a malformed one, a negative or non-integer N, or a name given twice raises ValueError."""
    out: dict[str, int] = {}
    for it in items or []:
        name, eq, val = it.rpartition("=")
        if not eq or not name.strip():
            raise ValueError(f"{flag} {it!r}: wanted NAME=N")
        if not val.isascii() or not val.isdigit():
            raise ValueError(f"{flag} {it!r}: N must be a whole number >= 0")
        if name in out:
            raise ValueError(f"{flag} {name!r} is given twice")
        out[name] = int(val)
    return out


def describe(rec: dict) -> str:
    return f"source: {rec.get('source')}; who: {rec.get('who')}; set_utc: {rec.get('set_utc')}"
