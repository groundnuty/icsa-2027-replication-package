"""Instrument validation against scripted runs with known omissions (#9).

    uv run python -m icsa.instruments.validate --work DIR [--jobs 4] [--only NAME]

Every scripted run is `validate_agent.py` executed in a fresh interpreter
with the tracer installed, through one option's read path:
- T and T-unpaginated: range reads over HTTP from a local server;
- D: whole-file downloads from that server, then local reads;
- M and M+: local reads from the files.

The server's request log is the proxy log; `strace` records the local reads.
The known omission of a run comes from its scenario parameters, i.e. from
what the script was written to skip, and from science's ruling on the required
extent (#9, 1 Nov): `expected()` derives the required days, the expected extents
and the true label with its own date arithmetic, sharing nothing with the
instrument's mappers or with #5's code. The instrument gets its required extent
from #5 (`icsa.instances.load.required_extent`), which raises if #5's day count
differs from the ruling's. The report counts, per true class, how often the
instrument says complete, omitting and unknown. The criterion is no omitting run
called complete, with <= 10% unknown, and the analysed extent of every resolved
run must equal the expected one exactly.

Amendment 19(a) routes an `omitting` whose only cause is loaded_not_used to inspection as `unknown`. For the matrix (science, #2, 2 Nov
17:21Z) the unknown gate counts only the instrument's own `unknown`s; a routed run is judged on its raw label against truth, so a wrong
raw label still fails, and the routed share is reported beside the gate, overall and per cell.

Synthetic data (`synth.py`) on the study's real required extent: a Jun-Aug target
and the method window, 12 May..20 Sep of 1992..2002 (1,452 days). S1 and S2 also
hold the rest of the pooling superset (1991-12-27..2003-01-05) and all of the
target year, so that a run can read more than it needs.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import datetime as dt
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .. import grid
from ..extent import CellBox
from ..instances import load as instance_load
from ..instances import required as instance_required
from ..records import Instance, OmissionLabel, Period
from .labeller import label_run
from .layout import HashlessIndex, LayoutIndex, build_index
from .sim.httpserve import RangeServer
from .synth import default_land, write_synthetic

OPTIONS = ("T", "T-unpaginated", "D", "M", "M+")
LAYOUTS = ("S1", "S2")
CROP = CellBox(300, 308, 500, 510)
INSTANCE = Instance("val-1", "val-r", 0, 0, 0, 0, 301, 306, 502, 508,
                    Period(dt.date(2010, 6, 1), dt.date(2010, 8, 31)))
TARGET = (dt.date(2010, 6, 1), dt.date(2010, 8, 31))   # as every real instance: Jun-Aug
WHOLE_BASELINE = (dt.date(1992, 1, 1), dt.date(2002, 12, 31))
CFG = {"page": 1000, "stop_after_pages": 2}
# page: the listing page size the client and the agents send (the real client's 1000);
# stop_after_pages: where a paged_stop agent stops. It must be >= 2: an agent that stops
# after its first page sent no token, which the request log cannot tell from the client.
RUN_TIMEOUT_S = 5400         # an S1 run reading every baseline day opens about 4,100 files


def sea_cells() -> np.ndarray:
    """The instance's sea cells, from the land mask the synthetic data are written with."""
    land = default_land(CROP)
    return ~land[INSTANCE.lat0 - CROP.lat0:INSTANCE.lat1 - CROP.lat0,
                 INSTANCE.lon0 - CROP.lon0:INSTANCE.lon1 - CROP.lon0]


# ---- the ruling, written out independently of #5's code and of the instrument
_REF = dt.date(2000, 1, 1)         # a leap year: every month/day has a position (366 of them)
_MONTH_DAY = [(_REF + dt.timedelta(days=k)) for k in range(366)]


def month_day_position(d: dt.date) -> int:
    return (dt.date(2000, d.month, d.day) - _REF).days


def ruling_baseline_days(start: dt.date, end: dt.date) -> set[int]:
    """Science's ruling on #9 (1 Nov): the required baseline is the union, over target days of
    year d and e in [d-15, d+15], of all dates within +-5 calendar days of a 1992-2002 date with
    day of year e, on the 366-day month/day mapping. For Jun-Aug: 12 May..20 Sep, 1,452 days."""
    target = [start + dt.timedelta(days=k) for k in range((end - start).days + 1)]
    es = {(month_day_position(t) + k) % 366 for t in target for k in range(-15, 16)}
    out: set[int] = set()
    for y in range(1992, 2003):
        for e in es:
            md = _MONTH_DAY[e]
            try:
                c = dt.date(y, md.month, md.day)
            except ValueError:
                continue                   # 29 Feb in a non-leap baseline year
            out.update(grid.day_index(c + dt.timedelta(days=k)) for k in range(-5, 6))
    return out


@dataclasses.dataclass(frozen=True)
class Scenario:
    name: str
    kind: str                   # the issue's class
    method: str = "numpy"       # numpy | xarray_window | doy_smoothed | doy | xarray_groupby | list_* (LIST_IDIOMS)
    writer: str = "xarray"      # xarray | netCDF4
    reads: str = "window"       # window: the ruling's baseline days | whole: every day of 1992-2002
    skip_every: int = 0         # skip every n-th baseline day (S1 files / S2 time steps)
    lat_shift: int = 0          # wrong region: read and use the box shifted by this many rows
    target_trim: int = 0        # wrong period: drop the last n target days
    baseline_start: dt.date | None = None   # wrong baseline: nothing before this date
    header_only: int = 0        # first n baseline days opened for metadata only
    partial_from: int = 0       # read everything, analyse baseline days from this offset on
    listing: str = "construct"  # S1 discovery: construct names | ls (fs.ls / os.listdir) |
                                # paged (own requests calls, to the end) | paged_stop (own, stops) |
                                # subprocess (one page, in a process the tracer does not see)
    debug_print: bool = False   # print a statistic of everything read (an observation)
    masked: str = ""            # netCDF4's default masked reads, kept as: masked_sink | filled |
                                # getdata | stack (np.stack of the masked days); "" = not used
    options: tuple = ()         # run only through these options (default: all)
    source: str = ""            # how a file reaches h5py (science, #9 17:55Z): path | fileobj | memory; "" = the style's


