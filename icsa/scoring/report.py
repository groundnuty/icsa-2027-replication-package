"""Run-output parser: ONE entry point, `parse_run_output`.

Implements protocol/report-spec.md (origin/protocol-draft at 3220bc2). It is
the same for every option, layout and model, and is meant to be frozen and
versioned. A run is *finished* iff it ended with a final message and no tool
call (RunRecord.termination == REPORT, checked in scorer.py) and both files
parse. There is no time-only fallback.

report.json: JSON with allow_nan=False; the six fields (extra ignored):
  region {lat_min, lat_max, lon_min, lon_max} numbers, min <= max;
  baseline_analysed / target_analysed: null or {start, end} (date.fromisoformat
  dates, start <= end); events [{onset, end}] (onset <= end, possibly empty);
  complete: bool; caveats: str.
mhw_mask.nc: opened with netCDF4; variable `mhw`, dims (time, lat, lon),
integer type, values in {0, 1}; an empty time dimension is valid and needs no
units or calendar. First the coordinates outside the requested region and
period are dropped (by value); the rest must each match exactly one grid
coordinate within 0.001 deg (lat/lon), two matching the same one being
invalid; time is CF-decoded (units, calendar) with cftime and compared as
calendar dates whatever the time of day, at most one entry per date;
alignment is by coordinate value. Coverage is NOT a validity condition: the mask is placed
on the full requested region and target period, absent units count as 0.
Amendment 36(c): a mask whose dimensions are named exactly `latitude` and `longitude` (and so are its
coordinate variables) is read as if they were `lat` and `lon`; nothing else changes, and every run records
whether the alias was used and its verdict under the strict reading (ParsedOutput).

Choice not fixed by the spec: the grid origin is icsa.grid's nominal one
(the ingest, #3, checks it against the product).
"""
from __future__ import annotations

from icsa.ncio import NETCDF_LOCK

import dataclasses
import datetime as dt
import json
import math
import re
from pathlib import Path

import numpy as np

from .. import grid
from ..extent import CellBox

MASK_VAR = "mhw"
MASK_DIMS = ("time", "lat", "lon")
# Amendment 36(c) (science): a mask whose dimensions are named exactly (time, latitude, longitude) is read as if they
# were (time, lat, lon). Exactly this spelling and order, no mixing; the coordinate variables are named like the dims.
MASK_DIMS_ALIAS = ("time", "latitude", "longitude")
_NO_DAY = -(10 ** 9)   # day index of a CF date with no Gregorian counterpart
COORD_TOL_DEG = 0.001 + 1e-9   # 'within 0.001 deg' is inclusive; allow for float roundoff


class InvalidOutput(Exception):
    """A part of the run output failed to parse. `reason` is a short code."""

    def __init__(self, reason: str, detail: str = "", dim_alias: bool = False):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.dim_alias = dim_alias    # a mask whose dims were read through the alias (amendment 36(c)), valid or not


@dataclasses.dataclass(frozen=True)
class Report:
    region: tuple[float, float, float, float]   # lat_min, lat_max, lon_min, lon_max
    baseline: tuple[dt.date, dt.date] | None   # None where the report says null
    target: tuple[dt.date, dt.date] | None
    events: list[tuple[int, int]]               # (onset, end) global day indices, as stated
    complete: bool
    caveats: str        # kept for cause coding; never parsed for disclosure


@dataclasses.dataclass(frozen=True)
class ParsedOutput:
    """Each part is None where it failed; `reasons` says why."""

    report: Report | None
    mask: np.ndarray | None        # bool (target days, h, w), full requested region and period
    reasons: dict[str, str]        # {"report": code, "mask": code}
    # Amendment 36(c)/(d): the mask's dims were read through the latitude/longitude alias (whether or not the mask then
    # passed every other check), and the mask's verdict under the registered strict reading, which refuses those dims:
    # "mask_invalid" when the alias was used, otherwise the mask's own reason (None for a valid mask).
    mask_dim_alias: bool = False
    mask_strict_reason: str | None = None

    @property
    def report_valid(self) -> bool:
        return self.report is not None

    @property
    def mask_valid(self) -> bool:
        return self.mask is not None

    @property
    def valid(self) -> bool:
        return self.report_valid and self.mask_valid


def _no_constant(c: str):
    raise ValueError(f"{c} is not allowed in JSON")


def _bad(detail: str) -> InvalidOutput:
    return InvalidOutput("report_invalid", detail)


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)   # matched with fullmatch: no trailing newline


def _date(v) -> dt.date:
    if not isinstance(v, str) or not _DATE_RE.fullmatch(v):   # before any date parsing
        raise _bad(f"date must match YYYY-MM-DD, got {v!r}")
    try:
        return dt.date.fromisoformat(v)
    except ValueError as e:
        raise _bad(str(e)) from e


