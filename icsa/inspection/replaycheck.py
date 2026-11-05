"""The dependence test by replay (#76, rubric §8): a check reported beside the inspection labels.

    A report, not a go criterion: it blocks nothing and changes no label.
    Positive evidence shows that some values of that group are used, not that every required cell-day is.
    No change is never taken as proof of omission; no verdict that a run omits anything exists here.

For a seeded sample of inspection-resolved runs, a run's recorded code cells are replayed (no model) through the real harness
and sandbox on the local simulation, once on the real data (the control: it must reproduce the run's own saved mask exactly,
else the run is `not_replayable` and no perturbed arm runs) and once per group on a copy of the data that differs in that ONE
group. The groups are the reduced set: the target, space, and 2 seeded baseline years (5 replays per run counting the control).
`--groups all` (the rubric's 13) and explicit group lists exist for validation.

Per group the outcome compares the replayed mask's change with the study's own reference detector's change under the same
perturbation:

    positive          the replayed mask changes in at least one cell-day where the reference's also changes
    change_elsewhere  it changes, but only where the reference's does not
    no_change         it does not change (never proof of anything)
    not_tested        the reference did not move, or the arm failed (a cap, a crash, an invalid mask): no evidence

Perturbation (scheme "v1", fixed before any replay from the reference alone, recorded in every result). One group at a time, on
the group's REQUIRED sea cells only, as an additive offset of delta_k kelvin (a few K: agent sanity checks stay quiet):

    baseline year Y   +delta on every required baseline day of year Y. Only a positive offset moves the reference (it pushes the
                      day-of-year 90th percentile towards the 99th of the other years); a negative one moves it about one rank.
    target            +delta on every required target day.
    space             a seeded box of the instance's sea cells, on every required day: -delta on baseline days and +delta on
                      target days. The SAME offset on every day of a box would cancel (the detector compares each cell with
                      its own baseline percentile: threshold, climatology and target all shift together), so the reference
                      would never move and the group would always be `not_tested`.

On an event-free instance the baseline groups cannot move the reference: they are `not_tested` whatever is done.

The data copy changes only the group's files: S1 rewrites the group's day files (new inodes) and hard-links the rest; S2 is a full
private copy of the one file, edited in place, deleted after the arm. A file that is hard-linked is NEVER opened for writing: it
would change every lane's copy.

Sample: one fixed, ordered, append-only plan. The pilot's resolved runs come first (up to `pilot_per_option` per option,
oversampling `complete`), then the main block's resolved runs balanced per option x layout and oversampled the same way, in a
seeded order. Runs that arrive later are appended in later segments; what is already in the plan never moves. Progress is per run
(a result file each), the run works through the plan in order and can be stopped and resumed anywhere. What the run did not reach is a
stated limitation of the check, and the summary says how far it got.

    python -m icsa.inspection.replaycheck plan    --decisions D --population P --seed S --out OUT
    python -m icsa.inspection.replaycheck run     --out OUT --scratch DIR --data-root DIR [--jobs N] [--limit N]
    python -m icsa.inspection.replaycheck summary --out OUT
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

FORMAT_PLAN = "icsa-replaycheck-plan-v1"
FORMAT_RUN = "icsa-replaycheck-run-v1"
FORMAT_SUMMARY = "icsa-replaycheck-summary-v1"
SCHEME = "v1"

# ---- the vocabulary. There is no run-level verdict about omission in it, and a test asserts that.
OUTCOMES = ("positive", "change_elsewhere", "no_change", "not_tested")
NOT_TESTED_REASONS = ("reference_did_not_move", "arm_not_ok", "perturbation_unverified")
RUN_STATUSES = ("replayed", "not_replayable", "infra")
ARM_STATUSES = ("ok", "capped", "no_mask", "cells_differ", "infra")
CONTROL_STATES = ("reproduced", "not_reproduced", "not_run")

REPORT_NOTE = "A report beside the labels: it is not a go criterion, blocks nothing and changes no label."
LIMIT_NOTE = ("Positive evidence shows that some values of that group are used, not that every required cell-day is. "
              "No change is never taken as proof of omission, and no verdict that a run omits anything exists in this check.")
REACH_NOTE = "What the replay did not reach is a stated limitation of this check."

BASELINE_YEARS = tuple(range(1992, 2003))
LABELS = ("complete", "omitting")
DEFAULT_DELTA_K = 3.0
DEFAULT_SPACE_FRAC = 0.5
DEFAULT_PILOT_PER_OPTION = 4
DEFAULT_COMPLETE_WEIGHT = 2
LOCAL_UPSTREAM_ADDRS = ("host-17.invalid", "localhost", "localhost")


class PerturbationError(RuntimeError):
    """A perturbation could not be made or verified (loud: the arm is `not_tested`, never silently skipped)."""


class LocalOnlyError(RuntimeError):
    """A data configuration that is not the local simulation was offered; nothing may read site_g or site_f."""


class ScratchError(RuntimeError):
    """The scratch directory cannot do its job (too little room, another filesystem, not private)."""


# ----------------------------------------------------------------------------------------------------------- groups
def baseline_group(year: int) -> str:
    return f"baseline:{int(year)}"


def group_kind(group: str) -> str:
    return "baseline" if group.startswith("baseline:") else group


def all_groups() -> list[str]:
    return [baseline_group(y) for y in BASELINE_YEARS] + ["target", "space"]


def select_groups(mode: str, seed, run_key: str, *, n_years: int = 2, explicit=None) -> list[str]:
    """The groups replayed for one run. "reduced" (the default): the target, space and `n_years` seeded baseline years, seeded per
    run; "all": the rubric's 13; `explicit`: a list the caller names (validation), each checked. Baseline years first, ascending."""
    valid = all_groups()
    if mode == "plan" and not explicit:
        raise ValueError("group mode 'plan' takes each run's groups from its plan entry, and this entry has none")
    if explicit:
        bad = [g for g in explicit if g not in valid]
        if bad:
            raise ValueError(f"unknown group(s) {bad}; valid: {valid}")
        return [g for g in valid if g in set(explicit)]
    if mode == "all":
        return valid
    if mode != "reduced":
        raise ValueError(f"group mode must be 'reduced' or 'all', got {mode!r}")
    years = sorted(random.Random(f"{seed}|groups|{run_key}").sample(BASELINE_YEARS, n_years))
    return [baseline_group(y) for y in years] + ["target", "space"]