SCENARIOS = [
    Scenario("complete", "complete"),
    # More than the method needs: data beyond the requirement does no harm.
    Scenario("complete_whole_baseline", "complete", reads="whole"),
    Scenario("complete_xarray", "complete", method="xarray_window"),
    # The ruling: a seasonal climatology covering the window is complete. +-5-day pooling and
    # the 31-day smoothing reach exactly 12 May..20 Sep.
    Scenario("seasonal_doy", "complete", method="doy_smoothed", writer="netCDF4"),
    # The same pooling without the smoothing reaches 27 May..5 Sep only: omitting by extent.
    Scenario("seasonal_doy_narrow", "seasonal_narrow_window", method="doy"),
    # The ruling: labelled by its extent like any run. Exact day-of-year groups, no window.
    Scenario("groupby_leap", "groupby_dayofyear_extent", method="xarray_groupby"),
    Scenario("skip", "skipped_files_or_steps", skip_every=40),
    Scenario("wrong_region", "wrong_subset_region", lat_shift=1),
    Scenario("wrong_period", "wrong_subset_period", target_trim=10),
    Scenario("wrong_baseline", "wrong_subset_baseline", baseline_start=dt.date(1993, 1, 1)),
    Scenario("header_only", "header_only", header_only=30),
    Scenario("partial_use", "full_read_partial_use", partial_from=132),
    # Listing (S1): fs.ls truncates under T and D (the official client), not under
    # T-unpaginated (the shim) or M; the agent's own paging to the end is complete;
    # the agent's own paging that stops early truncates in every option.
    Scenario("listing_ls", "listing_client", listing="ls"),
    Scenario("listing_paged", "complete", listing="paged"),
    Scenario("listing_paged_stop", "truncated_listing_agent", listing="paged_stop"),
    # A listing the in-process hook cannot see (urllib in a subprocess): the gate log can, and the
    # cross-check must say they disagree (science, #9, 1 Nov).
    Scenario("listing_subprocess", "listing_outside_tracer", listing="subprocess", options=("T", "T-unpaginated", "D")),
    Scenario("stress_print", "stress_partial_use_with_print", partial_from=132, debug_print=True),
]
# netCDF4 returns masked arrays by default (lead, 1 Nov): each way an ordinary agent keeps
# them, complete and with skipped days, through T, D and M. Labels from what each script does.
for _flow in ("masked_sink", "filled", "getdata", "stack"):
    SCENARIOS.append(Scenario(f"masked_{_flow}", "complete", masked=_flow, options=("T", "D", "M")))
    SCENARIOS.append(Scenario(f"masked_{_flow}_skip", "skipped_files_or_steps", masked=_flow, skip_every=40,
                              options=("T", "D", "M")))


# The ordinary idioms (science, #2, 07:35Z): one array per day in a list, then one call, as `np.mean([load(d) for d in days],
# axis=0)` does. Worked out from each script: every call reads every baseline day it is given into the threshold, and every
# target day is compared with it, so the whole list is complete, and a list with every 40th day skipped is omitting those days.
LIST_IDIOMS = ("list_mean", "list_nanmean", "list_percentile", "list_concatenate", "list_sum", "list_accumulate")
for _idiom in LIST_IDIOMS:
    SCENARIOS.append(Scenario(_idiom, "complete", method=_idiom, options=("T", "D", "M")))
    SCENARIOS.append(Scenario(f"{_idiom}_skip", "skipped_files_or_steps", method=_idiom, skip_every=40, options=("T", "D", "M")))


# One analysis, its files reaching the decoder three ways, in every option and layout; the labels must be
# identical within each (option, layout, kind) (science, #9 17:55Z, 19:29Z). Under T and T-unpaginated there is
# no local path: "path" is the client's file object there, as the access text says.
SOURCES = ("path", "fileobj", "memory")
for _src in SOURCES:
    SCENARIOS.append(Scenario(f"source_{_src}", "complete", source=_src))
    SCENARIOS.append(Scenario(f"source_{_src}_skip", "skipped_files_or_steps", skip_every=40, source=_src))


def styles_for(option: str) -> tuple[str, ...]:
    # netCDF4-python cannot open file objects; under T an agent uses h5py or xarray/h5netcdf.
    return ("h5py", "xarray") if option in ("T", "T-unpaginated") else ("netCDF4", "h5py", "xarray")


def style_of(option: str, layout: str, k: int) -> str:
    st = styles_for(option)
    return st[(k + LAYOUTS.index(layout)) % len(st)]


# --------------------------------------------------------------- data

@dataclasses.dataclass
class Data:
    """The world a matrix runs on: the data (root, naming, the days each layout holds, the
    layout index) and the instance (box, target, sea cells, the grid index of the files'
    first row and column). Defaults: the synthetic world of this module."""
    root: Path
    s1_days: np.ndarray
    s2_days: np.ndarray
    index: LayoutIndex
    inst: Instance = None
    sea: np.ndarray = None
    origin: tuple = (CROP.lat0, CROP.lon0)     # grid index of file row 0 and column 0
    s1_dir: str = "s1"
    s1_fmt: str = "%Y%m%d-SST-L4.nc"
    s2_rel: str = "s2/sst_s2.nc"
    stamp: str = ""                             # what identifies the data (cache stamp, sha)

    def __post_init__(self):
        if self.inst is None:
            self.inst = INSTANCE
        if self.sea is None:
            self.sea = sea_cells()

    @property
    def target(self) -> tuple:
        return (self.inst.target.start, self.inst.target.end)

    def s1_name(self, day: int) -> str:
        return grid.day_date(int(day)).strftime(self.s1_fmt)