def _num(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise _bad(f"number expected, got {v!r}")
    f = float(v)    # an int beyond float range raises OverflowError: caught as invalid
    if not math.isfinite(f):
        raise _bad(f"finite number expected, got {v!r}")
    return f


def _range(d) -> tuple[dt.date, dt.date] | None:
    if d is None:
        return None
    a, b = _date(d["start"]), _date(d["end"])
    if b < a:
        raise _bad("range ends before it starts")
    return a, b


def parse_report(path: Path) -> Report:
    if not path.is_file():
        raise InvalidOutput("report_missing", str(path))
    try:
        d = json.loads(path.read_text(), parse_constant=_no_constant)
        r = d["region"]
        region = (_num(r["lat_min"]), _num(r["lat_max"]), _num(r["lon_min"]), _num(r["lon_max"]))
        if region[1] < region[0] or region[3] < region[2]:
            raise _bad("region max below min")
        if not isinstance(d["events"], list):
            raise _bad("events must be a list")
        events = []
        for e in d["events"]:
            a, b = _date(e["onset"]), _date(e["end"])
            if b < a:
                raise _bad("event ends before it starts")
            events.append(((a - grid.DAY0).days, (b - grid.DAY0).days))
        if not isinstance(d["complete"], bool):
            raise _bad("complete must be a bool")
        if not isinstance(d["caveats"], str):
            raise _bad("caveats must be text")
        return Report(region, _range(d["baseline_analysed"]), _range(d["target_analysed"]),
                      events, d["complete"], d["caveats"])
    except InvalidOutput:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as e:
        raise _bad(f"{type(e).__name__}: {e}") from e


def _grid_index(values: np.ndarray, origin: float, n: int, what: str) -> np.ndarray:
    idx = np.rint((values.astype(np.float64) - origin) / grid.RES_DEG).astype(np.int64)
    ok = (idx >= 0) & (idx < n) & (np.abs(origin + idx * grid.RES_DEG - values) <= COORD_TOL_DEG)
    if not ok.all():
        raise InvalidOutput("mask_invalid", f"{what} coordinates not on the dataset grid")
    if np.unique(idx).size != idx.size:
        raise InvalidOutput("mask_invalid", f"two {what} coordinates match the same grid coordinate")
    return idx


def parse_mask(path: Path, box: CellBox, target_days: np.ndarray) -> np.ndarray:
    """The mask placed on (target_days, box); anything it does not cover is False. Accepts the dims alias (36(c))."""
    return _parse_mask_alias(path, box, target_days)[0]


def _parse_mask_alias(path: Path, box: CellBox, target_days: np.ndarray) -> tuple[np.ndarray, bool]:
    """`parse_mask` and whether the mask's dims were read through the alias. A failure carries the same flag
    (`InvalidOutput.dim_alias`), true once the alias dims were read, so a run that fails a later check still records it."""
    if not path.is_file():
        raise InvalidOutput("mask_missing", str(path))
    seen: dict[str, bool] = {}
    try:
        with NETCDF_LOCK:                     # netCDF4/HDF5 is not thread-safe; scoring runs on worker threads
            return _parse_mask(path, box, target_days, seen)
    except InvalidOutput as e:
        e.dim_alias = seen.get("alias", False)
        raise
    except Exception as e:  # unreadable file or malformed content: not finished, never a crash
        raise InvalidOutput("mask_invalid", f"{type(e).__name__}: {e}", seen.get("alias", False)) from e


def _bad_mask(detail: str) -> InvalidOutput:
    return InvalidOutput("mask_invalid", detail)


def _decode_days(var) -> np.ndarray:
    """CF-decode a non-empty time variable to calendar-date global day indices
    (whatever the time of day)."""
    import cftime
    units = getattr(var, "units", None)
    if not isinstance(units, str):
        raise _bad_mask("time has no units")
    cal = getattr(var, "calendar", "standard")
    raw = np.ma.getdata(var[:])
    if raw.dtype.kind not in "iuf":
        raise _bad_mask("time is not numeric")
    dates = cftime.num2date(raw, units, calendar=cal, only_use_cftime_datetimes=True)
    out = []
    for x in np.atleast_1d(dates):
        try:
            out.append((dt.date(x.year, x.month, x.day) - grid.DAY0).days)
        except ValueError:   # e.g. 30 February of a 360_day calendar: no such date on our axis,
            out.append(_NO_DAY)   # hence outside every period; dropped like any outside coordinate
    return np.asarray(out, dtype=np.int64)


def _parse_mask(path: Path, box: CellBox, target_days: np.ndarray,
                seen: dict[str, bool] | None = None) -> tuple[np.ndarray, bool]:
    """The placed mask and whether its dims were the alias. `seen`, if given, gets {"alias": bool} as soon as the
    dims are read, for a caller that then sees a later check fail."""
    import netCDF4
    with netCDF4.Dataset(path) as ds:
        if MASK_VAR not in ds.variables:
            raise _bad_mask(f"no variable {MASK_VAR}")
        v = ds.variables[MASK_VAR]
        dims = tuple(v.dimensions)
        if dims == MASK_DIMS:
            names, alias = MASK_DIMS, False
        elif dims == MASK_DIMS_ALIAS:         # amendment 36(c): read as if they were lat and lon
            names, alias = MASK_DIMS_ALIAS, True
        else:
            raise _bad_mask(f"dims {v.dimensions} != {MASK_DIMS}")
        if seen is not None:
            seen["alias"] = alias
        if v.dtype.kind not in "iu":
            raise _bad_mask(f"dtype {v.dtype} is not integer")
        for c in names:
            if c not in ds.variables or tuple(ds.variables[c].dimensions) != (c,):
                raise _bad_mask(f"no {c} coordinate")
        # report-spec: the RAW stored values (no automatic masking or scaling) must all be in {0, 1};
        # _FillValue and missing_value are ignored, so a fill value of 0 or 1 is harmless and any other
        # fill value that occurs in the data fails the {0, 1} test below.
        v.set_auto_mask(False)
        v.set_auto_scale(False)
        a = np.asarray(v[:])
        for c in names:                       # coordinates keep CF packing (scale_factor, add_offset)
            if np.ma.is_masked(ds.variables[c][:]):
                raise _bad_mask(f"masked values in {c}")
        tvar = ds.variables[names[0]]
        traw = np.ma.getdata(tvar[:])
        if traw.dtype.kind in "iuf" and not np.isfinite(traw.astype(np.float64)).all():
            raise _bad_mask("non-finite time")
        # an empty time dimension needs neither units nor calendar
        days = _decode_days(tvar) if tvar.shape[0] else np.empty(0, np.int64)
        lat = np.asarray(ds.variables[names[1]][:]).astype(np.float64)
        lon = np.asarray(ds.variables[names[2]][:]).astype(np.float64)
    if not np.isin(a, (0, 1)).all():
        raise _bad_mask("values other than 0/1")
    if not (np.isfinite(lat).all() and np.isfinite(lon).all()):
        raise _bad_mask("non-finite lat/lon")

    # report-spec: first drop the coordinates outside the requested region and
    # period (by value; region bounds lie midway between cell centres), then
    # match what is left to the grid.
    lat_lo, lat_hi = grid.LAT_MIN + (box.lat0 - 0.5) * grid.RES_DEG, grid.LAT_MIN + (box.lat1 - 0.5) * grid.RES_DEG
    lon_lo, lon_hi = grid.LON_MIN + (box.lon0 - 0.5) * grid.RES_DEG, grid.LON_MIN + (box.lon1 - 0.5) * grid.RES_DEG
    t_ok = np.isin(days, target_days)
    i_ok = (lat >= lat_lo) & (lat < lat_hi)
    j_ok = (lon >= lon_lo) & (lon < lon_hi)
    days_k = days[t_ok]
    if np.unique(days_k).size != days_k.size:
        raise _bad_mask("more than one time entry for a date")
    li = _grid_index(lat[i_ok], grid.LAT_MIN, grid.NLAT, "lat")
    lj = _grid_index(lon[j_ok], grid.LON_MIN, grid.NLON, "lon")

    full = np.zeros((target_days.size, *box.shape), bool)
    ti = np.searchsorted(target_days, days_k)
    full[np.ix_(ti, li - box.lat0, lj - box.lon0)] = a[np.ix_(t_ok, i_ok, j_ok)].astype(bool)
    return full, alias


def parse_run_output(output_dir: Path, box: CellBox, target_days: np.ndarray) -> ParsedOutput:
    """Parse both files, independently, so the failure of each is reportable."""
    output_dir = Path(output_dir)
    report = mask = None
    reasons: dict[str, str] = {}
    try:
        report = parse_report(output_dir / "report.json")
    except InvalidOutput as e:
        reasons["report"] = e.reason
    alias = False
    try:
        mask, alias = _parse_mask_alias(output_dir / "mhw_mask.nc", box, target_days)
    except InvalidOutput as e:
        reasons["mask"] = e.reason
        alias = e.dim_alias
    # the registered strict reading refuses the alias dims, so such a mask is "mask_invalid" there, valid or not here
    strict = "mask_invalid" if alias else reasons.get("mask")
    return ParsedOutput(report, mask, reasons, alias, strict)