# ------------------------------------------------------------------------------------------------------ perturbation
@dataclasses.dataclass(frozen=True)
class PerturbSpec:
    delta_k: float = DEFAULT_DELTA_K
    space_frac: float = DEFAULT_SPACE_FRAC
    seed: str = "0"
    scheme: str = SCHEME

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, eq=False)
class GroupEdit:
    """What one group changes: on each of `days` the cells `cells[i]` (over the instance box) get `offsets[i]` kelvin."""
    group: str
    box: object                   # icsa.extent.CellBox
    days: np.ndarray              # int64 global day indices, sorted, unique
    offsets: np.ndarray           # float32 (n_days,)
    cells: np.ndarray             # bool (n_days, h, w)
    space_box: tuple | None = None   # (row0, col0, rows, cols) inside the instance box, for the space group

    def __post_init__(self):
        if self.days.size != self.offsets.size or self.cells.shape != (self.days.size, *self.box.shape):
            raise ValueError("edit arrays disagree in shape")

    def n_cell_days(self) -> int:
        return int(self.cells.sum())

    def fingerprint(self) -> str:
        h = hashlib.sha256(self.group.encode())
        for a in (self.days.astype(np.int64), self.offsets.astype(np.float32), np.packbits(self.cells, axis=None)):
            h.update(np.ascontiguousarray(a).tobytes())
        return h.hexdigest()

    def describe(self) -> dict:
        return {"group": self.group, "scheme": SCHEME, "days": int(self.days.size), "cell_days": self.n_cell_days(),
                "offsets_k": sorted({float(x) for x in self.offsets}), "space_box": self.space_box,
                "fingerprint": self.fingerprint()}


def pick_space_box(sea: np.ndarray, spec: PerturbSpec, instance_id: str) -> tuple[np.ndarray, tuple]:
    """A seeded sub-rectangle of the instance box whose sea share is at least half the box's own: (mask over the box, (r0, c0, rows,
    cols)). Seeded by (spec.seed, instance), so every run of one instance gets the same box (and an S2 copy can be reused)."""
    h, w = sea.shape
    if not sea.any():
        raise PerturbationError("the instance has no sea cell")
    bh, bw = max(1, round(h * spec.space_frac)), max(1, round(w * spec.space_frac))
    rng = random.Random(f"{spec.seed}|space|{instance_id}")
    overall = sea.mean()
    best = None
    for _ in range(20):
        r0, c0 = rng.randrange(h - bh + 1), rng.randrange(w - bw + 1)
        share = sea[r0:r0 + bh, c0:c0 + bw].mean()
        if best is None or share > best[0]:
            best = (share, r0, c0)
        if share >= 0.5 * overall and share > 0:
            best = (share, r0, c0)
            break
    _, r0, c0 = best
    if not sea[r0:r0 + bh, c0:c0 + bw].any():
        raise PerturbationError("no seeded box holds a sea cell")
    m = np.zeros((h, w), bool)
    m[r0:r0 + bh, c0:c0 + bw] = True
    return m, (r0, c0, bh, bw)