def make_data(root: Path, s1_days=None, s2_days=None) -> Data:
    """The synthetic world, written once under `root` and reused. What identifies it is
    the content of its files (data_digest), never a marker: the layout index and every
    resumed row are bound to that digest. Default days: the pooling superset (#5) and all
    of the target year, in both layouts."""
    extra = list(grid.day_range(dt.date(TARGET[0].year, 1, 1), dt.date(TARGET[0].year, 12, 31)))
    if s1_days is None:
        s1_days = sorted(set(int(d) for d in instance_required.baseline_day_indices()) | set(extra))
    if s2_days is None:
        s2_days = list(grid.day_range(instance_required.BASE_START, dt.date(TARGET[0].year, 12, 31)))
    s1_days, s2_days = np.array(sorted(int(d) for d in s1_days)), np.array(sorted(int(d) for d in s2_days))
    marker = root / "READY"
    # rebuild data written with another compression or for another day range
    made = f"ok deflate4 s1={int(s1_days[0])}..{int(s1_days[-1])} n={s1_days.size} s2={s2_days.size}"
    if not marker.exists() or marker.read_text() != made:
        if root.exists():
            shutil.rmtree(root)
        write_synthetic(root, CROP, s1_days, s2=False)
        write_synthetic(root, CROP, s2_days, s1=False)
        marker.write_text(made)
    files = sorted((root / "s1").glob("*.nc")) + [root / "s2" / "sst_s2.nc"]
    digest = data_digest(root, files)
    idx_path, idx_digest = root / "layout_index.npz", root / "layout_index.sha256"
    index = None
    if idx_path.is_file() and idx_digest.is_file() and idx_digest.read_text() == digest:
        try:
            index = LayoutIndex.load(idx_path)
        except HashlessIndex:           # saved before the hashes were kept (#9): rebuilt, never reused
            index = None
    if index is None:
        index = build_index(root, files)
        index.save(idx_path)
        idx_digest.write_text(digest)
    return Data(root, s1_days, s2_days, index,
                stamp=json.dumps({"made": made, "sha256": digest, "files": len(files)}, sort_keys=True))


