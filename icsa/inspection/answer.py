"""The coder's structured answer (rubric §4): its JSON schema and its validation.

Both coders get the same schema (Codex through `--output-schema`, Claude through
`output_config.format`). A schema-valid answer can still be malformed: a contradiction
(RANGES with no range), a date that does not exist, a range outside its year, or a citation
of a line the packet does not have. `validate` returns every problem; an answer with any
problem is MALFORMED and is never turned into a verdict (the caller retries a bounded number
of times, then records MALFORMED, which counts as no agreement).

Citations are `C<cell>:L<line>` or `C<cell>:L<first>-L<last>` (the `-L` before the last line is
optional), cell and line numbers as the packet prints them.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
import re

BASELINE_YEARS = tuple(range(1992, 2003))
PART_STATUS = ("RANGES", "NONE", "CANNOT_TELL")
CELL_STATUS = ("ALL_SEA_CELLS", "SOME_MISSING", "CANNOT_TELL")
EXC_STATUS = ("NONE", "LISTED", "CANNOT_TELL")
EXC_KIND = ("SKIPPED_DATES", "DUPLICATE_DATES", "STRIDE", "CELL_SPECIFIC", "OTHER")
EXC_CELLS = ("ALL", "BOXES")
CITE = re.compile(r"^C(\d+):L(\d+)(?:-L?(\d+))?$")

_RANGE = {"type": "object", "additionalProperties": False, "required": ["start", "end"],
          "properties": {"start": {"type": "string"}, "end": {"type": "string"}}}
_BOX = {"type": "object", "additionalProperties": False, "required": ["lat_min", "lat_max", "lon_min", "lon_max"],
        "properties": {k: {"type": "number"} for k in ("lat_min", "lat_max", "lon_min", "lon_max")}}
# minItems 1 (prepared for science's ruling, 2 Nov): the prompt says each part cites code lines, and 29% of Claude's
# attempts on dev packets gave a NONE part an empty cite, which the validator refuses; the schema now refuses it at the API.
# It applies to CANNOT_TELL parts too (a schema cannot make it conditional): they cite the lines that leave it open.
_CITES = {"type": "array", "items": {"type": "string"}, "minItems": 1}


def _part(status_enum) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["status", "ranges", "cite"],
            "properties": {"status": {"type": "string", "enum": list(status_enum)},
                           "ranges": {"type": "array", "items": _RANGE}, "cite": _CITES}}


SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["baseline", "target", "cells", "exceptions", "summary"],
    "properties": {
        "baseline": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["year", "status", "ranges", "cite"],
            "properties": {"year": {"type": "integer"}, "status": {"type": "string", "enum": list(PART_STATUS)},
                           "ranges": {"type": "array", "items": _RANGE}, "cite": _CITES}}},
        "target": _part(PART_STATUS),
        "cells": {"type": "object", "additionalProperties": False,
                  "required": ["status", "missing_boxes", "missing_rule", "cite"],
                  "properties": {"status": {"type": "string", "enum": list(CELL_STATUS)},
                                 "missing_boxes": {"type": "array", "items": _BOX},
                                 "missing_rule": {"type": "string"}, "cite": _CITES}},
        "exceptions": {"type": "object", "additionalProperties": False, "required": ["status", "items"],
                       "properties": {"status": {"type": "string", "enum": list(EXC_STATUS)}, "items": {
                           "type": "array", "items": {
                               "type": "object", "additionalProperties": False,
                               "required": ["kind", "ranges", "keep_every_nth_day", "cells", "boxes", "description", "cite"],
                               "properties": {"kind": {"type": "string", "enum": list(EXC_KIND)},
                                              "ranges": {"type": "array", "items": _RANGE},
                                              "keep_every_nth_day": {"type": "integer"},
                                              "cells": {"type": "string", "enum": list(EXC_CELLS)},
                                              "boxes": {"type": "array", "items": _BOX},
                                              "description": {"type": "string"}, "cite": _CITES}}}}},
        "summary": {"type": "string"},
    },
}


def schema() -> dict:
    return copy.deepcopy(SCHEMA)


def schema_text() -> str:
    """Canonical text of the schema (it is part of the hashed prompt)."""
    return json.dumps(SCHEMA, indent=1, sort_keys=True)


def parse_date(s) -> dt.date | None:
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def _keys(obj, want: set, where: str, errs: list) -> bool:
    if not isinstance(obj, dict):
        errs.append(f"{where}: not an object")
        return False
    if set(obj) != want:
        errs.append(f"{where}: keys {sorted(obj)} are not {sorted(want)}")
        return False
    return True


def _ranges(rs, where: str, errs: list, year: int | None = None) -> None:
    if not isinstance(rs, list):
        errs.append(f"{where}.ranges: not a list")
        return
    for k, r in enumerate(rs):
        w = f"{where}.ranges[{k}]"
        if not _keys(r, {"start", "end"}, w, errs):
            continue
        a, b = parse_date(r["start"]), parse_date(r["end"])
        if a is None or b is None:
            errs.append(f"{w}: dates must be real YYYY-MM-DD dates")
            continue
        if a > b:
            errs.append(f"{w}: start after end")
        if year is not None and (a.year != year or b.year != year):
            errs.append(f"{w}: outside {year}")


def _boxes(bs, where: str, errs: list) -> None:
    if not isinstance(bs, list):
        errs.append(f"{where}: not a list")
        return
    for k, b in enumerate(bs):
        w = f"{where}[{k}]"
        if not _keys(b, {"lat_min", "lat_max", "lon_min", "lon_max"}, w, errs):
            continue
        if not all(isinstance(b[x], (int, float)) and not isinstance(b[x], bool) and math.isfinite(b[x]) for x in b):
            errs.append(f"{w}: coordinates must be finite numbers")
            continue
        if b["lat_min"] > b["lat_max"] or b["lon_min"] > b["lon_max"]:
            errs.append(f"{w}: min above max")


def _cites(cs, where: str, errs: list, lines: dict[int, int] | None, required: bool) -> None:
    if not isinstance(cs, list) or not all(isinstance(c, str) for c in cs):
        errs.append(f"{where}.cite: not a list of strings")
        return
    if required and not cs:
        errs.append(f"{where}.cite: no code line cited")
    for c in cs:
        m = CITE.match(c.strip())
        if not m:
            errs.append(f"{where}.cite: {c!r} is not C<cell>:L<line>[-L<line>]")
            continue
        cell, a = int(m.group(1)), int(m.group(2))
        b = int(m.group(3)) if m.group(3) else a
        if b < a:
            errs.append(f"{where}.cite: {c!r} ends before it starts")
        elif lines is not None and (cell not in lines or a < 1 or b > lines[cell]):
            errs.append(f"{where}.cite: {c!r} is not a line of the packet")


def validate(ans, lines: dict[int, int] | None = None) -> list[str]:
    """Every problem with a parsed answer. `lines`: cell number -> number of code lines in the
    packet, to check that citations exist (None skips that check)."""
    errs: list[str] = []
    if not _keys(ans, {"baseline", "target", "cells", "exceptions", "summary"}, "answer", errs):
        return errs
    bl = ans["baseline"]
    if not isinstance(bl, list):
        errs.append("baseline: not a list")
    else:
        years = [e.get("year") if isinstance(e, dict) else None for e in bl]
        if sorted(y for y in years if isinstance(y, int)) != list(BASELINE_YEARS) or len(years) != len(BASELINE_YEARS):
            errs.append(f"baseline: needs exactly one entry for each year {BASELINE_YEARS[0]}..{BASELINE_YEARS[-1]}")
        for e in bl:
            w = f"baseline[{e.get('year') if isinstance(e, dict) else '?'}]"
            if not _keys(e, {"year", "status", "ranges", "cite"}, w, errs):
                continue
            _status_part(e, w, errs, lines, year=e["year"] if isinstance(e["year"], int) else None)
    if _keys(ans["target"], {"status", "ranges", "cite"}, "target", errs):
        _status_part(ans["target"], "target", errs, lines)
    c = ans["cells"]
    if _keys(c, {"status", "missing_boxes", "missing_rule", "cite"}, "cells", errs):
        if c["status"] not in CELL_STATUS:
            errs.append(f"cells.status: {c['status']!r}")
        _boxes(c["missing_boxes"], "cells.missing_boxes", errs)
        if not isinstance(c["missing_rule"], str):
            errs.append("cells.missing_rule: not a string")
        elif c["status"] == "SOME_MISSING" and not c["missing_boxes"] and not c["missing_rule"].strip():
            errs.append("cells: SOME_MISSING names no box and no rule")
        elif c["status"] != "SOME_MISSING" and (c["missing_boxes"] or c["missing_rule"].strip()):
            errs.append(f"cells: {c['status']} with missing cells named")
        _cites(c["cite"], "cells", errs, lines, required=c["status"] != "CANNOT_TELL")
    x = ans["exceptions"]
    if _keys(x, {"status", "items"}, "exceptions", errs):
        if x["status"] not in EXC_STATUS:
            errs.append(f"exceptions.status: {x['status']!r}")
        items = x["items"] if isinstance(x["items"], list) else None
        if items is None:
            errs.append("exceptions.items: not a list")
            items = []
        if x["status"] == "LISTED" and not items:
            errs.append("exceptions: LISTED with no item")
        if x["status"] != "LISTED" and items:
            errs.append(f"exceptions: {x['status']} with items")
        for k, it in enumerate(items):
            w = f"exceptions.items[{k}]"
            if not _keys(it, {"kind", "ranges", "keep_every_nth_day", "cells", "boxes", "description", "cite"}, w, errs):
                continue
            if it["kind"] not in EXC_KIND:
                errs.append(f"{w}.kind: {it['kind']!r}")
            _ranges(it["ranges"], w, errs)
            n = it["keep_every_nth_day"]
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                errs.append(f"{w}.keep_every_nth_day: must be an integer >= 1 (1 = no stride)")
            elif n > 1 and not it["ranges"]:
                errs.append(f"{w}: a stride needs the ranges it applies to")
            if it["cells"] not in EXC_CELLS:
                errs.append(f"{w}.cells: {it['cells']!r}")
            _boxes(it["boxes"], f"{w}.boxes", errs)
            if it["cells"] == "BOXES" and not it["boxes"]:
                errs.append(f"{w}: cells BOXES with no box")
            if it["cells"] == "ALL" and it["boxes"]:
                errs.append(f"{w}: cells ALL with boxes")
            if it["cells"] == "ALL" and not it["ranges"]:
                errs.append(f"{w}: excludes no day (no ranges) and no particular cell")
            if not isinstance(it["description"], str):
                errs.append(f"{w}.description: not a string")
            _cites(it["cite"], w, errs, lines, required=True)
    if not isinstance(ans["summary"], str):
        errs.append("summary: not a string")
    return errs


def _status_part(e: dict, w: str, errs: list, lines, year: int | None = None) -> None:
    if e["status"] not in PART_STATUS:
        errs.append(f"{w}.status: {e['status']!r}")
        return
    _ranges(e["ranges"], w, errs, year=year)
    if e["status"] == "RANGES" and not e["ranges"]:
        errs.append(f"{w}: RANGES with no range")
    if e["status"] != "RANGES" and isinstance(e["ranges"], list) and e["ranges"]:
        errs.append(f"{w}: {e['status']} with ranges")
    _cites(e["cite"], w, errs, lines, required=e["status"] != "CANNOT_TELL")


def parse(text: str):
    """The answer object from a coder's final text: the whole text, or the one fenced or braced
    JSON object in it. Returns (obj, error)."""
    t = (text or "").strip()
    cands = [t]
    m = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
    cands += m
    if "{" in t and "}" in t:
        cands.append(t[t.index("{"): t.rindex("}") + 1])
    last = "empty answer"
    for c in cands:
        try:
            return json.loads(c, parse_constant=_no_constant), None
        except (json.JSONDecodeError, ValueError) as e:
            last = f"not JSON: {e}"
    return None, last


def _no_constant(name: str):
    raise ValueError(f"{name} is not standard JSON")