def build_edit(group: str, required, spec: PerturbSpec, instance_id: str) -> GroupEdit:
    """The edit of one group on an instance's REQUIRED sea cells (`required`: icsa.extent.PartedExtent)."""
    from icsa import grid
    base, tgt = required.baseline, required.target
    d = np.float32(spec.delta_k)
    if group.startswith("baseline:"):
        year = int(group.split(":", 1)[1])
        if year not in BASELINE_YEARS:
            raise ValueError(f"baseline year {year} is outside {BASELINE_YEARS[0]}..{BASELINE_YEARS[-1]}")
        rows = np.array([grid.day_date(int(x)).year == year for x in base.days])
        if not rows.any():
            raise PerturbationError(f"no required baseline day in {year}")
        return GroupEdit(group, base.box, base.days[rows], np.full(int(rows.sum()), d, np.float32), base.mask[rows].copy())
    if group == "target":
        return GroupEdit(group, tgt.box, tgt.days.copy(), np.full(tgt.days.size, d, np.float32), tgt.mask.copy())
    if group == "space":
        sea = tgt.mask.any(axis=0)
        box_mask, sb = pick_space_box(sea, spec, instance_id)
        days = np.concatenate([base.days, tgt.days])
        offs = np.concatenate([np.full(base.days.size, -d, np.float32), np.full(tgt.days.size, d, np.float32)])
        cells = np.concatenate([base.mask & box_mask, tgt.mask & box_mask])
        order = np.argsort(days)
        return GroupEdit(group, base.box, days[order], offs[order], cells[order], sb)
    raise ValueError(f"unknown group {group!r}")


def apply_edit_to_series(sst: np.ndarray, days: np.ndarray, edit: GroupEdit) -> np.ndarray:
    """A copy of `sst` (len(days), h, w; float32, the instance box) with the edit applied on the days it names. Same float32 sum as
    the on-disk edit, so the in-memory reference and the files agree bit for bit (the read-back check proves it)."""
    out = np.array(sst, dtype=np.float32, copy=True)
    pos = {int(d): i for i, d in enumerate(np.asarray(days))}
    for d, off, cells in zip(edit.days, edit.offsets, edit.cells):
        i = pos.get(int(d))
        if i is not None and cells.any():
            out[i][cells] = out[i][cells] + np.float32(off)
    return out


# --- on-disk edits: a file is opened for writing only after it is proved to be a private copy
def assert_private_copy(dst: Path, src: Path, scratch: Path | None = None) -> None:
    """Refuse to write `dst` unless it is a file of its own: not linked to anything, not the source's inode, under `scratch`."""
    ds, ss = os.stat(dst), os.stat(src)
    if ds.st_nlink != 1:
        raise PerturbationError(f"{dst} has {ds.st_nlink} links: writing it would change the master copy")
    if (ds.st_dev, ds.st_ino) == (ss.st_dev, ss.st_ino):
        raise PerturbationError(f"{dst} is the source file itself")
    if scratch is not None and not Path(dst).resolve().is_relative_to(Path(scratch).resolve()):
        raise PerturbationError(f"{dst} is not under the scratch directory {scratch}")


def _signature(ds) -> dict:
    """Everything about a dataset except the values of the SST variable: dimensions, attributes, variables' dtype, dimensions,
    attributes, storage (filters, chunking), and the full values of every other variable (the coordinates)."""
    sig = {"dims": {k: len(v) for k, v in ds.dimensions.items()},
           "attrs": {k: str(ds.getncattr(k)) for k in sorted(ds.ncattrs())}, "vars": {}}
    for name, v in ds.variables.items():
        sig["vars"][name] = {"dtype": str(v.dtype), "dims": list(v.dimensions), "shape": list(v.shape),
                             "attrs": {k: repr(v.getncattr(k)) for k in sorted(v.ncattrs())},
                             "filters": {k: str(x) for k, x in v.filters().items()}, "chunking": str(v.chunking())}
        if name != "analysed_sst":
            sig["vars"][name]["values_sha256"] = hashlib.sha256(np.ascontiguousarray(np.asarray(v[:])).tobytes()).hexdigest()
    return sig


def file_signature(path: Path) -> dict:
    import netCDF4
    from icsa.ncio import NETCDF_LOCK
    with NETCDF_LOCK, netCDF4.Dataset(path) as ds:
        return _signature(ds)


def read_day(path: Path, t: int, box=None) -> np.ndarray:
    """The raw float32 slice of `analysed_sst` at time index t (whole grid, or `box`), no masking, no scaling."""
    import netCDF4
    from icsa.ncio import NETCDF_LOCK
    with NETCDF_LOCK, netCDF4.Dataset(path) as ds:
        ds.set_auto_mask(False)
        ds.set_auto_scale(False)
        v = ds["analysed_sst"]
        a = v[t] if box is None else v[t, box.lat0:box.lat1, box.lon0:box.lon1]
        return np.array(a, dtype=np.float32)