def data_digest(root: Path, files) -> str:
    """sha256 over the relative path and the bytes of every data file."""
    root = Path(root)
    h = hashlib.sha256()
    for f in sorted(Path(f) for f in files):
        h.update(str(f.relative_to(root)).encode() + b"\0")
        with open(f, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        h.update(b"\0")
    return h.hexdigest()


# --------------------------------------------------------------- expected (independent)

def expected(sc: Scenario, option: str, layout: str, data: Data) -> dict:
    """Expected loaded and analysed units and the true label: the required part from the ruling,
    the rest from the scenario's parameters."""
    target = data.target
    req_base = ruling_baseline_days(*target)
    req_tgt = set(grid.day_range(*target))
    if sc.reads == "whole":
        script_base = sorted(grid.day_range(*WHOLE_BASELINE))
    else:
        script_base = sorted(req_base)
    if sc.baseline_start:
        first = grid.day_index(sc.baseline_start)
        script_base = [d for d in script_base if d >= first]
    skip = set(script_base[::sc.skip_every][1:]) if sc.skip_every else set()
    tgt = sorted(req_tgt)[: len(req_tgt) - sc.target_trim]
    header = set(script_base[: sc.header_only])
    available = {int(d) for d in (data.s1_days if layout == "S1" else data.s2_days)}
    listing = None
    if layout == "S1" and sc.listing != "construct":
        all_names = sorted(data.s1_name(int(d)) for d in data.s1_days)
        n_listed = len(all_names)
        if sc.listing in ("ls", "subprocess") and option in ("T", "D"):
            n_listed = CFG["page"]                      # one page, as the client asks
        elif sc.listing == "paged_stop" and option != "T-unpaginated":
            n_listed = CFG["page"] * CFG["stop_after_pages"]   # under T-unpaginated the gate merged them
        listed = set(all_names[:n_listed])
        available &= {int(d) for d in data.s1_days if data.s1_name(int(d)) in listed}
        # What the listing stream must show (REST options only; M lists locally). A listing in
        # a subprocess shows nothing there; the gate log has it.
        if option in ("T", "T-unpaginated", "D") and sc.listing != "subprocess":
            truncated = n_listed < len(all_names)
            if sc.listing == "ls":
                attribution = "client" if truncated else None
            else:
                attribution = "agent" if truncated else None
            listing = {"truncated": truncated, "attribution": attribution,
                       "entries_listed": min(n_listed, len(all_names))}
    want = (set(script_base) - skip) | set(tgt)
    loaded_days = (want & available) - header
    analysis_base = (set(script_base[sc.partial_from:]) - skip) & loaded_days
    used_tgt = set(tgt) & loaded_days
    # The output is a mask over the used target days: with none, it has no elements
    # and no baseline value reaches it (a truncated S1 listing lists early years only).
    analysis_used = _method_baseline(sc.method, analysis_base, used_tgt) if used_tgt else set()
    used_days = analysis_used | used_tgt
    inst = data.inst
    lat0 = inst.lat0 + sc.lat_shift
    cells = [(la, lo) for la in range(lat0, inst.lat1 + sc.lat_shift)
             for lo in range(inst.lon0, inst.lon1)]
    req_cells = {(inst.lat0 + int(j), inst.lon0 + int(i)) for j, i in zip(*np.nonzero(data.sea))}
    req_days = req_base | req_tgt
    # D's scripts download every wanted S1 file they found, header-only days included (S2's one file names no
    # day: labeller.ledger_read).
    downloaded = (want & available) if option == "D" and layout == "S1" else set()
    # Scenarios are rectangular (days x cells), so the required, used and loaded units are
    # products: R is in the used units iff its days and its cells are (no unit sets: a real
    # instance has millions of units).
    complete = bool(req_days) and req_days <= used_days and req_cells <= set(cells)
    return {"label": OmissionLabel.COMPLETE if complete else OmissionLabel.OMITTING,
            "used_days": used_days, "loaded_days": loaded_days, "cells": set(cells),
            "req_days": req_days, "req_cells": req_cells, "req_baseline_days": len(req_base),
            "script_base": script_base, "skip": sorted(skip), "tgt": tgt, "header": sorted(header),
            "analysis_base": sorted(analysis_base), "lat0": lat0, "listing": listing,
            # amendment 2: S1 days decoded, downloaded (D) or fetched (T, T-unpaginated: every file the script
            # opened, header-only ones too) outside the required days; S2's one file is always listed: none
            "beyond_days": (sorted((loaded_days | downloaded | (want & available if option in ("T", "T-unpaginated")
                                                                else set())) - req_days)
                            if layout == "S1" else []),
            "listing_disagrees": (sc.listing == "subprocess" and layout == "S1"
                                  and option in ("T", "T-unpaginated", "D"))}


def _yday(d: int) -> int:
    return grid.day_date(int(d)).timetuple().tm_yday


def _method_baseline(method: str, base: set, tgt: set) -> set:
    """Baseline days whose values reach the target-period output, by method."""
    if method in ("numpy", "xarray_window") or method in LIST_IDIOMS:  # one threshold per cell from every baseline day used
        return set(base)
    if method == "xarray_groupby":            # groupby dayofyear: only the matching days of year
        tdoy = {_yday(t) for t in tgt}
        return {d for d in base if _yday(d) in tdoy}
    if method == "doy":                       # +-5-day window, circular over 366 day-of-year positions
        t0 = np.array(sorted(_yday(t) - 1 for t in tgt))
        out = set()
        for d in base:
            k = _yday(d) - 1
            if len(t0) and np.min(np.minimum((k - t0) % 366, (t0 - k) % 366)) <= 5:
                out.add(d)
        return out
    if method == "doy_smoothed":              # +-5 pooling, then a 31-day mean: +-20 month/day positions
        t0 = np.array(sorted(month_day_position(grid.day_date(int(t))) for t in tgt))
        out = set()
        for d in base:
            k = month_day_position(grid.day_date(int(d)))
            if len(t0) and np.min(np.minimum((k - t0) % 366, (t0 - k) % 366)) <= 20:
                out.add(d)
        return out
    raise ValueError(method)


def expected_vs(exp: dict, ext, data: Data, days_key: str) -> tuple[np.ndarray, np.ndarray]:
    """(expected, got) boolean arrays on one canonical axis, the required space: every
    required day x the instance box, restricted to sea cells. Expected from exp[days_key] x
    exp["cells"], got from the extent (whose parts may carry fewer days)."""
    req = np.array(sorted(exp["req_days"]), np.int64)
    box = ext.baseline.box
    sea = np.asarray(data.sea, bool)
    cm = np.zeros(box.shape, bool)
    for la, lo in exp["cells"]:
        j, i = la - box.lat0, lo - box.lon0
        if 0 <= j < box.shape[0] and 0 <= i < box.shape[1]:
            cm[j, i] = True
    days = np.fromiter(exp[days_key], np.int64, len(exp[days_key]))
    want = np.isin(req, days)[:, None, None] & (cm & sea)[None]
    got = np.zeros((req.size, *box.shape), bool)
    for part in (ext.baseline, ext.target):
        pos = np.searchsorted(req, part.days)
        ok = (pos < req.size) & (req[np.minimum(pos, req.size - 1)] == part.days)
        got[pos[ok]] |= part.mask[ok]
    got &= sea[None]
    return want, got


def units_of(mask_extent) -> set:
    out = set()
    for e in (mask_extent.baseline, mask_extent.target):
        d, y, x = np.nonzero(e.mask)
        for a, b, c in zip(e.days[d], y + e.box.lat0, x + e.box.lon0):
            out.add((int(a), (int(b), int(c))))
    return out


def in_space(units: set, req: set) -> set:
    days = {d for d, _ in req}
    cells = {c for _, c in req}
    return {(d, c) for d, c in units if d in days and c in cells}


# --------------------------------------------------------------- one run

BOOT = ("import icsa.instruments.hooks as h; h.install_from_env(); import runpy, sys; "
        "runpy.run_path(sys.argv[1], run_name='__main__')")


def agent_cfg(option, layout, sc: Scenario, data: Data, exp: dict, style: str, *, out: str,
              download_dir: str, access: str) -> dict:
    """The scripted agent's configuration for one cell, on either access path."""
    inst = data.inst
    j0 = exp["lat0"] - data.origin[0]
    i0 = inst.lon0 - data.origin[1]
    rows = inst.lat1 - inst.lat0
    cols = inst.lon1 - inst.lon0
    return {
        "option": option, "layout": layout, "style": style, "root": str(data.root), "out": out,
        "access": access, "s1_dir": data.s1_dir, "s1_fmt": data.s1_fmt, "s2_rel": data.s2_rel,
        "listing": sc.listing, "page_limit": CFG["page"], "stop_after_pages": CFG["stop_after_pages"],
        "download_dir": download_dir,
        "read_box": [j0, j0 + rows, i0, i0 + cols],
        "use_box": [j0, j0 + rows, i0, i0 + cols],
        "lat_origin": data.origin[0], "lon_origin": data.origin[1],
        "baseline_days": exp["script_base"], "skip_days": exp["skip"], "target_days": exp["tgt"],
        "header_only_days": exp["header"], "analysis_baseline_days": exp["analysis_base"],
        "method": sc.method, "writer": sc.writer, "debug_print": sc.debug_print, "masked": sc.masked,
        "source": sc.source,
    }


def required_of(data: Data, exp: dict):
    """The instance's required extent (#5), through its loader, which raises if #5's count of
    baseline days differs from the one computed in expected() from the ruling."""
    i = data.inst
    t0, t1 = data.target
    return instance_load.required_extent(
        {"instance": {"instance_id": i.instance_id, "lat0": i.lat0, "lat1": i.lat1, "lon0": i.lon0, "lon1": i.lon1,
                      "target": [t0.isoformat(), t1.isoformat()]},
         "baseline_days": exp["req_baseline_days"]}, data.sea)


def run_case(option: str, layout: str, k: int, sc: Scenario, data: Data, work: Path) -> dict:
    case = f"{option}__{layout}__{sc.name}"
    wd = work / "runs" / case
    if wd.exists():
        shutil.rmtree(wd)
    (wd / "trace").mkdir(parents=True)
    (wd / "platform").mkdir()
    script = wd / "agent.py"
    shutil.copy(Path(__file__).with_name("validate_agent.py"), script)
    exp = expected(sc, option, layout, data)
    if sc.kind == "complete" and exp["label"] != OmissionLabel.COMPLETE:
        # the fixture lacks data a complete run needs: an error in the suite, not a result
        raise RuntimeError(f"{option}/{layout}/{sc.name}: the synthetic data cannot support a complete run")
    style = "netCDF4" if sc.masked else "h5py" if sc.source else style_of(option, layout, k)
    cfg = agent_cfg(option, layout, sc, data, exp, style, out=str(wd / "output"),
                    download_dir=str(wd / "downloads"), access="sim")
    env = dict(os.environ, SCEN_CFG=json.dumps(cfg), ICSA_TRACE_DIR=str(wd / "trace"),
               ICSA_OUTPUT_DIR=str(wd / "output"))
    if option in ("M", "M+"):
        env["ICSA_MOUNT_PATH"] = str(data.root)   # as the sandbox does: the dataset's local path is the mount
    if sc.listing == "subprocess":                # a child traced as in the sandbox, whose site hook this path does not have
        (wd / "site").mkdir(exist_ok=True)
        (wd / "site" / "sitecustomize.py").write_text("import icsa.instruments.hooks as h\nh.install_from_env()\n")
        env["PYTHONPATH"] = str(wd / "site") + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-c", BOOT, str(script)]
    strace = shutil.which("strace") if option in ("D", "M", "M+") else None
    if strace:
        cmd = [strace, "-f", "-y", "-e", "trace=openat,read,pread64,lseek,close",
               "-o", str(wd / "platform" / "strace.txt")] + cmd
    srv = None
    t0 = time.time()
    try:
        if option in ("T", "T-unpaginated", "D"):
            srv = RangeServer(data.root, wd / "platform" / "proxy.jsonl",
                              merge_pages=option == "T-unpaginated").start()
            cfg["url"] = srv.url
            env["SCEN_CFG"] = json.dumps(cfg)
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, cwd=wd)
    finally:
        if srv is not None:
            srv.stop()
    (wd / "stdout.txt").write_text(p.stdout)
    (wd / "stderr.txt").write_text(p.stderr)
    row = {"case": case, "option": option, "layout": layout, "scenario": sc.name, "kind": sc.kind,
           "style": style, "method": sc.method, "writer": sc.writer, "exit": p.returncode,
           "wall_s": round(time.time() - t0, 1), "true": exp["label"].value}
    if p.returncode != 0:
        row["error"] = p.stderr[-2000:]
        return row
    required = required_of(data, exp)
    roots = [wd / "downloads"] if option == "D" else [data.root] if option in ("M", "M+") else []
    lab = label_run(option, wd / "trace", wd / "output", data.index, required, platform_dir=wd / "platform",
                    local_roots=roots, dir_sizes={data.s1_dir: int(len(data.s1_days))},
                    code_text=script.read_text())          # the entry point as the campaign calls it
    an = lab.analysis
    row.update({"label": an.label.value, "raw_label": an.flags.get("raw_label"), "reasons": an.reasons, "coverage": an.coverage,
                "coverage_upper": an.coverage_upper, "flags": _jsonable(an.flags), "notes": an.notes,
                "observed": lab.observed})
    # Required space only: the instance's sea cells and required days (R has no land cells).
    want_a, got_a = expected_vs(exp, an.analysed, data, "used_days")
    want_l, got_l = expected_vs(exp, an.loaded, data, "loaded_days")
    row["analysed_exact"] = bool(np.array_equal(want_a, got_a))
    row["analysed_missing"] = int((want_a & ~got_a).sum())
    row["analysed_extra"] = int((got_a & ~want_a).sum())
    row["loaded_exact"] = bool(np.array_equal(want_l, got_l))
    if an.bound is None:
        row["bound_sound"] = True
    else:
        _, got_b = expected_vs(exp, an.bound, data, "used_days")
        row["bound_sound"] = bool(not (want_a & ~got_b).any())
    row.update(_read_check(lab, exp, data))
    row.update(_listing_check(lab, exp["listing"], layout, data))
    row.update(identity_fields(lab, data))
    row["listing_disagrees_want"] = exp["listing_disagrees"]
    # Keep the disk bounded: what the row needs has been read.
    shutil.rmtree(wd / "downloads", ignore_errors=True)
    (wd / "platform" / "strace.txt").unlink(missing_ok=True)
    return row


