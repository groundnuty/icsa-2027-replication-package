"""Rubric §5: compare one coder's extraction with the required extent, giving its verdict.

The required extent is the instance's (`icsa.instances`): the region's sea cells, the
method-required baseline days (12 May-20 Sep of each year 1992-2002 for a Jun-Aug target) and
the target days. The coder never sees it; this script does the comparison.

- COMPLETE: the extraction covers all of the required extent, with no CANNOT TELL anywhere.
- OMITTING: a definite part of the required extent is missing; the missing parts are named.
  A definite missing part wins over a CANNOT TELL elsewhere.
- CANNOT_TELL: otherwise.

A missing part is "definite" when the coder's answer says it: a required day outside every
range the coder gave for its year (or for the target), a box of missing cells that holds at
least one required sea cell (or a missing-cells rule, which names no box and so cannot be
checked against the sea cells, recorded as such), or an exception that removes a required
day or cell. Exceptions that touch only days or cells outside the required extent remove
nothing. Boxes are inclusive in degrees; a cell is inside when its centre is (grid.lat_of /
grid.lon_of, with half a grid step of tolerance).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

from icsa import grid
from icsa.extent import PartedExtent

from .answer import parse_date

TOL = grid.RES_DEG / 2


@dataclass
class Required:
    """What the comparison needs from the required extent, in plain terms."""
    baseline_days: dict[int, set]        # year -> required baseline dates
    target_days: set                     # required target dates
    lat: np.ndarray                      # (h,) centre latitude of each box row
    lon: np.ndarray                      # (w,) centre longitude of each box column
    sea: np.ndarray                      # (h, w) bool: the required (sea) cells

    @classmethod
    def from_extent(cls, ext: PartedExtent) -> "Required":
        box = ext.target.box
        base: dict[int, set] = {}
        for d in ext.baseline.days:
            day = grid.day_date(int(d))
            base.setdefault(day.year, set()).add(day)
        sea = ext.target.mask.any(axis=0) if ext.target.days.size else ext.baseline.mask.any(axis=0)
        if ext.baseline.days.size and not np.array_equal(ext.baseline.mask.any(axis=0), sea):
            raise ValueError("baseline and target require different cells; the comparison assumes one sea mask")
        return cls(base, {grid.day_date(int(d)) for d in ext.target.days},
                   np.array([grid.lat_of(j) for j in range(box.lat0, box.lat1)]),
                   np.array([grid.lon_of(i) for i in range(box.lon0, box.lon1)]), sea.astype(bool))

    def all_days(self) -> set:
        return set().union(*self.baseline_days.values(), self.target_days)


@dataclass
class Verdict:
    verdict: str                                  # COMPLETE | OMITTING | CANNOT_TELL
    missing: list[dict] = field(default_factory=list)       # definite missing parts
    cannot_tell: list[str] = field(default_factory=list)    # parts the coder could not tell
    missing_cell_days: int = 0                    # required (day, sea cell) pairs the extraction leaves out
    missing_extent_sha256: str = ""               # hash of that exact set (two coders agree exactly iff equal)
    exact: bool = True                            # False when a part (CANNOT TELL, a cells rule) has no exact extent
    extraction_sha256: str = ""                   # hash of the whole canonical extraction (two coders agree exactly iff equal)
    # The instrument's coverage, per part: the share of the part's required (day, sea cell) pairs the extraction covers is
    # 1 - missing / required. Only meaningful when `exact` (a CANNOT TELL part or a cells rule leaves pairs uncounted).
    required_cell_days: dict = field(default_factory=dict)          # {"baseline": n, "target": n}: required days x sea cells
    missing_cell_days_by_part: dict = field(default_factory=dict)   # {"baseline": n, "target": n}: of them, the ones left out

    def groups(self) -> set:
        """The groups with a definite missing part: ('baseline', year), ('target',), ('cells',)."""
        out = set()
        for m in self.missing:
            if m["part"] == "baseline":
                out.add(("baseline", m["year"]))
            elif m["part"] == "target":
                out.add(("target",))
            elif m["part"] in ("cells", "cells_rule"):
                out.add(("cells",))
            elif m["part"] == "exception":
                out.update(tuple(g) for g in m["groups"])
        return out

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "missing": self.missing, "cannot_tell": self.cannot_tell,
                "groups": sorted(list(g) for g in self.groups()), "missing_cell_days": self.missing_cell_days,
                "missing_extent_sha256": self.missing_extent_sha256, "exact": self.exact,
                "extraction_sha256": self.extraction_sha256, "required_cell_days": self.required_cell_days,
                "missing_cell_days_by_part": self.missing_cell_days_by_part}


def _days(ranges) -> set:
    out = set()
    for r in ranges:
        a, b = parse_date(r["start"]), parse_date(r["end"])
        out.update(a + dt.timedelta(k) for k in range((b - a).days + 1))
    return out


def _span(days) -> list[list[str]]:
    out: list[list] = []
    for d in sorted(days):
        if out and d == out[-1][1] + dt.timedelta(1):
            out[-1][1] = d
        else:
            out.append([d, d])
    return [[a.isoformat(), b.isoformat()] for a, b in out]


def _box_cells(req: Required, boxes) -> np.ndarray:
    m = np.zeros_like(req.sea)
    for b in boxes:
        rows = (req.lat >= b["lat_min"] - TOL) & (req.lat <= b["lat_max"] + TOL)
        cols = (req.lon >= b["lon_min"] - TOL) & (req.lon <= b["lon_max"] + TOL)
        m |= rows[:, None] & cols[None, :]
    return m & req.sea


def _region_cells(req: Required, boxes) -> list[int]:
    """Flat indices of the region's cells (land included) inside the boxes."""
    m = np.zeros(req.sea.shape, dtype=bool)
    for b in boxes:
        rows = (req.lat >= b["lat_min"] - TOL) & (req.lat <= b["lat_max"] + TOL)
        cols = (req.lon >= b["lon_min"] - TOL) & (req.lon <= b["lon_max"] + TOL)
        m |= rows[:, None] & cols[None, :]
    return [int(i) for i in np.flatnonzero(m.ravel())]