def write_day_edit(path: Path, t: int, box, cells: np.ndarray, offset: float) -> None:
    """Add `offset` (float32) to the `cells` of the box at time index t, in place. The caller has proved `path` private."""
    import netCDF4
    from icsa.ncio import NETCDF_LOCK
    with NETCDF_LOCK, netCDF4.Dataset(path, "r+") as ds:
        ds.set_auto_mask(False)
        ds.set_auto_scale(False)
        v = ds["analysed_sst"]
        if v.dtype != np.float32 or v.dimensions[0] != "time":
            raise PerturbationError(f"{path}: analysed_sst is {v.dtype} {v.dimensions}, expected float32 (time, lat, lon)")
        sub = np.array(v[t, box.lat0:box.lat1, box.lon0:box.lon1], dtype=np.float32)
        if not np.isfinite(sub[cells]).all():
            raise PerturbationError(f"{path}: a required sea cell is not finite on this day; the extent and the file disagree")
        sub[cells] = sub[cells] + np.float32(offset)
        v[t, box.lat0:box.lat1, box.lon0:box.lon1] = sub


def expected_after(src_day: np.ndarray, box, cells: np.ndarray, offset: float) -> np.ndarray:
    exp = src_day.copy()
    sub = exp[box.lat0:box.lat1, box.lon0:box.lon1]
    sub[cells] = sub[cells] + np.float32(offset)
    return exp