def _listing_check(lab, want: dict | None, layout: str, data: Data) -> dict:
    """The listing summary against what the script was written to do (expected())."""
    got = (lab.listing or {}).get(data.s1_dir)
    if want is None:
        # no REST listing of S1 expected: none may appear (construct, S2, M)
        return {"listing_ok": got is None, "listing": None if got is None else got.to_json()}
    if got is None:
        return {"listing_ok": False, "listing": None, "listing_want": want}
    ok = (got.truncated == want["truncated"] and got.attribution == want["attribution"]
          and got.entries_listed == want["entries_listed"])
    return {"listing_ok": ok, "listing": got.to_json(), "listing_want": want}


def _read_check(lab, exp: dict, data: Data) -> dict:
    """lab.read, from the ledger on every run, against what the script read. The byte logs
    (proxy log, strace) are never the source of `read`: they are the outside view, and what they
    delivered must contain what was decoded."""
    out = {"read_source": None if lab.read is None else lab.read.source,
           "read_beyond_exact": lab.read is not None and lab.read.beyond_days == exp["beyond_days"]}
    # the read extent itself, unit by unit, against the units the script decoded (its loaded days over its cells)
    if lab.read is None:
        out["read_exact"] = False
    else:
        want_r, got_r = expected_vs(exp, lab.read.extent, data, "loaded_days")
        out["read_exact"] = bool(np.array_equal(want_r, got_r))
        out["read_missing"] = int((want_r & ~got_r).sum())
        out["read_extra"] = int((got_r & ~want_r).sum())
    if lab.fetched is not None:
        out["fetched_units"] = int(lab.fetched.extent.baseline.count() + lab.fetched.extent.target.count())
        out["fetched_bytes"] = lab.fetched.bytes_total
    if lab.delivered is None:
        out["read_superset"] = None
        out["read_note"] = "bytes delivered not observed (" + ("strace unavailable" if lab.option != "T" else "no log") + ")"
        return out
    want_l, got_d = expected_vs(exp, lab.delivered.extent, data, "loaded_days")
    out["read_superset"] = bool(not (want_l & ~got_d).any())
    out["delivered_extra"] = int((got_d & ~want_l).sum())
    out["read_bytes"] = lab.delivered.bytes_total
    return out


def signature(ext, data: Data) -> dict:
    """An extent restricted to the required space (sea cells), as a count and a hash: two
    paths agree on an extent iff their signatures are equal."""
    sea = np.asarray(data.sea, bool)
    h = hashlib.sha256()
    n = 0
    for part in (ext.baseline, ext.target):
        m = part.mask & sea[None]
        h.update(np.asarray(part.days, np.int64).tobytes())
        h.update(np.packbits(m).tobytes())
        n += int(m.sum())
    return {"units": n, "sha256": h.hexdigest()}


def none_fields(lab) -> list[str]:
    """Which of read, read_beyond_days and listing are None. All-None is the failure of a run the
    tracer did not reach; it looks like success (science, #9, 1 Nov). M lists locally: no listing."""
    out = []
    if lab.read is None:
        out += ["read", "read_beyond_days"]
    if lab.option in ("T", "T-unpaginated", "D") and lab.listing is None:
        out.append("listing")
    return out