def _excluded_days(it) -> list[str]:
    span = _days(it["ranges"])
    if it["keep_every_nth_day"] > 1:
        kept = set()
        for r in it["ranges"]:
            a, b = parse_date(r["start"]), parse_date(r["end"])
            kept.update(a + dt.timedelta(s) for s in range(0, (b - a).days + 1, it["keep_every_nth_day"]))
        span -= kept
    return sorted(d.isoformat() for d in span)


def extraction_sha256(ans: dict, req: Required) -> str:
    """Hash of the WHOLE extraction in canonical form: the extracted extent as a set of covered dates
    (inside the required extent or not), each with the region cells it excludes (the cells part's boxes
    plus every exception's cells on that date), plus the CANNOT TELL markers and the cells rule text.
    Phrasings that denote the same extent (one range minus an excluded day, or two ranges around it)
    give the same hash; any difference in what the coder extracted, even outside the required extent,
    gives another (rubric §5: the decomposition needs extractions that agree exactly)."""
    region = req.sea.size
    covered: set = set()
    marks = []
    for e in sorted(ans["baseline"], key=lambda e: e["year"]):
        if e["status"] == "CANNOT_TELL":
            marks.append(f"baseline {e['year']}")
        elif e["status"] == "RANGES":
            covered |= _days(e["ranges"])
    if ans["target"]["status"] == "CANNOT_TELL":
        marks.append("target")
    elif ans["target"]["status"] == "RANGES":
        covered |= _days(ans["target"]["ranges"])
    c, x = ans["cells"], ans["exceptions"]
    if c["status"] == "CANNOT_TELL":
        marks.append("cells")
    if x["status"] == "CANNOT_TELL":
        marks.append("exceptions")
    glob = set(_region_cells(req, c["missing_boxes"])) if c["status"] == "SOME_MISSING" else set()
    excl: dict = {}
    for it in x["items"] if x["status"] == "LISTED" else []:
        cells = set(range(region)) if it["cells"] == "ALL" else set(_region_cells(req, it["boxes"]))
        days = {dt.date.fromisoformat(d) for d in _excluded_days(it)} if it["ranges"] else covered
        for d in days:
            excl.setdefault(d, set()).update(cells)
    dates = {}
    for d in sorted(covered):
        ex = glob | excl.get(d, set())
        if len(ex) < region:                     # a date with every cell excluded is a date not covered
            dates[d.isoformat()] = sorted(ex)
    canon = {"dates": dates, "cannot_tell": marks,
             "cells_rule": " ".join(c["missing_rule"].lower().split()) if c["status"] == "SOME_MISSING" else ""}
    return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()


def _groups_of(req: Required, days: set) -> list[list]:
    g = [["baseline", y] for y, ds in sorted(req.baseline_days.items()) if ds & days]
    if req.target_days & days:
        g.append(["target"])
    return g