def _bits(a: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(a, dtype=np.float32).view(np.uint32)


def verify_edited_day(src: Path, t_src: int, dst: Path, t_dst: int, box, cells: np.ndarray, offset: float) -> None:
    """Read both back: bit-equal everywhere except the touched cells, which are exactly float32(src) + float32(offset)."""
    a, b = read_day(src, t_src), read_day(dst, t_dst)
    exp = expected_after(a, box, cells, offset)
    if a.shape != b.shape or not np.array_equal(_bits(b), _bits(exp)):
        n = int((_bits(b) != _bits(exp)).sum()) if a.shape == b.shape else -1
        raise PerturbationError(f"{dst} day {t_dst}: {n} cells differ from the intended edit")


# ------------------------------------------------------------------------------------------------- the comparison
def masks_equal(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and bool(np.array_equal(a.astype(bool), b.astype(bool)))


def n_differing(a: np.ndarray, b: np.ndarray) -> int:
    if a.shape != b.shape:
        return -1
    return int((a.astype(bool) != b.astype(bool)).sum())


def compare_group(ref_base: np.ndarray, ref_pert: np.ndarray, agent_base: np.ndarray | None, agent_pert: np.ndarray | None,
                  sea: np.ndarray, *, arm_ok: bool = True, arm_detail: str = "") -> dict:
    """The outcome of one group. Masks are bool (target days, h, w); `ref_*` are the reference detector's masks without and with the
    perturbation, `agent_*` the replayed masks of the control and of the perturbed arm; `sea` is bool (h, w).

    The reference's change counts on sea cells only (scoring does the same). Order of the tests matters: a group whose reference did
    not move is `not_tested` even when its arm ran; an arm that failed is `not_tested`, never `no_change`."""
    ref_base, ref_pert = np.asarray(ref_base, bool), np.asarray(ref_pert, bool)
    if ref_base.shape != ref_pert.shape or ref_base.shape[1:] != sea.shape:
        raise ValueError("reference masks and the sea mask disagree in shape")
    ref_ch = (ref_base != ref_pert) & sea
    n_ref = int(ref_ch.sum())
    out = {"n_ref_change": n_ref, "n_agent_change": None, "n_overlap": None, "n_overlap_same_direction": None,
           "outcome": "not_tested", "reason": None, "detail": ""}
    if n_ref == 0:
        out["reason"] = "reference_did_not_move"
        return out
    if not arm_ok or agent_base is None or agent_pert is None:
        out.update(reason="arm_not_ok", detail=arm_detail)
        return out
    agent_base, agent_pert = np.asarray(agent_base, bool), np.asarray(agent_pert, bool)
    if agent_base.shape != ref_ch.shape or agent_pert.shape != ref_ch.shape:
        raise ValueError("agent masks and reference masks disagree in shape")
    ag_ch = agent_base != agent_pert
    ov = ag_ch & ref_ch
    out.update(n_agent_change=int(ag_ch.sum()), n_overlap=int(ov.sum()),
               n_overlap_same_direction=int((ov & (agent_pert == ref_pert)).sum()))
    out["outcome"] = "positive" if out["n_overlap"] > 0 else "change_elsewhere" if out["n_agent_change"] > 0 else "no_change"
    return out


# ------------------------------------------------------------------------------------------- the local-only guard
def assert_local_data_config(dc, option, *, local_token: str, real_hosts=()) -> None:
    """Refuse a data configuration that could reach site_g, site_f or any Onedata that is not the local mock. Checked on the DataConfig that
    is about to be handed to the sandbox: the token is the made-up local one, every real host name maps to a plain-HTTP upstream on
    this host, there is no knowledge plane, and M binds a plain directory instead of oneclient."""
    problems = []
    if getattr(dc, "token", None) != local_token:
        problems.append("the token is not the local-simulation token")
    if getattr(dc, "oneclient_token", ""):
        problems.append("a oneclient token is set")
    if getattr(dc, "knowledge", None):
        problems.append("a knowledge plane is configured")
    hosts = {h for h in (*real_hosts, dc.onezone_host, dc.oneclient_provider_host, *(dc.provider_hosts or [])) if h}
    for h in sorted(hosts):
        up = (dc.upstream or {}).get(h)
        if not up or up.get("addr") not in LOCAL_UPSTREAM_ADDRS or up.get("tls") is not False:
            problems.append(f"host {h} does not map to a local plain-HTTP upstream")
    opt = getattr(option, "value", option)
    if opt == "M" and not (dc.mount_stub_dir and Path(dc.mount_stub_dir).is_dir()):
        problems.append("M does not bind a plain local directory")
    if problems:
        raise LocalOnlyError("refusing a data configuration that is not local: " + "; ".join(problems))


# --------------------------------------------------------------------------------------------------------- scratch
MARKER = ".replaycheck-scratch"


def check_scratch(scratch: Path, data_paths, *, need_bytes: int, min_free_bytes: int = 0) -> dict:
    """The scratch must exist, be on the data's filesystem (hard links), and hold `need_bytes` (an S2 copy per concurrent S2 arm)
    beyond `min_free_bytes`. Raises ScratchError with the numbers; returns them."""
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    devs = {os.stat(p).st_dev for p in data_paths}
    if devs != {os.stat(scratch).st_dev}:
        raise ScratchError(f"scratch {scratch} is not on the same filesystem as the data {[str(p) for p in data_paths]}: "
                           "hard links need one filesystem")
    free = shutil.disk_usage(scratch).free
    if free < need_bytes + min_free_bytes:
        raise ScratchError(f"scratch {scratch} has {free / 2**30:.1f} GiB free; an S2 copy needs {need_bytes / 2**30:.1f} GiB "
                           f"beyond the {min_free_bytes / 2**30:.1f} GiB to keep free")
    return {"free_bytes": free, "need_bytes": need_bytes, "min_free_bytes": min_free_bytes}


def safe_rmtree(path: Path, scratch: Path) -> None:
    """Delete a directory this module made: strictly inside the scratch and carrying the marker. Anything else is refused."""
    p, s = Path(path).resolve(), Path(scratch).resolve()
    if p == s or not p.is_relative_to(s) or not (p / MARKER).is_file():
        raise ScratchError(f"refusing to delete {p}: not a directory this check made inside {s}")
    shutil.rmtree(p)


def mark(path: Path) -> Path:
    Path(path).mkdir(parents=True, exist_ok=True)
    (Path(path) / MARKER).write_text("made by icsa.inspection.replaycheck; safe to delete\n")
    return Path(path)


# ------------------------------------------------------------------------------------------------ the sample / plan
def frame_from_decisions(decisions: dict, population: list[dict]) -> tuple[list[dict], list[dict]]:
    """The frame: inspection-resolved runs (decision route `inspection`, label complete or omitting; K cases never), each joined to
    its population row for the run directory. Returns (rows, unjoined): a resolved run with no population row or no run directory is
    listed with the reason, never dropped silently."""
    pop = {r["run_key"]: r for r in population}
    rows, unjoined = [], []
    for pid, p in sorted(decisions.get("packets", {}).items()):
        d = p.get("decision")
        if not d or d.get("route") != "inspection" or p.get("set") == "K" or p.get("phase") == "ktest":
            continue
        if d.get("label") not in LABELS:
            continue
        r = pop.get(p["run_key"])
        if r is None or not r.get("run_dir"):
            unjoined.append({"run_key": p["run_key"], "reason": "no population row" if r is None else "no run_dir"})
            continue
        rows.append({"run_key": p["run_key"], "phase": p.get("phase") or r.get("phase"), "option": str(p.get("option") or r.get("option")),
                     "layout": str(p.get("layout") or r.get("layout")), "instance_id": p.get("instance_id") or r.get("instance_id"),
                     "model": p.get("model") or r.get("model"), "label": d["label"], "run_dir": r["run_dir"]})
    return rows, unjoined


def label_pattern(weight: int) -> list[str]:
    """`weight` completes, then one omitting, repeated: oversampling resolved `complete`."""
    if not isinstance(weight, int) or weight < 1:
        raise ValueError("complete_weight must be an integer >= 1")
    return ["complete"] * weight + ["omitting"]


def _emit(lists: dict[str, list], n: int | None, weight: int):
    """Yield up to n items alternating labels by the pattern; a label that has run out is skipped, so nothing is lost."""
    pat, i, got = label_pattern(weight), 0, 0
    lists = {k: list(v) for k, v in lists.items()}
    while (n is None or got < n) and any(lists.values()):
        lab = pat[i % len(pat)]
        i += 1
        if lists[lab]:
            yield lists[lab].pop(0)
            got += 1


def _by_label(rows, seed, *tag) -> dict[str, list]:
    out = {}
    for lab in LABELS:
        xs = sorted((r for r in rows if r["label"] == lab), key=lambda r: r["run_key"])
        random.Random("|".join(map(str, (seed, *tag, lab)))).shuffle(xs)
        out[lab] = xs
    return out


def _round_robin(streams: list[list]) -> list:
    out, i = [], 0
    streams = [list(s) for s in streams]
    while any(streams):
        s = streams[i % len(streams)]
        if s:
            out.append(s.pop(0))
        i += 1
    return out


def _entry(r: dict, kind: str, segment: int) -> dict:
    keep = ("run_key", "phase", "option", "layout", "instance_id", "model", "label", "run_dir", "groups")
    e = {k: r[k] for k in keep if k in r and r[k] is not None}
    e.update(kind=kind, segment=segment, stratum=f"{r['option']}/{r['layout']}")
    return e


def empty_plan(seed, *, pilot_per_option=DEFAULT_PILOT_PER_OPTION, complete_weight=DEFAULT_COMPLETE_WEIGHT,
               main_phases=("main",), pilot_phase="pilot") -> dict:
    label_pattern(complete_weight)
    return {"format": FORMAT_PLAN, "seed": str(seed), "params": {"pilot_per_option": pilot_per_option, "complete_weight": complete_weight,
            "main_phases": list(main_phases), "pilot_phase": pilot_phase, "order": "pilot first, then main balanced per option x layout; "
            "later arrivals are appended in later segments, nothing planned ever moves"}, "segments": [], "entries": []}


def extend_plan(plan: dict, frame: list[dict], *, when: str | None = None) -> dict:
    """A new plan: every entry of `plan` unchanged and in place, then the frame's runs not yet in it, appended as one new segment.
    The new segment is the pilot's resolved runs (up to the per-option quota not yet used, oversampling `complete`), then the main
    block's, balanced per option x layout in a seeded order. Nothing already planned is reordered, dropped or re-picked."""
    if plan.get("format") != FORMAT_PLAN:
        raise ValueError("not a replay-check plan")
    p = plan["params"]
    seed, w = plan["seed"], p["complete_weight"]
    planned = {e["run_key"] for e in plan["entries"]}
    new_rows = [r for r in frame if r["run_key"] not in planned]
    info = {"frame_labels": dict(Counter(r["label"] for r in frame)), "frame_size": len(frame)}
    if not new_rows:                      # nothing arrived: the plan is returned as it is (no empty segment)
        return {**plan, **info}
    seg = len(plan["segments"])
    entries = [dict(e) for e in plan["entries"]]
    added = {"pilot": 0, "main": 0}
    # pilot: up to pilot_per_option per option over the whole plan, round-robin across options
    pil = [r for r in new_rows if r["phase"] == p["pilot_phase"]]
    used = Counter(e["option"] for e in plan["entries"] if e["kind"] == "pilot")
    streams = []
    for o in sorted({r["option"] for r in pil}):
        quota = max(0, p["pilot_per_option"] - used[o])
        streams.append(list(_emit(_by_label([r for r in pil if r["option"] == o], seed, "pilot", seg, o), quota, w)))
    for r in _round_robin(streams):
        entries.append({**_entry(r, "pilot", seg), "pos": len(entries)})
        added["pilot"] += 1
    # main: every resolved run of the main phases, strata = option x layout, round-robin across strata
    main = [r for r in new_rows if r["phase"] in p["main_phases"]]
    streams = []
    for o, l in sorted({(r["option"], r["layout"]) for r in main}):
        sr = [r for r in main if (r["option"], r["layout"]) == (o, l)]
        streams.append(list(_emit(_by_label(sr, seed, "main", seg, o, l), None, w)))
    for r in _round_robin(streams):
        entries.append({**_entry(r, "main", seg), "pos": len(entries)})
        added["main"] += 1
    if len(entries) == len(plan["entries"]):      # the new runs were all beyond the pilot's quota: still nothing to add, no empty segment
        return {**plan, **info}
    segs = list(plan["segments"]) + [{"index": seg, "built_at": when or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                       "frame_size": len(frame), "added": added}]
    return {**plan, "segments": segs, "entries": entries, **info}


def result_name(run_key: str) -> str:
    return hashlib.sha256(run_key.encode()).hexdigest()[:20] + ".json"


def progress(plan: dict, out: Path) -> dict:
    """How far the work got, from the result files (per run, not a pointer): finished runs, the contiguous prefix of the plan that is
    finished, the next position, and what was not reached."""
    res = Path(out) / "results"
    done, status = [], Counter()
    for e in plan["entries"]:
        p = res / result_name(e["run_key"])
        if p.is_file():
            try:
                s = json.loads(p.read_text()).get("status")
            except ValueError:
                s = None
            if s in ("replayed", "not_replayable"):
                done.append(e["pos"])
                status[s] += 1
    ds = set(done)
    prefix = 0
    while prefix in ds:
        prefix += 1
    n = len(plan["entries"])
    return {"planned": n, "finished": len(done), "contiguous_prefix": prefix, "next_pos": next((i for i in range(n) if i not in ds), None),
            "not_reached": n - len(done), "by_status": dict(status)}


# ---------------------------------------------------------------------------------------------------- the summary
def _blank():
    return {"runs": 0, "replayed": 0, "not_replayable": 0, "infra": 0, "group_outcomes": {o: 0 for o in OUTCOMES}}


def _add(cell: dict, res: dict) -> None:
    cell["runs"] += 1
    cell[res["status"]] = cell.get(res["status"], 0) + 1
    for g in res.get("groups", []):
        cell["group_outcomes"][g["outcome"]] += 1


def summarise(plan: dict, results: list[dict]) -> dict:
    """Counts only: per option x layout and per resolved label (and both), outcomes per group kind, the time and sandbox use, how far
    the work got. Nothing in it is a verdict about a run."""
    by_ol, by_lab, by_both, by_kind = defaultdict(_blank), defaultdict(_blank), defaultdict(_blank), defaultdict(lambda: {o: 0 for o in OUTCOMES})
    reasons, arm_wall, sbx, mem = Counter(), [], 0, 0
    totals = Counter()
    for r in results:
        key = f"{r['option']}/{r['layout']}"
        _add(by_ol[key], r)
        _add(by_lab[r["label"]], r)
        _add(by_both[f"{key}|{r['label']}"], r)
        if r["status"] != "replayed":
            reasons[r.get("reason") or r["status"]] += 1
        for g in r.get("groups", []):
            by_kind[group_kind(g["group"])][g["outcome"]] += 1
            if g["outcome"] == "not_tested":
                reasons["not_tested:" + str(g.get("reason"))] += 1
        arms = ([r["control"]] if r.get("control") else []) + [g["arm"] for g in r.get("groups", []) if g.get("arm")]
        for a in arms:
            arm_wall.append(a.get("wall_s") or 0.0)
            sbx += a.get("sandbox_starts") or 0
            mem = max(mem, a.get("memory_peak_bytes") or 0)
        for k in ("replay_wall_s", "perturb_wall_s", "reference_wall_s", "total_wall_s", "s2_copy_s", "s2_copy_bytes"):
            totals[k] += (r.get("timing") or {}).get(k) or 0
    prog = progress_from(plan, results)
    return {"format": FORMAT_SUMMARY, "status": "report", "note": REPORT_NOTE, "limit": LIMIT_NOTE, "reach_note": REACH_NOTE,
            "plan": {"seed": plan["seed"], "params": plan["params"], "planned": len(plan["entries"]), "segments": plan["segments"],
                     "frame_size": plan.get("frame_size"), "frame_labels": plan.get("frame_labels"),
                     "by_label_planned": dict(Counter(e["label"] for e in plan["entries"]))},
            "progress": prog, "perturbation": results[0].get("perturbation") if results else None,
            "runs": dict(Counter(r["status"] for r in results)), "reasons": dict(reasons),
            "by_option_layout": dict(by_ol), "by_label": dict(by_lab), "by_option_layout_label": dict(by_both),
            "group_outcomes_by_kind": dict(by_kind),
            "time_and_sandbox": {"arms": len(arm_wall), "arm_wall_s_total": round(sum(arm_wall), 1),
                                 "arm_wall_s_mean": round(sum(arm_wall) / len(arm_wall), 1) if arm_wall else None,
                                 "arm_wall_s_max": round(max(arm_wall), 1) if arm_wall else None, "sandbox_starts": sbx,
                                 "memory_peak_bytes_max": mem or None, **{k: round(v, 1) for k, v in totals.items()}}}


def progress_from(plan: dict, results: list[dict]) -> dict:
    done = {r["pos"] for r in results if r["status"] in ("replayed", "not_replayable")}
    prefix = 0
    while prefix in done:
        prefix += 1
    n = len(plan["entries"])
    return {"planned": n, "finished": len(done), "contiguous_prefix": prefix, "not_reached": n - len(done),
            "reached_note": f"reached {len(done)} of {n} planned runs (the first {prefix} in order); {REACH_NOTE}"}


def replay_status(summary: dict) -> dict:
    """The {status, note} file `report.py --replay-status` takes for its independent-check entry."""
    p, c = summary["progress"], summary["runs"]
    return {"status": "built",
            "note": f"dependence test by replay: {p['reached_note']} {c.get('replayed', 0)} replayed, {c.get('not_replayable', 0)} not "
                    f"replayable. {REPORT_NOTE} {LIMIT_NOTE}"}


# --------------------------------------------------------------------------------------------------------------- CLI
def _read_jsonl(path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def _write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str))
    os.replace(tmp, path)


def load_results(out: Path) -> list[dict]:
    res = []
    for p in sorted((Path(out) / "results").glob("*.json")):
        try:
            res.append(json.loads(p.read_text()))
        except ValueError:
            continue
    return res


def plan_main(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pp = out / "plan.json"
    if pp.is_file():
        plan = json.loads(pp.read_text())
        if str(plan["seed"]) != str(a.seed):
            print(f"{pp} exists with seed {plan['seed']}, not {a.seed}: the plan is fixed", file=sys.stderr)
            return 2
    else:
        plan = empty_plan(a.seed, pilot_per_option=a.pilot_per_option, complete_weight=a.complete_weight,
                          main_phases=tuple(x for x in a.main_phases.split(",") if x))
    if a.frame:
        frame, unjoined = _read_jsonl(a.frame), []
    else:
        if not (a.decisions and a.population):
            print("give --frame, or --decisions and --population", file=sys.stderr)
            return 2
        from .queue import read_population
        frame, unjoined = frame_from_decisions(json.loads(Path(a.decisions).read_text()), read_population(a.population))
    before = len(plan["entries"])
    plan = extend_plan(plan, frame)
    plan["unjoined"] = unjoined
    _write_json(pp, plan)
    print(f"plan: {len(plan['entries'])} runs ({len(plan['entries']) - before} new), segments {len(plan['segments'])}, frame {len(frame)}, "
          f"unjoined {len(unjoined)}")
    return 0


def summary_main(a) -> int:
    out = Path(a.out)
    plan = json.loads((out / "plan.json").read_text())
    s = summarise(plan, load_results(out))
    _write_json(out / "summary.json", s)
    _write_json(out / "replay_status.json", replay_status(s))
    print(json.dumps({"runs": s["runs"], "progress": s["progress"], "group_outcomes_by_kind": s["group_outcomes_by_kind"]}, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="replaycheck", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="create or extend the fixed, ordered, append-only sample")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", required=True)
    p.add_argument("--decisions", help="report.py's decisions.json")
    p.add_argument("--population", help="the population JSONL (run directories)")
    p.add_argument("--frame", help="a JSONL of frame rows instead (run_key, phase, option, layout, instance_id, label, run_dir[, groups])")
    p.add_argument("--pilot-per-option", type=int, default=DEFAULT_PILOT_PER_OPTION)
    p.add_argument("--complete-weight", type=int, default=DEFAULT_COMPLETE_WEIGHT,
                   help="resolved `complete` runs per resolved `omitting` run in the order (oversampling); a new plan only")
    p.add_argument("--main-phases", default="main", help="comma list of the phases whose resolved runs follow the pilot's")
    r = sub.add_parser("run", help="work through the plan in order; resumable; stop by creating OUT/STOP")
    r.add_argument("--out", required=True)
    r.add_argument("--scratch", required=True, help="private working directory on the data's filesystem (perturbed copies live here)")
    r.add_argument("--data-root", required=True, help="holds s1z/ (the daily files) and s2z/sst_s2.nc, and layout/ids.json")
    r.add_argument("--s1-dir")
    r.add_argument("--s2-file")
    r.add_argument("--ids-json")
    r.add_argument("--sandbox-work-root", help="where the sandboxes' own disks live (default: the sandbox config's)")
    r.add_argument("--config-dir", help="harness config (sandbox limits); default: the repository's")
    r.add_argument("--image-id", help="sha256:... for every arm; default: each run's own pinned image, which must be present")
    r.add_argument("--groups", default="reduced", help="'reduced' (the set: target, space, 2 seeded baseline years), 'all', 'plan' (each plan entry "
                   "names its groups: validation), or a comma list (the same groups for every run)")
    r.add_argument("--baseline-years", type=int, default=2, help="seeded baseline years in the reduced set")
    r.add_argument("--delta-k", type=float, default=DEFAULT_DELTA_K)
    r.add_argument("--space-frac", type=float, default=DEFAULT_SPACE_FRAC)
    r.add_argument("--jobs", type=int, default=1, help="runs in parallel (each uses one sandbox at a time)")
    r.add_argument("--max-d", type=int, default=1, help="option D arms at once")
    r.add_argument("--max-sandboxes", type=int, default=0, help="this host's ceiling on sandboxes at once (0: as many as --jobs)")
    r.add_argument("--max-s2-copies", type=int, default=1, help="full S2 copies on the scratch at once")
    r.add_argument("--arm-cap-s", type=float, default=3600.0, help="wall cap of each arm")
    r.add_argument("--min-free-gb", type=float, default=25.0, help="no arm starts with less free on the scratch's filesystem")
    r.add_argument("--s2-cache", help="keep perturbed S2 copies here, per (instance, group), for reuse; off by default (made and deleted)")
    r.add_argument("--limit", type=int, default=None, help="stop after this many runs finished in this invocation")
    s = sub.add_parser("summary", help="counts, how far it got, and the report.py --replay-status file")
    s.add_argument("--out", required=True)
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "plan":
        return plan_main(a)
    if a.cmd == "summary":
        return summary_main(a)
    from .replayrun import run_main
    return run_main(a)


if __name__ == "__main__":
    raise SystemExit(main())