def identity_fields(lab, data: Data) -> dict:
    """What the two paths of a confirmation must agree on, as one row's fields."""
    an = lab.analysis
    return {"analysed": signature(an.analysed, data), "loaded": signature(an.loaded, data),
            "read": None if lab.read is None else signature(lab.read.extent, data),
            "read_beyond_days": None if lab.read is None else lab.read.beyond_days,
            "listing_summary": None if lab.listing is None else {k: v.to_json() for k, v in sorted(lab.listing.items())},
            "listing_disagrees": an.flags.get("listing_disagrees"),
            "decoded_not_delivered": an.flags.get("decoded_not_delivered"),
            "delivered_not_decoded": an.flags.get("delivered_not_decoded"),
            "cross_check_source": an.flags["cross_check"]["source"],
            "cross_check_unknown_ids": an.flags["cross_check"]["unknown_file_ids"],
            "none_fields": none_fields(lab)}


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


# --------------------------------------------------------------- report

# A case in any of these fails the matrix. `icsa.dossier.criteria.FAIL_LISTS` reads the same summary for criterion 2; a list
# it gates on is here too, or the command would pass a matrix the dossier fails (b1 #6: a wrong analysed extent exited 0).
MANDATORY_LISTS = ("failed", "omitting_called_complete", "complete_not_called_complete", "analysed_not_exact_resolved",
                   "loaded_not_exact", "bound_unsound", "read_not_superset", "read_not_observed", "read_beyond_not_exact",
                   "read_not_exact", "none_fields", "listing_disagrees_unexpected", "listing_mismatch",
                   "decoded_not_delivered", "cross_check_not_observed", "source_variants_disagree")


def exit_status(summ: dict) -> int:
    """The command's exit status: 1 if a mandatory list has an entry or the core's unknown share is over its limit."""
    return 1 if any(summ[k] for k in MANDATORY_LISTS) or summ["unknown_share_core"] > 0.10 else 0


def routed(r: dict) -> bool:
    """19(a): the instrument said omitting, and it was routed to inspection as unknown because its only cause was loaded_not_used."""
    return r.get("label") == "unknown" and r.get("raw_label") == "omitting" and "inspection:loaded_not_used" in (r.get("notes") or [])


def judged(rows: list[dict]) -> list[dict]:
    """The rows as the matrix judges them (science, #2, 2 Nov 17:21Z): a routed run on its raw label, every other on its label."""
    return [{**r, "label": r["raw_label"], "routed": True} if routed(r) else {**r, "routed": False} for r in rows]


def summarise(rows: list[dict]) -> dict:
    ok = judged([r for r in rows if "label" in r])
    by_true: dict[str, dict[str, int]] = {}
    for r in ok:
        by_true.setdefault(r["true"], {}).setdefault(r["label"], 0)
        by_true[r["true"]][r["label"]] += 1
    core = [r for r in ok if not r["kind"].startswith("stress")]
    unknown_share = sum(r["label"] == "unknown" for r in core) / len(core) if core else float("nan")      # the instrument's own unknowns only
    resolved = [r for r in ok if r["label"] != "unknown"]
    cells = sorted({(r["option"], r["layout"]) for r in ok})
    return {
        "routed_cases": [r["case"] for r in ok if r["routed"]],
        "routed_share_core": sum(r["routed"] for r in core) / len(core) if core else float("nan"),
        "by_cell": {f"{o}/{la}": _cell([r for r in core if (r["option"], r["layout"]) == (o, la)]) for o, la in cells},
        "runs": len(rows), "failed": [r["case"] for r in rows if "label" not in r],
        "by_true_label": by_true,
        "omitting_called_complete": [r["case"] for r in ok if r["true"] == "omitting" and r["label"] == "complete"],
        "complete_not_called_complete": [r["case"] for r in ok if r["true"] == "complete" and r["label"] != "complete"],
        "unknown_share_core": unknown_share,
        "unknown_cases": [r["case"] for r in ok if r["label"] == "unknown"],
        "analysed_not_exact_resolved": [r["case"] for r in resolved if not r["analysed_exact"]],
        "loaded_not_exact": [r["case"] for r in ok if not r["loaded_exact"]],
        "bound_unsound": [r["case"] for r in ok if not r["bound_sound"]],
        "read_not_superset": [r["case"] for r in ok if r.get("read_superset") is False],
        # lab.read is the ledger's, and the scripted reads are the truth: every run has one
        "read_not_observed": [r["case"] for r in ok if "read" in r.get("none_fields", ["read"])],
        "read_beyond_not_exact": [r["case"] for r in ok if not r.get("read_beyond_exact")],
        "read_not_exact": [r["case"] for r in ok if not r.get("read_exact")],
        "none_fields": [r["case"] for r in ok if r.get("none_fields")],
        "listing_disagrees_unexpected": [r["case"] for r in ok
                                         if r.get("listing_disagrees") != r.get("listing_disagrees_want")
                                         and r.get("cross_check_source") == "gate"],
        "listing_disagrees": [r["case"] for r in ok if r.get("listing_disagrees")],
        "decoded_not_delivered": [r["case"] for r in ok if r.get("decoded_not_delivered")],
        "delivered_not_decoded": [r["case"] for r in ok if r.get("delivered_not_decoded")],
        "cross_check_not_observed": [r["case"] for r in ok if r.get("cross_check_source") is None],
        "listing_mismatch": [r["case"] for r in ok if r.get("listing_ok") is False],
        "tracer_internal_errors": [r["case"] for r in ok
                                   if ((r.get("flags") or {}).get("counts") or {}).get("internal_error")],
        "bypass_scan_hits": [r["case"] for r in ok if (r.get("flags") or {}).get("bypass_scan")],
        "source_variants_disagree": source_variants_disagree(ok),
        "unidentified_source_share_by_option": {
            o: (sum(bool((r.get("flags") or {}).get("unidentified_source")) for r in ok if r["option"] == o)
                / max(1, sum(r["option"] == o for r in ok))) for o in OPTIONS},
        "by_scenario": {sc.name: _tally([r for r in ok if r["scenario"] == sc.name]) for sc in SCENARIOS},
        "by_option": {o: {"runs": sum(r["option"] == o for r in ok),
                          "omitting_called_complete": sum(r["option"] == o and r["true"] == "omitting"
                                                          and r["label"] == "complete" for r in ok),
                          "unknown": sum(r["option"] == o and r["label"] == "unknown" for r in ok)}
                      for o in OPTIONS},
    }