def compare(ans: dict, req: Required) -> Verdict:
    """The verdict of one VALID answer (see answer.validate) against the required extent.

    Besides the named parts, the exact set of required (day, sea cell) pairs the extraction leaves
    out is built and hashed: two coders' extractions agree exactly when the hashes are equal and
    both are `exact` (rubric §5: only then is the counterfactual decomposition computed)."""
    missing: list[dict] = []
    unknown: list[str] = []
    day_list = sorted(req.all_days())
    dpos = {d: k for k, d in enumerate(day_list)}
    sea_flat = np.flatnonzero(req.sea.ravel())
    cpos = np.full(req.sea.size, -1)
    cpos[sea_flat] = np.arange(sea_flat.size)
    grid_missing = np.zeros((len(day_list), sea_flat.size), dtype=bool)
    exact = True

    def cols(cellmask: np.ndarray) -> np.ndarray:
        return cpos[np.flatnonzero(cellmask.ravel())]

    def rows(days) -> list[int]:
        return [dpos[d] for d in days if d in dpos]
    by_year = {e["year"]: e for e in ans["baseline"]}
    for y in sorted(req.baseline_days):
        e = by_year.get(y)
        if e is None or e["status"] == "CANNOT_TELL":
            unknown.append(f"baseline {y}")
            continue
        gap = req.baseline_days[y] - (_days(e["ranges"]) if e["status"] == "RANGES" else set())
        if gap:
            missing.append({"part": "baseline", "year": y, "days": len(gap), "ranges": _span(gap)})
            grid_missing[rows(gap), :] = True
    t = ans["target"]
    if t["status"] == "CANNOT_TELL":
        unknown.append("target")
    else:
        gap = req.target_days - (_days(t["ranges"]) if t["status"] == "RANGES" else set())
        if gap:
            missing.append({"part": "target", "days": len(gap), "ranges": _span(gap)})
            grid_missing[rows(gap), :] = True
    c = ans["cells"]
    if c["status"] == "CANNOT_TELL":
        unknown.append("cells")
    elif c["status"] == "SOME_MISSING":
        if c["missing_boxes"]:
            bc = _box_cells(req, c["missing_boxes"])
            n = int(bc.sum())
            if n:
                missing.append({"part": "cells", "cells": n, "boxes": c["missing_boxes"]})
                grid_missing[:, cols(bc)] = True
        if c["missing_rule"].strip():
            exact = False
            missing.append({"part": "cells_rule", "rule": c["missing_rule"].strip(),
                            "note": "a rule, not boxes: not checked against the sea cells"})
    x = ans["exceptions"]
    if x["status"] == "CANNOT_TELL":
        unknown.append("exceptions")
    elif x["status"] == "LISTED":
        all_req = req.all_days()
        for k, it in enumerate(x["items"]):
            span = _days(it["ranges"])
            n = it["keep_every_nth_day"]
            if n > 1:                            # stride: within each range only every n-th day is kept
                kept = set()
                for r in it["ranges"]:
                    a, b = parse_date(r["start"]), parse_date(r["end"])
                    kept.update(a + dt.timedelta(s) for s in range(0, (b - a).days + 1, n))
                span = span - kept
            days = (span & all_req) if it["ranges"] else set(all_req)
            cells = req.sea if it["cells"] == "ALL" else _box_cells(req, it["boxes"])
            if days and cells.any():
                grid_missing[np.ix_(rows(days), cols(cells))] = True
                missing.append({"part": "exception", "item": k, "kind": it["kind"], "days": len(days),
                                "ranges": _span(days), "cells": int(cells.sum()),
                                "groups": _groups_of(req, days), "description": it["description"]})
    exact = exact and not unknown
    n_missing = int(grid_missing.sum())
    digest = hashlib.sha256(np.packbits(grid_missing).tobytes() + str(grid_missing.shape).encode()).hexdigest()
    ext = extraction_sha256(ans, req)
    n_sea = int(req.sea.sum())
    base_days = set().union(*req.baseline_days.values())
    required = {"baseline": len(base_days) * n_sea, "target": len(req.target_days) * n_sea}
    by_part = {"baseline": int(grid_missing[rows(base_days)].sum()), "target": int(grid_missing[rows(req.target_days)].sum())}
    if missing:
        return Verdict("OMITTING", missing, unknown, n_missing, digest, exact, ext, required, by_part)
    return Verdict("CANNOT_TELL" if unknown else "COMPLETE", [], unknown, n_missing, digest, exact, ext, required, by_part)
