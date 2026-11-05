"""A data-driven exclusion list for H3's audit records (#34; science 5 Nov 02:50Z): leases that a foreign actor shared a slot user with are marked `not_observed:foreign_lines`.

The file (`H3_EXCLUSIONS`, default `/mnt/volume2/icsa-2027/lane-snap4/h3-exclusions.tsv`) has one line per window, tab separated, `#` comments:

    provider <TAB> slot <TAB> from (UTC ISO) <TAB> to (UTC ISO) <TAB> reason

A production lease of `slot` on `provider` whose window [start, end] (the run record's `extras.onedata_slot`) overlaps [from, to] has its audit record's verdict replaced by
`{class: not_observed, reason: foreign_lines, testable: false, in_primary: false}` with the list line that did it. The audit lines of a foreign actor sat in that slot user's stream, so the
lease's lines cannot be told from the run's own; counting them as the run's reads (or as "nothing read") would be wrong either way. Run directories and the capture are untouched; only the
store's `runs/<run key>/<attempt>/m_audit.json` is rewritten, by rename, and `exclusions.applied.json` (counts by reason, no run key) is written beside. It is applied between the records and
the platform-rows summary of every extract pass (`h3_extract.py` hooks `extract._summary_and_join`), so a record that a pass rebuilt is marked again before anything reads it. A switched-on
record (the gate or perf log) is the run's own file and is not touched.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from collections import Counter
from pathlib import Path

DEFAULT = "/mnt/volume2/icsa-2027/lane-snap4/h3-exclusions.tsv"
REASON = "foreign_lines"


def _epoch(s: str) -> float:
    return dt.datetime.fromisoformat(s.strip().replace("Z", "+00:00")).timestamp()


def load(path=None) -> list[dict]:
    """The list; a missing file is an empty list (no exclusion), a malformed line is an error (never skipped silently)."""
    p = Path(path or os.environ.get("H3_EXCLUSIONS") or DEFAULT)
    if not p.is_file():
        return []
    out = []
    for n, ln in enumerate(p.read_text().splitlines(), 1):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) != 5 or not all(x.strip() for x in f):
            raise ValueError(f"{p}:{n}: five tab-separated fields expected (provider, slot, from, to, reason)")
        out.append({"provider": f[0].strip(), "slot": f[1].strip(), "from": _epoch(f[2]), "to": _epoch(f[3]), "reason": f[4].strip(), "line": n})
        if out[-1]["to"] < out[-1]["from"]:
            raise ValueError(f"{p}:{n}: the window ends before it starts")
    return out


def overlaps(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 <= b1 and b0 <= a1


def _write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def apply(store, attempts, provider: str, exclusions: list[dict] | None = None) -> dict:
    """Mark the audit records of `attempts` ((run dir, run record) pairs, as `extract.attempts` gives them) that fall in a window of `provider`. Returns counts by reason only."""
    store = Path(store)
    ex = [e for e in (load() if exclusions is None else exclusions) if e["provider"] == provider]
    counts: Counter = Counter()
    if ex:
        for d, rec in attempts:
            sl = (rec.get("extras") or {}).get("onedata_slot") or {}
            if sl.get("start") is None or sl.get("end") is None:
                continue
            hit = next((e for e in ex if e["slot"] == str(sl.get("slot")) and overlaps(float(sl["start"]), float(sl["end"]), e["from"], e["to"])), None)
            if hit is None:
                continue
            from icsa.faults.mainaudit import windows as W
            p = store / "runs" / W.run_key_of(rec) / Path(d).name / "m_audit.json"
            if not p.is_file():
                counts["record_missing"] += 1
                continue
            r = json.loads(p.read_text())
            v = r.get("verdict") or {}
            if v.get("reason") == REASON and (r.get("exclusion") or {}).get("list_line") == hit["line"]:
                counts[hit["reason"]] += 1                       # already marked by this line: counted, not rewritten
                continue
            r["verdict"] = {**v, "class": "not_observed", "reason": REASON, "testable": False, "in_primary": False, "calibration_rule_class": "not_observed"}
            r["exclusion"] = {"list_line": hit["line"], "reason": hit["reason"], "was": {"class": v.get("class"), "reason": v.get("reason")}}
            _write(p, json.dumps(r, indent=1, sort_keys=True).encode())
            counts[hit["reason"]] += 1
    _write(store / "exclusions.applied.json", json.dumps({"provider": provider, "by_reason": dict(counts), "windows": len(ex)}, indent=1, sort_keys=True).encode())
    return dict(counts)