def source_variants_disagree(rows: list[dict]) -> list[str]:
    """(option, layout, kind) groups of the source_* scenarios whose labels differ: the same analysis, its files
    reaching the decoder by path, file object or memory, must get the same label in every option."""
    groups: dict[tuple, dict[str, str]] = {}
    for r in rows:
        sc = r.get("scenario", "")
        if not sc.startswith("source_"):
            continue
        kind = "skip" if sc.endswith("_skip") else "complete"
        groups.setdefault((r["option"], r["layout"], kind), {})[sc] = r["label"]
    return [f"{o}__{lay}__{kind}: {labels}" for (o, lay, kind), labels in sorted(groups.items())
            if len(set(labels.values())) > 1]


def _cell(rows: list[dict]) -> dict:
    n = len(rows)
    own, rt = sum(r["label"] == "unknown" for r in rows), sum(r["routed"] for r in rows)
    return {"runs": n, "own_unknown": own, "own_unknown_share": own / n if n else float("nan"), "routed": rt, "routed_share": rt / n if n else float("nan")}


def _tally(rows: list[dict]) -> dict:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        t = out.setdefault(f"true_{r['true']}", {})
        t[r["label"]] = t.get(r["label"], 0) + 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4, help="parallel runs (host rule: at most 4)")
    ap.add_argument("--only", default=None, help="substring filter on option__layout__scenario")
    ap.add_argument("--resume", action="store_true",
                    help="reuse cells already finished with the same code and data (row.json)")
    ap.add_argument("--commit", default=None, help="the git commit the code was taken from (recorded)")
    ap.add_argument("--confirmation", type=Path, default=None,
                    help="confirm_summary.json of a real-path confirmation (icsa.instruments.confirm)")
    ap.add_argument("--data", type=Path, default=None,
                    help="where the synthetic S1/S2 are cached (default: WORK/data-method-window)")
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=True)
    data = make_data(a.data or a.work / "data-method-window")
    cases = [(o, lay, k, sc) for o in OPTIONS for lay in LAYOUTS for k, sc in enumerate(SCENARIOS)
             if not sc.options or o in sc.options]
    if a.only:
        cases = [c for c in cases if a.only in f"{c[0]}__{c[1]}__{c[3].name}"]
    confirmation = json.loads(a.confirmation.read_text()) if a.confirmation else None
    ident = run_identity(cases, data, confirmation)
    code = code_stamp()
    stamp = cell_stamp(code, data)
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda c: _safe(c, data, a.work, stamp, a.resume), cases))
    summ = summarise(rows)
    if code_stamp()["instruments_sha256"] != code["instruments_sha256"]:
        # the rows may come from two versions of the code: none of them is evidence
        summ["failed"].append("the code changed while the matrix ran")
    summ["data"] = json.loads(data.stamp) if data.stamp.startswith("{") else data.stamp
    rb = sorted(ruling_baseline_days(*data.target))
    summ["baseline"] = [str(grid.day_date(rb[0])), str(grid.day_date(rb[-1]))]
    summ["required_baseline_days"] = len(rb)
    summ.update(ident)
    summ.update(code)
    summ["commit"] = a.commit
    summ["resumed_cells"] = sum(1 for r in rows if r.get("resumed"))
    (a.work / "rows.json").write_text(json.dumps(rows, indent=1, default=str))
    (a.work / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps(summ, indent=1, default=str))
    return exit_status(summ)


def cell_stamp(code: dict, data: Data) -> str:
    """What a cell's row depends on: every code file a cell runs and the environment
    (code_stamp), the required-extent source, and the content of the data (make_data)."""
    return json.dumps({"code": code["instruments_sha256"], "req": code["required_extent_source"],
                       "data": data.stamp}, sort_keys=True)


def _safe(c, data, work, stamp: str, resume: bool):
    """One cell. Its row is saved in the cell's directory with the stamp of the code and
    data that produced it, so an interrupted matrix can resume (--resume) without rerunning
    finished cells, and never mixes rows of another code or data version."""
    case = f"{c[0]}__{c[1]}__{c[3].name}"
    saved = work / "runs" / case / "row.json"
    if resume and saved.is_file():
        try:
            rec = json.loads(saved.read_text())
            if rec.get("stamp") == stamp and "label" in rec.get("row", {}):
                return dict(rec["row"], resumed=True)
        except ValueError:
            pass
    try:
        row = run_case(*c, data, work)
    except Exception as e:  # noqa: BLE001
        row = {"case": case, "error": repr(e), "kind": c[3].kind, "true": "?"}
    if "label" in row:
        saved.write_text(json.dumps({"stamp": stamp, "row": row}, default=str))
    return row


# ---------------------------------------------------------------- what was run

def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


REPO = Path(__file__).resolve().parents[2]
# What a matrix cell runs: the matrix (expected extents; labelling through labeller and
# analyse), the scripted agent, the tracer it boots, and the simulated access paths.
CELL_ENTRY = ("icsa/instruments/validate.py", "icsa/instruments/validate_agent.py",
              "icsa/instruments/hooks.py", "icsa/instruments/sim/httpserve.py",
              "icsa/instruments/sim/rangefs.py")
# What a real-path confirmation runs besides: its runner, the instrumentation slot it
# builds, and (through their imports) the sandbox and the oracle's data configuration.
CONFIRM_ENTRY = CELL_ENTRY + ("icsa/instruments/confirm.py", "icsa/instruments/sandbox_dir.py")
# The libraries whose behaviour the tracer and the readers depend on.
CELL_LIBRARIES = ("numpy", "h5py", "netCDF4", "xarray", "h5netcdf", "fsspec", "pandas")


def _module_file(root: Path, dotted: str) -> Path | None:
    p = root.joinpath(*dotted.split("."))
    if (p / "__init__.py").is_file():
        return p / "__init__.py"
    if p.with_suffix(".py").is_file():
        return p.with_suffix(".py")
    return None


def code_files(root: Path | None = None, entries: tuple[str, ...] = CELL_ENTRY) -> list[str]:
    """Every icsa file a matrix cell runs (or, with CONFIRM_ENTRY, a confirmation cell):
    the entry points and every sim/ module, then, transitively, every icsa module any of
    them imports (import statements anywhere in the file, inside functions too), with the
    __init__ of each package on the way."""
    root = Path(root or REPO)
    todo = [root / e for e in entries] + sorted((root / "icsa" / "instruments" / "sim").glob("*.py"))
    seen: set[Path] = set()
    while todo:
        f = todo.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        pkg = list(f.relative_to(root).parent.parts)
        todo += [root.joinpath(*pkg[:k], "__init__.py") for k in range(1, len(pkg) + 1)]
        for node in ast.walk(ast.parse(f.read_text(), filename=str(f))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = pkg[:len(pkg) - node.level + 1] if node.level else []
                mod = ".".join(base + ([node.module] if node.module else []))
                names = [mod] + [f"{mod}.{a.name}" for a in node.names]
            else:
                continue
            for n in names:
                parts = n.split(".")
                if parts[0] != "icsa":
                    continue
                todo += [m for k in range(1, len(parts) + 1)
                         if (m := _module_file(root, ".".join(parts[:k]))) is not None]
    return sorted(str(f.relative_to(root)) for f in seen)


def _library_versions() -> dict:
    out = {}
    for name in CELL_LIBRARIES:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = None
    return out


def _environment(root: Path) -> dict:
    lock = root / "uv.lock"
    return {"python": sys.version.split()[0], "libraries": _library_versions(),
            "uv_lock_sha256": _sha256(lock) if lock.is_file() else None}


def _files_sha256(root: Path, files: list[str], env: dict) -> str:
    h = hashlib.sha256()
    for rel in files:
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes() + b"\0")
    h.update(json.dumps(env, sort_keys=True).encode())
    return h.hexdigest()


def confirm_stamp(root: Path | None = None) -> str:
    """Hash of the code a real-path confirmation runs (code_files with CONFIRM_ENTRY: the
    matrix's code, the runner, the instrumentation slot, the sandbox) and its environment.
    A confirmation confirms only the code it ran: validate checks this hash too."""
    root = Path(root or REPO)
    return _files_sha256(root, code_files(root, CONFIRM_ENTRY), _environment(root))


def code_stamp(root: Path | None = None) -> dict:
    """Hashes of the code a matrix cell runs (code_files), of the environment it runs in
    (Python, the data libraries, uv.lock) and of the required-extent definition."""
    root = Path(root or REPO)
    files = code_files(root)
    env = _environment(root)
    req = root / "icsa" / "instances" / "required.py"
    manifest = root / "data" / "instances" / "instances.json"
    return {"instruments_sha256": _files_sha256(root, files, env), "code_files": files, "environment": env,
            "required_extent_source": {"module": "icsa.instances.required",
                                       "function": "method_baseline_day_indices",
                                       "sha256": _sha256(req),
                                       "manifest": "data/instances/instances.json",
                                       "manifest_sha256": _sha256(manifest) if manifest.is_file() else None}}


GATES_LOCAL, GATES_CONFIRMED = "local-sim", "local-sim+real-confirmed"


def run_identity(cases, data: Data, confirmation: dict | None = None) -> dict:
    """baseline_window, data_kind and gates, computed from what this run did.

    gates is exactly "local-sim" (a local Range server and local files, not the sandbox's
    gates), or "local-sim+real-confirmed" when a real-path confirmation
    (icsa.instruments.confirm) of the same code (instruments_sha256 and confirm_sha256) ran
    its complete set on a pilot instance with no difference between the two paths and every
    listing and label as the scenario says.
    real_confirmation is exactly {"runs": <int>, "differences": [...], "none_fields": [...]} (runs
    0 before the set ran, or when it ran other code): none_fields are the fields a real run left
    None, and empty is required. Everything else goes into gates_detail."""
    rb = ruling_baseline_days(*data.target)
    five = {int(d) for d in instance_required.method_baseline_day_indices(*data.target)}
    whole = set(grid.day_range(*WHOLE_BASELINE))
    window = "method" if rb == five else ("whole" if rb == whole else "custom")
    filtered = {fl.filtered for fl in data.index.layouts.values()}
    kind = "compressed" if filtered == {True} else "uncompressed" if filtered == {False} else "mixed"
    options = sorted({c[0] for c in cases})
    paths = {}
    for o in options:
        if o in ("T", "T-unpaginated", "D"):
            paths[o] = "local Range HTTP server (icsa.instruments.sim.httpserve), Onedata-style paging"
        else:
            paths[o] = "local files (no oneclient mount)"
    gates = GATES_LOCAL
    real = {"runs": 0, "differences": [], "none_fields": []}
    detail = ["matrix on the local path: T, T-unpaginated and D through a local Range HTTP server, "
              "M and M+ from local files"]
    if confirmation is None:
        detail.append("real-path confirmation: not run")
    else:
        c = confirmation
        runs, diffs = c.get("runs"), c.get("differences")
        problems = []
        if c.get("instruments_sha256") != code_stamp()["instruments_sha256"]:
            problems.append("it ran other code (instruments_sha256 differs), so it confirms nothing here")
        elif c.get("confirm_sha256") != confirm_stamp():
            problems.append("its runner or the sandbox code changed since (confirm_sha256 differs), "
                            "so it confirms nothing here")
        else:
            real = {"runs": runs if isinstance(runs, int) and not isinstance(runs, bool) else 0,
                    "differences": list(diffs) if isinstance(diffs, list) else
                    [{"field": "differences", "error": "the confirmation has no differences list"}],
                    "none_fields": list(c.get("none_fields") or []) if "none_fields" in c else
                    [{"field": "none_fields", "error": "the confirmation has no none_fields list"}]}
        if c.get("pilot") is not True:
            problems.append(f"instance {c.get('instance')} is not a pilot instance")
        if not c.get("complete_set"):
            problems.append("the set is incomplete")
        if not real["runs"]:
            problems.append("no runs")
        if real["differences"]:
            problems.append(f"{len(real['differences'])} difference(s) between the two paths")
        if real["none_fields"]:
            problems.append(f"{len(real['none_fields'])} field(s) None on a real run")
        if c.get("expectation_failures"):
            problems.append(f"{len(c['expectation_failures'])} listing or label expectation(s) failed: "
                            + json.dumps(c["expectation_failures"], default=str)[:2000])
        if not problems:
            gates = GATES_CONFIRMED
        detail.append(f"real-path confirmation on instance {c.get('instance')} (image {c.get('image')}, "
                      f"{runs} runs): " + ("confirmed, every cell identical" if not problems
                                          else "; ".join(problems)))
    return {"baseline_window": window, "data_kind": kind, "gates": gates, "gates_detail": ". ".join(detail),
            "gates_by_option": paths, "real_confirmation": real,
            "target": [str(data.target[0]), str(data.target[1])]}


if __name__ == "__main__":
    sys.exit(main())
