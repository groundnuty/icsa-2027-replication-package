"""The duty-cycle curve (science, #34, 2 Nov 05:21Z and 05:27Z; #2, 14:14Z item 6): the registered curve's pass rule under agent-shaped load.

Science's definition: "c sandboxes each repeating the scripted cell with idle gaps matched to the measured data share of a run, plus a probe run
measured against 1.25x". Here a level c is c slots looping the block's mix as the registered curve does (`__main__.run_mix`), each run followed by an
idle gap, so every counted run is an ordinary scripted run with its stamps: `curve.level_table` and `curve.cap` judge it unchanged (both ratios, each
<= 1.25x its own instance's single run), and every counted run is a probe.

The data share of a pilot run (an agent run, `block == "pilot"`), from what the run left behind:
- T, T-unpaginated, D: the gate's log. The gate stamps a request when it COMPLETES (`t`), not when it starts, so the time share is estimated: each
  forwarded request is taken as busy for min(the time since the previous completion, `TAU_S`) before its completion (`gate_busy`). Beside it, the
  byte share, which is measured: the bytes site_g served (`site_g_bytes`, per tag the larger of `bytes` and `upstream_bytes`, the same counter for the
  scripted baselines) per second of the run's wall, over the scripted cell's own rate while reading (bytes per second of read phase). A run's share
  is the larger of the two: the time estimate covers request-bound reading, the bytes a long download the time estimate cuts to `TAU_S`.
- M, M+: oneclient's perf log, each FsLogic read and ReadCache prefetch row busy for its own `Duration` from its `Time` (taken as the start): the busy
  time is the union of those intervals, with no bridging of the gaps between them (science, #34, amendment 25(d); it bridged gaps of at most `TAU_S`
  before, as the gate rule counts them busy). Listing and metadata do not appear in that log, so M's share is low by their time.
The run's window is the one its `wall_time_s` measured (`run_window`): from `started_at` plus the wait for a slot user (`extras.onedata_slot_wait_s`,
which `wall_time_s` leaves out and which happens after `started_at`, inside the sandbox start) for `wall_time_s`. Not `ended_at`: the runner takes it after
validation (and after any wait for its lock), so it can lie hundreds of seconds past the end of the reads; a window built back from it clips the first
reads (review S1). A record without the slot wait gets [started_at, ended_at], which can only be too wide, and the row says so; one without a
`started_at` fails. The runs: the pilot's (`block == "pilot"`,
not excluded from analysis) and the calibration's (`block == "calibration"`, which every outcome analysis excludes but whose load is real; the pilot
is S1 only, so S2's shares come from calibration). A cell's share is the 90th PERCENTILE of its runs' shares (science, #34, 15:10Z; numpy's linear
interpolation), with the mean, median and per-model means beside it. A cell with no runs fails, unless the command names the cells its share is
taken from (`--share-from`, recorded in the profile): T-unpaginated is in neither block. Given several, it takes the largest of their shares, so its
offered load is never lighter than any of theirs; the documented choice is `T-unpaginated/S1=T/S1,D/S1,M/S1` (science, #34, 15:27Z).

The schedule (`build_profile`): after a run of (option, layout, instance), idle `read / share - total`, from that instance's single-run read phase and
`total_s` (the registered curve's baselines), so the read phase is `share` of the cycle. `total_s`, not the script's `wall_s`: a slot is busy for the
whole `run_one` (lease, sandbox start, collect, teardown) before its gap starts, as the pilot's `wall_time_s` includes the agent's sandbox start. A negative gap is 0 and flagged: that cell is loaded above its
share. The cycle is held fixed: after a run that took longer than its baseline the gap shrinks by the overrun (never below 0, flagged when it
reaches 0), so a slowdown on the host does not lower site_g's load (the lead, 2 Nov). Seeded: each slot starts at an offset in [0, one cycle), every
gap carries jitter of +-`JITTER`, and each slot's first cycle is an uncounted warm-up. The profile is frozen with its hash before the curve starts; every decision line carries it.

Missing inputs fail (`DutyInputError`), they never default: an eligible run without its log, a cell without runs, a baseline without a read phase.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import re
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Iterable

import numpy as np

TAU_S = 1.0                      # a gate request is busy for at most this long before its completion, unless the previous one completed later
JITTER = 0.5                     # each gap is drawn uniformly in [1 - JITTER, 1 + JITTER] x its scheduled length
MAX_M_RUNS = 16                  # science's ruling, relayed by the lead (2 Nov): M x 16 was shown on site_g; more M runs at once wait, and the wait is recorded
HOST_SAMPLE_S = 5.0              # the host watch's period during a level
REST = ("T", "T-unpaginated", "D")
MOUNT = ("M", "M+")
FORMAT = "icsa-duty-profile-v1"


class DutyInputError(ValueError):
    """An input the duty-cycle curve rests on is missing or does not fit: nothing is defaulted."""


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float("inf")


def merge(iv: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def union_s(iv: Iterable[tuple[float, float]]) -> float:
    return sum(b - a for a, b in merge(iv))


def bridge(iv: Iterable[tuple[float, float]], tau: float = TAU_S) -> list[tuple[float, float]]:
    """Merged intervals with every gap of at most `tau` between them counted busy."""
    out: list[list[float]] = []
    for a, b in merge(iv):
        if out and a - out[-1][1] <= tau:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def clip(iv: Iterable[tuple[float, float]], start: float, end: float) -> list[tuple[float, float]]:
    return [(max(a, start), min(b, end)) for a, b in iv if min(b, end) > max(a, start)]


def burst_stats(iv: list[tuple[float, float]]) -> dict:
    """Descriptive only: the merged busy intervals ("bursts") and the idle gaps between them."""
    m = merge(iv)
    lens = [b - a for a, b in m]
    gaps = [m[i + 1][0] - m[i][1] for i in range(len(m) - 1)]

    def q(xs, p):
        return round(float(np.quantile(xs, p)), 3) if xs else None
    return {"bursts": len(m), "burst_s_median": q(lens, 0.5), "burst_s_p90": q(lens, 0.9), "burst_s_max": q(lens, 1.0),
            "gap_s_median": q(gaps, 0.5), "gap_s_p90": q(gaps, 0.9)}


def gate_site_g_bytes(by_tag: dict) -> int:
    """Bytes site_g served, from `metrics.summarize_gate_requests(...)["by_tag"]`: per tag the larger of the bytes sent to the sandbox and the bytes taken
    from upstream (D's whole files are spooled: `upstream_bytes`; a passed-through range: `bytes`). The same counter for pilot and scripted runs."""
    return int(sum(max(int(t.get("bytes") or 0), int(t.get("upstream_bytes") or 0)) for t in by_tag.values()))


def gate_busy(lines: list[dict], start: float, end: float, tau: float = TAU_S) -> list[tuple[float, float]]:
    """Busy intervals from the gate's log: every request the gate forwarded (`decision == "allow"`) is busy from max(the previous completion,
    its completion - `tau`) to its completion. A forwarded request without a completion time, or completed outside the run's window (1 s of
    slack), means the log and the record do not fit: it raises."""
    ts = []
    for r in lines:
        if r.get("decision") != "allow":
            continue                                     # a denied request never reached site_g
        t = r.get("t")
        if not _num(t):
            raise DutyInputError(f"a forwarded gate request without a completion time: {str(r)[:200]}")
        if t < start - 1.0 or t > end + 1.0:
            raise DutyInputError(f"a gate request completed at {t:.3f}, outside the run's window [{start:.3f}, {end:.3f}]")
        ts.append(float(t))
    iv, prev = [], start
    for t in sorted(ts):
        iv.append((max(prev, t - tau), t))
        prev = max(prev, t)
    return clip(iv, start, end)


def perf_busy(csv_paths: list[Path], start: float, end: float) -> list[tuple[float, float]]:
    """Busy intervals from oneclient's perf CSVs: FsLogic reads and ReadCache prefetches, each [Time, Time + Duration], merged where they overlap and nothing
    more: the gaps between them are not busy (amendment 25(d): reads at [0, 0.1] and [0.9, 1.0] of a run are 0.2 s, not 1.0 s; before it a gap of at most
    `TAU_S` was bridged). Parsed by the fault records' parser (date from the file name's epoch, midnight rollover), which raises on a malformed file."""
    from ..faults.records.base import Kind
    from ..faults.records.perf import parse_perf
    iv = []
    for p in csv_paths:
        m = re.fullmatch(r"read_write_perf-(\d+)\.csv", p.name)
        if not m:
            raise DutyInputError(f"{p}: not a read_write_perf-<epoch ms>.csv file")
        try:
            res = parse_perf(p.read_text(), int(m.group(1)), sidecar_id=p.name)
        except ValueError as e:                      # a malformed file, or time running backwards: not a share to guess at
            raise DutyInputError(f"{p}: {e}") from e
        for ev in res.events:
            if ev.kind in (Kind.READ, Kind.PREFETCH):
                try:
                    dur = int(ev.raw.rsplit(",", 1)[1]) / 1e6
                except (ValueError, IndexError) as e:
                    raise DutyInputError(f"{p}: a row without a duration: {ev.raw[:200]}") from e
                if not _num(ev.ts) or dur < 0:
                    raise DutyInputError(f"{p}: a row with no time or a negative duration: {ev.raw[:200]}")
                iv.append((ev.ts, ev.ts + dur))
    return clip(merge(iv), start, end)       # the union of the read intervals: no gap between them is counted busy (science, #34, amendment 25(d))


def _epoch(iso: str) -> float:
    t = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise DutyInputError(f"{iso!r}: a time without its zone")
    return t.timestamp()


ELIGIBLE_BLOCKS = ("pilot", "calibration")


def excluded(rec: dict) -> str | None:
    """Why a run record is not an eligible run, or None: the pilot's and the calibration's (science, #34, 15:10Z). Calibration rows carry
    `exclude_from_analysis` (#14's outcome analysis drops them) and are eligible here; a pilot row with it is a test row and is not.
    Time-cap stops are eligible: they held a slot."""
    if rec.get("block") not in ELIGIBLE_BLOCKS:
        return f"block {rec.get('block')!r}"
    if rec.get("infra_failure"):
        return "infrastructure failure"
    if rec.get("exclude_from_analysis") and rec.get("block") != "calibration":
        return "excluded from analysis"
    return None


def run_window(run_dir, rec: dict, wall: float) -> tuple[float, float, str]:
    """(start, end, how) in epoch seconds: the window a pilot run's `wall_time_s` measured. The runner (`harness/runner.py`) takes `started_at` and its
    monotonic t0 together, then `wall_time_s` = elapsed - the wait for a slot user (`extras.onedata_slot_wait_s`; None without a lease: nothing was
    taken off), after the agent loop, collect and stop; validation and `ended_at` come after. The wait is inside the sandbox start, so the reads lie in
    [started_at + wait, started_at + wait + wall_time_s]. Without the slot wait on the record the window is [started_at, ended_at]: it holds the reads
    whatever the wait was (the sandbox does not exist before t0 or after the wall is taken), and can only count a read that is not the run's if
    a log held one, which a run's own gate and perf logs do not. Without a usable `started_at` the window cannot be placed: it raises."""
    sa = rec.get("started_at")
    if not sa:
        raise DutyInputError(f"{run_dir}: a pilot record without started_at: the window its wall time measured cannot be placed")
    try:
        t0 = _epoch(sa)
    except (ValueError, TypeError, OverflowError) as e:
        raise DutyInputError(f"{run_dir}: started_at {sa!r}: {e}") from e
    ex = rec.get("extras")
    if not isinstance(ex, dict) or "onedata_slot_wait_s" not in ex:
        if not rec.get("ended_at"):
            raise DutyInputError(f"{run_dir}: a pilot record with neither the slot wait nor ended_at: the window cannot be placed")
        try:
            end = _epoch(rec["ended_at"])
        except (ValueError, TypeError, OverflowError) as e:
            raise DutyInputError(f"{run_dir}: ended_at {rec['ended_at']!r}: {e}") from e
        return t0, max(end, t0 + wall), "started_at to ended_at (the slot wait is not on the record)"      # never narrower than the wall it measured
    wait = ex["onedata_slot_wait_s"]
    wait = 0.0 if wait is None else wait
    if not _num(wait) or wait < 0:
        raise DutyInputError(f"{run_dir}: onedata_slot_wait_s {ex['onedata_slot_wait_s']!r}")
    return t0 + float(wait), t0 + float(wait) + wall, "started_at + slot wait + wall_time_s"


def bytes_between_sites(rec: dict) -> int | None:
    """The bytes the run took from the provider, as the harness keeps them on the record (`extras.bytes_between_sites`, H2: the sidecar's between-sites
    counter for a mount). None when the record does not have them: not known is not 0."""
    ex = rec.get("extras")
    v = ex.get("bytes_between_sites") if isinstance(ex, dict) else None
    return int(v) if _num(v) and v >= 0 else None


def run_share(run_dir: Path, rec: dict) -> dict:
    """One eligible pilot run's busy time, from its gate log (REST options) or its perf CSVs (mounts)."""
    run_dir = Path(run_dir)
    run = rec.get("run") or {}
    opt, lay = str(run.get("option")), str(run.get("layout"))
    wall = rec.get("wall_time_s")
    if not _num(wall) or wall <= 0:
        raise DutyInputError(f"{run_dir}: wall_time_s {wall!r}")
    start, end, how = run_window(run_dir, rec, float(wall))
    out = {"run_dir": str(run_dir), "window": how, "block": rec.get("block"), "option": opt, "layout": lay, "model": run.get("model"), "instance_id": run.get("instance_id"),
           "attempt": rec.get("attempt"), "termination": rec.get("termination"), "wall_s": float(wall)}
    if opt in REST:
        p = run_dir / "gate_requests.jsonl"
        if not p.is_file():
            raise DutyInputError(f"{run_dir}: a {opt} pilot run without gate_requests.jsonl")
        text = [ln for ln in p.read_text().splitlines() if ln.strip()]
        try:
            lines = [json.loads(ln) for ln in text]
        except ValueError as e:
            raise DutyInputError(f"{p}: {e}") from e
        from .metrics import summarize_gate_requests
        iv = gate_busy(lines, start, end)
        out["site_g_bytes"] = gate_site_g_bytes(summarize_gate_requests(text)["by_tag"])
        out["source"] = "gate"
    elif opt in MOUNT:
        csvs = sorted((run_dir / "oneclient_perf").glob("read_write_perf-*.csv"))
        if not csvs:
            raise DutyInputError(f"{run_dir}: an {opt} pilot run without its oneclient perf CSV")
        iv = perf_busy(csvs, start, end)
        out["site_g_bytes"] = bytes_between_sites(rec)         # (d): a mount's byte share too; None when the record does not know them, which is not 0
        out["source"] = "oneclient_perf"
    else:
        raise DutyInputError(f"{run_dir}: option {opt!r}")
    out["busy_s"] = round(union_s(iv), 3)
    out["time_share"] = out["busy_s"] / float(wall)
    out.update(burst_stats(iv))
    return out


def pilot_runs(dirs: Iterable) -> tuple[list[dict], dict]:
    """(the eligible runs' shares, what was left out and why). Every `run_record.json` under the given directories is read; a record that does not
    parse raises. Of several eligible records of one run (same block and RunId), the last directory in sorted order is kept, the others listed. The
    block is part of the run: the default campaign's pilot and calibration both run the calibration instance with one model and seed on the same
    options, and one overwriting the other drops a share (review S1: p90 0.38 became 0.1)."""
    found: dict[tuple, tuple[Path, dict]] = {}
    left: dict[str, list[str]] = {}
    superseded = []
    for d in dirs:
        paths = sorted(Path(d).rglob("run_record.json"))
        if not paths:
            raise DutyInputError(f"{d}: no run_record.json under it")
        for p in paths:
            try:
                rec = json.loads(p.read_text())
            except ValueError as e:
                raise DutyInputError(f"{p}: {e}") from e
            if str(rec.get("base_url") or "").startswith("stub://"):
                raise DutyInputError(f"{p}: a stub model's run (base_url {rec.get('base_url')}) is not an agent run")
            why = excluded(rec)
            if why:
                left.setdefault(why, []).append(str(p.parent))
                continue
            run = rec.get("run") or {}
            key = (rec.get("block"), run.get("instance_id"), run.get("option"), run.get("layout"), run.get("model"), run.get("seed"))
            if key in found:
                superseded.append(str(found[key][0]))
            found[key] = (p.parent, rec)
    rows = [run_share(d, rec) for d, rec in found.values()]
    return rows, {"excluded": {k: len(v) for k, v in left.items()}, "superseded": superseded}


def scripted_rates(single_runs: Iterable[dict]) -> dict[tuple[str, str], float]:
    """(option, layout) -> the scripted cell's median rate while reading: bytes site_g served over its read phase. REST options: from the clean single runs'
    gate summaries, and a clean run without one or without a read phase raises. Mounts (amendment 25(d), the byte share of M): from the sidecar's
    between-sites bytes (`bytes.between_sites_rx`) over the read phase, the same counter the pilot record keeps; a run without it (a local test's None)
    gives no rate for its cell, which fails only if a pilot run of that cell has bytes to compare."""
    from . import curve as Cv
    got: dict[tuple[str, str], list[float]] = {}
    for r in single_runs:
        if not Cv.clean(r):
            continue
        if r.get("option") in MOUNT:
            rx, rp = (r.get("bytes") or {}).get("between_sites_rx"), Cv.read_phase_s(r)
            if _num(rx) and rx > 0 and rp is not None and rp > 0:
                got.setdefault((r["option"], r["layout"]), []).append(rx / rp)
            continue
        if r.get("option") not in REST:
            continue
        by_tag = (r.get("gate_requests") or {}).get("by_tag")
        rp = Cv.read_phase_s(r)
        if not isinstance(by_tag, dict) or rp is None or rp <= 0:
            raise DutyInputError(f"{r.get('run_key')}: a clean {r.get('option')} single run without a gate summary or a read phase")
        got.setdefault((r["option"], r["layout"]), []).append(gate_site_g_bytes(by_tag) / rp)
    return {k: statistics.median(v) for k, v in got.items()}


REGISTERED_SHARE_FROM = {"T-unpaginated/S1": "T/S1,D/S1,M/S1"}     # amendment 25(d): T-unpaginated, which has neither kind of run, takes the largest S1 share among T, D and M
SHARE_QUANTILE = 0.9             # science, #34, 15:10Z: the cell's share is the 90th percentile of its runs' shares


def cell_shares(rows: list[dict], cells: Iterable[tuple[str, str]], rates: dict[tuple[str, str], float],
                share_from: dict[str, str] | None = None) -> dict[str, dict]:
    """"<option>/<layout>" -> the cell's share (`share`: the 90th percentile of its runs' shares) with the mean, median and per-model means. A run's
    share is its time share, or for a REST option the larger of that and its byte share (needs the cell's scripted rate). A cell without runs raises,
    unless `share_from` names the cells whose share it takes ("T-unpaginated/S1" -> "T/S1,D/S1,M/S1"): the largest of theirs, and the entry records
    every candidate and which was taken. A share of 0 raises."""
    share_from = dict(share_from or {})
    out = {}
    for o, la in cells:
        rs = [r for r in rows if (r["option"], r["layout"]) == (o, la)]
        if not rs and f"{o}/{la}" in share_from:
            srcs = [x.strip() for x in share_from[f"{o}/{la}"].split(",") if x.strip()]
            if not srcs or any(src == f"{o}/{la}" or src in share_from or "/" not in src for src in srcs):
                raise DutyInputError(f"--share-from {o}/{la}={share_from[f'{o}/{la}']}: each source must be a cell with its own runs")
            cand = {src: cell_shares(rows, [tuple(src.split("/", 1))], rates)[src] for src in srcs}
            best = max(srcs, key=lambda src: cand[src]["share"])        # the largest: a borrowed share never makes the offered load lighter
            out[f"{o}/{la}"] = {**cand[best], "share_from": ",".join(srcs), "share_from_taken": best,
                                "share_from_candidates": {src: cand[src]["share"] for src in srcs}}
            continue
        if not rs:
            raise DutyInputError(f"no eligible pilot or calibration run of {o}/{la}")
        for r in rs:
            if o in REST or r.get("site_g_bytes") is not None:      # a mount's bytes count when its record has them; without, it counts by time and the entry says how many
                rate = rates.get((o, la))
                if not rate or rate <= 0:
                    raise DutyInputError(f"no scripted read rate for {o}/{la}: the byte share cannot be formed")
                r["byte_share"] = r["site_g_bytes"] / r["wall_s"] / rate
                r["share"] = max(r["time_share"], r["byte_share"])
            else:
                r["byte_share"] = None
                r["share"] = r["time_share"]
        sh = [r["share"] for r in rs]
        mean = statistics.fmean(sh)
        p90 = float(np.quantile(sh, SHARE_QUANTILE))
        if not p90 > 0:
            raise DutyInputError(f"{o}/{la}: the runs read nothing from site_g (p90 share {p90}): no gap can be set")
        models: dict[str, list[float]] = {}
        for r in rs:
            models.setdefault(str(r["model"]), []).append(r["share"])
        out[f"{o}/{la}"] = {
            "share": p90, "statistic": "p90 (numpy linear)", "runs": len(rs), "mean": mean, "median": statistics.median(sh), "p90": p90,
            "max": max(sh), "by_block": {b: sum(1 for r in rs if r.get("block") == b) for b in ELIGIBLE_BLOCKS},
            "time_share_mean": statistics.fmean(r["time_share"] for r in rs),
            "byte_share_mean": statistics.fmean(r["byte_share"] for r in rs if r["byte_share"] is not None) if any(r["byte_share"] is not None for r in rs) else None,
            "byte_share_set_it": sum(1 for r in rs if r["byte_share"] is not None and r["byte_share"] > r["time_share"]),
            "byte_share_unknown": sum(1 for r in rs if r["byte_share"] is None),
            "scripted_rate_bytes_per_s": rates.get((o, la)) if (o in REST or any(r["byte_share"] is not None for r in rs)) else None,
            "per_model": {m: {"runs": len(v), "share_mean": statistics.fmean(v)} for m, v in sorted(models.items())}}
    return out


def given_shares(path, cells: Iterable[tuple[str, str]]) -> dict[str, dict]:
    """Given shares (science's cap amendment, #34; the values of amendment 25(c) as corrected by amendment 28, made by `python -m icsa.scripted.duty
    shares`): a JSON `{"<option>/<layout>": {"share": x, "source": "..."}}`, one entry per cell the curve uses, each with the provenance of its value.
    The entries have the shape `build_profile` reads. This takes shares as given and assumes nothing about how a share was computed: it does not
    recompute one. A missing cell, an unknown cell, a share outside (0, 1] or an empty source raises: nothing is defaulted."""
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise DutyInputError(f"{path}: {e}") from e
    if not isinstance(raw, dict):
        raise DutyInputError(f"{path}: not a JSON object of cell -> {{share, source}}")
    want = [f"{o}/{la}" for o, la in cells]
    missing, unknown = [c for c in want if c not in raw], sorted(set(raw) - set(want))
    if missing or unknown:
        raise DutyInputError(f"{path}: given shares must cover exactly the block's cells (missing {missing}, unknown {unknown})")
    out = {}
    for c in want:
        e = raw[c]
        sh, src = (e.get("share"), e.get("source")) if isinstance(e, dict) else (None, None)
        if not _num(sh) or not 0 < sh <= 1:
            raise DutyInputError(f"{path}: {c}: share {sh!r} is not a number in (0, 1]")
        if not isinstance(src, str) or not src.strip():
            raise DutyInputError(f"{path}: {c}: a given share needs its provenance (`source`)")
        out[c] = {"share": float(sh), "source": src, "kind": "given"}
    return out


def check_against(prof: dict, measured: dict[str, dict]) -> dict:
    """The check before main: per cell of the given profile, its given share, the measured p90 share (`cell_shares`' `share`) and whether the measured
    one exceeds it. A cell the profile has and the measurement lacks raises. `exceeds` lists the cells; the curve reruns if it is not empty."""
    if prof.get("shares_kind") != "given":
        raise DutyInputError("--check-against needs a profile built from --given-shares")
    cells = {}
    for c in prof["cells"]:
        if c not in measured:
            raise DutyInputError(f"{c}: no measured share to check the given one against")
        g, m = prof["shares"][c]["share"], measured[c]["share"]
        cells[c] = {"given": g, "measured_p90": m, "measured_exceeds_given": m > g, "runs": measured[c].get("runs"),
                    "given_source": prof["shares"][c].get("source"),
                    **({"share_from_taken": measured[c]["share_from_taken"], "share_from": measured[c]["share_from"]} if "share_from_taken" in measured[c] else {})}
    return {"profile_id": prof["profile_id"], "cells": cells, "exceeds": sorted(c for c, v in cells.items() if v["measured_exceeds_given"])}


def rerun_shares(prof: dict, measured: dict[str, dict]) -> dict[str, dict]:
    """The shares of the rerun curve (amendment 25(d)): each cell's share at the LARGER of its given value (25(c) as corrected by amendment 28), the
    given profile's, and its measured 90th percentile, so no cell's share falls. Every entry names both figures and which was taken (`raised`), in the shape `build_profile` reads. Only a
    profile built from given shares can be rerun against: the rerun profile itself is not one, so a rerun is never made against a rerun."""
    if prof.get("shares_kind") != "given":
        raise DutyInputError(f"a rerun is made against a profile built from --given-shares (the given shares: amendment 25(c) as corrected by amendment 28); this one's shares are {prof.get('shares_kind') or 'measured'}")
    out = {}
    for c in prof["cells"]:
        if c not in measured:
            raise DutyInputError(f"{c}: no measured share to rerun the given one against")
        g, m = prof["shares"][c], measured[c]
        gs, ms = float(g["share"]), float(m["share"])
        out[c] = {"share": max(gs, ms), "kind": "rerun", "given": gs, "measured_p90": ms, "raised": ms > gs, "runs": m.get("runs"), "given_source": g.get("source"),
                  "source": f"max(given {gs:.4g} [{g.get('source')}], measured p90 {ms:.4g} over {m.get('runs')} runs) (amendment 25(d))",
                  **{k: m[k] for k in ("share_from", "share_from_taken", "share_from_candidates") if k in m}}
    return out


def main_cap(first_cap: int | None, rerun_cap: int | None, rerun_made: bool = True) -> dict:
    """The main block's cap under amendment 25(d): the LOWER of the first curve's cap and the rerun's, and it never rises. Both are reported. A curve
    with no passing level has no cap (None), which is the lowest there is: if either curve has none, the main block has none. `rerun_made=False`: no
    cell's measured share exceeded its given share (amendment 28), so there was no rerun and the first curve's cap stands."""
    if not rerun_made:
        return {"cap": first_cap, "first_cap": first_cap, "rerun_cap": None, "rerun_made": False, "lower_of": "first", "rerun_above_first": False}
    if first_cap is None or rerun_cap is None:
        cap = None
    else:
        cap = min(first_cap, rerun_cap)
    lo = (-1 if first_cap is None else first_cap), (-1 if rerun_cap is None else rerun_cap)
    return {"cap": cap, "first_cap": first_cap, "rerun_cap": rerun_cap, "rerun_made": True,
            "lower_of": "equal" if lo[0] == lo[1] else ("first" if lo[0] < lo[1] else "rerun"),
            "rerun_above_first": first_cap is not None and rerun_cap is not None and rerun_cap > first_cap}


def ladder_of(prof: dict) -> dict:
    """The profile's sequence (`curve.sequence_state`): {"frozen": the levels, "climb": the subset that runs in order (all of them when the profile has
    none), "floor": the one level below the first (None when the profile has none)}."""
    return {"frozen": list(prof["levels"]), "climb": list(prof.get("climb") or prof["levels"]), "floor": prof.get("floor_level")}


def _stop_summary(lines: list[dict]) -> dict | None:
    """The last measured line of a level, as the cap's reader names the level that ended the cap."""
    measured = [r for r in lines if not r.get("infrastructure")]
    if not measured:
        return None
    r = measured[-1]
    ro = r.get("ran_on") if isinstance(r.get("ran_on"), dict) else None
    two = ro.get("two_hosts") if ro else (r.get("hosts") or {}).get("multi")
    m_bound = r.get("failed_on") == "m_bound"
    return {"level": int(r["level"]), "failed_on": r.get("failed_on"), "failed_for": r.get("failed_for"), "m_bound": m_bound, "rerun_of": r.get("rerun_of"),
            "two_hosts": two, "m_bound_waits": len(r.get("m_bound_waits") or []),
            "one_host_m_bound_without_rerun": bool(m_bound and two is False and not r.get("rerun_of"))}


def cap_from_decisions(path, block: int, rep: int = 1, *, traced: bool = True, profile: dict | None = None) -> dict:
    """One duty-cycle curve's cap from its `curve_decisions.jsonl`. A level's line is its last MEASURED one (an infrastructure line is no measurement, so a
    rerun's later line decides, and a level with only infrastructure lines is "undecided"). The lines of the block, rep and tracing state that name a
    duty profile must name exactly one. `final` is False when more is due: a level undecided, or one the sequence has yet to ask for.

    The sequence (science, #34, 3 Nov 00:33Z) is read by `curve.sequence_state` from the ladder every line carries (`ladder`, copied from its frozen
    profile; `profile=` names the profile itself and must agree with the lines): the climb, and the step-downs after a failure. The order the lines
    were written in does not matter. A line for a level the sequence never asked for (a 2 when 4 did not fail) raises. Lines without a ladder, and no
    `profile`, are an older curve, read as before: the last pass before the first level that did not pass, with `sequence_checked` False.

    `capped_by_level` is the lowest failing level above the cap and `stopped_on` its last line; `cap_bound_by` is that line's `failed_on` ("m_bound",
    "not_m_bound"), None when no level failed above the cap, "pending" when more is due. `not_run` (amendment 34(a); present only when the ladder is known): the sorted levels
    of the ladder, its frozen levels and its floor, that have no decision line."""
    from . import curve as Cv
    try:
        lines = Path(path).read_text().splitlines()
    except OSError as e:
        raise DutyInputError(f"{path}: {e}") from e
    by_level: dict[int, list[dict]] = {}
    ids = set()
    for ln in lines:
        try:
            r = json.loads(ln)
            if int(r["block"]) != block or int(r.get("rep", 1)) != rep or bool(r.get("traced", True)) is not traced or not r.get("duty_profile_id"):
                continue
            by_level.setdefault(int(r["level"]), []).append(r)
            ids.add(r["duty_profile_id"])
        except (ValueError, KeyError, TypeError, AttributeError):
            continue                                     # a torn last line or another curve's: no decision
    if not by_level:
        raise DutyInputError(f"{path}: no duty-cycle decision line for block {block}, rep {rep}, {'traced' if traced else 'untraced'}")
    if len(ids) != 1:
        raise DutyInputError(f"{path}: the lines name {len(ids)} different duty profiles ({sorted(i[:12] for i in ids)}): not one curve")
    levels: dict[int, str] = {}
    for lv in sorted(by_level):
        measured = [r for r in by_level[lv] if not r.get("infrastructure")]
        levels[lv] = "undecided" if not measured else ("pass" if measured[-1].get("passed") is True else "fail")
    stamps = {json.dumps(r["ladder"], sort_keys=True) for rs in by_level.values() for r in rs if isinstance(r.get("ladder"), dict)}
    if len(stamps) > 1:
        raise DutyInputError(f"{path}: the lines of one profile name {len(stamps)} different ladders")
    ladder = json.loads(next(iter(stamps))) if stamps else None
    if profile is not None:
        if profile.get("profile_id") != next(iter(ids)):
            raise DutyInputError(f"{path}: the lines name profile {next(iter(ids))[:12]}.., not the profile given ({str(profile.get('profile_id'))[:12]}..)")
        if ladder is not None and ladder != ladder_of(profile):
            raise DutyInputError(f"{path}: the ladder on the lines {ladder} is not the profile's {ladder_of(profile)}")
        ladder = ladder_of(profile)
    if ladder is None:                                   # an older curve: every level in order, stopping at the first that did not pass
        cap, stopped = None, None
        for lv, st in levels.items():
            if st != "pass":
                stopped = lv
                break
            cap = lv
        final, due = stopped is None or levels[stopped] == "fail", (stopped if stopped is not None and levels[stopped] != "fail" else None)
    else:
        try:
            st = Cv.sequence_state(ladder["frozen"], ladder["climb"], ladder.get("floor"), {lv: s_ == "pass" for lv, s_ in levels.items() if s_ != "undecided"})
        except (ValueError, KeyError, TypeError) as e:
            raise DutyInputError(f"{path}: the ladder {ladder}: {e}") from e
        if ladder["climb"] != ladder["frozen"] or ladder.get("floor") is not None:      # a sequence with step-downs: a level it never asked for cannot be read
            never = sorted(set(levels) - set(st["visited"]))
            if never:
                raise DutyInputError(f"{path}: levels {never} have decision lines but the sequence {ladder} never asked for them (a step-down runs only after a failure "
                                     f"directly above it): not one curve")
        cap, final, due = st["cap"], st["done"], st["next"]
        stopped = st["failed_at"] if st["failed_at"] is not None else due
    above = [lv for lv, s_ in levels.items() if s_ == "fail" and (cap is None or lv > cap)]
    capped_by = min(above) if above else None
    stopped_on = _stop_summary(by_level[capped_by]) if capped_by is not None else None
    bound = "pending" if not final else (None if stopped_on is None else (stopped_on["failed_on"] or "unknown"))
    out = {"path": str(path), "block": block, "rep": rep, "profile_id": next(iter(ids)), "levels": levels, "cap": cap, "stopped_at": stopped,
           "final": final, "next_level_due": due, "ladder": ladder, "sequence_checked": ladder is not None,
           "capped_by_level": capped_by, "stopped_on": stopped_on, "cap_bound_by": bound}
    if ladder is not None:        # amendment 34(a): the levels below a block's start (and above its cap's failure) are not measured; the table is reported with them marked not run
        out["not_run"] = sorted(({int(x) for x in ladder["frozen"]} | ({int(ladder["floor"])} if ladder.get("floor") is not None else set())) - set(levels))
    return out


# ---- amendment 28: the shares before the pilot -----------------------------------------------------------------------------------------------
SHARE_FACTOR = 1.5               # amendment 28 (25(c) had 2): the margin for re-reads and bursts
W_PERCENTILE = 10                # 25(c): W(l) is the 10th percentile of the sizing runs' T walls on layout l
W_METHODS = ("linear", "nearest-rank")


def refuse_inside_code_tree(path, what: str) -> Path:
    """`path` resolved (symlinks followed), refused when it lies inside what `codestamp` hashes (icsa/, config/, protocol/, tools/, pyproject.toml,
    uv.lock) of the tree this code runs from or of the current directory's. The hosts compare that hash, and the shares and the profile are set after the
    freeze: a file written there would change the code's version. `results/` is not hashed."""
    from .. import codestamp
    p = Path(path).resolve()
    for root in {Path(__file__).resolve().parents[2], Path.cwd().resolve()}:
        for r in codestamp.ROOTS:
            h = (root / r).resolve()
            if p == h or h in p.parents:
                raise DutyInputError(f"{what} {path} is inside {h}, which the code's hash covers (codestamp.ROOTS): the hosts would see another code version. "
                                     f"Write it outside icsa/, config/, protocol/, tools/, pyproject.toml and uv.lock (results/ is not hashed)")
    return p


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sizing_walls(path) -> dict:
    """The sizing runs' T walls per layout, from `results/34-sizing/manifest.jsonl`: {"sha256", "layouts": {layout: [{key, attempt, wall_s, censored}]}}.
    Only `event == "attempt"` rows count, and each must be option T, `state == "ended"` and `ended` "run" (finished) or "stopped" (censored by the cut-off).
    A censored run's time is its `wall_time_s`, its time so far at the cut-off (not `elapsed_s`, which stops at its last step). The set of censored runs
    must be the one the manifest's own `cutoff_done` row lists, with the same walls: else the manifest and its reading disagree, and it raises. A repeated
    (key, attempt), a row of another option, a run still in flight or an unknown ending raises: nothing is dropped silently."""
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as e:
        raise DutyInputError(f"{p}: {e}") from e
    attempts, cut = [], {}
    for n, ln in enumerate(raw.decode().splitlines(), 1):
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except ValueError as e:
            raise DutyInputError(f"{p}:{n}: {e}") from e
        if not isinstance(r, dict):
            raise DutyInputError(f"{p}:{n}: not a JSON object")
        if r.get("event") == "attempt":
            attempts.append((n, r))
        elif r.get("event") == "cutoff_done":
            for c in r.get("censored") or []:
                cut[(c.get("key"), c.get("attempt"))] = c.get("wall_time_s")
    layouts: dict[str, list[dict]] = {}
    seen = set()
    for n, r in attempts:
        key = (r.get("key"), r.get("attempt"))
        if key in seen:
            raise DutyInputError(f"{p}:{n}: attempt {key} twice")
        seen.add(key)
        if r.get("option") != "T":
            raise DutyInputError(f"{p}:{n}: {key} is option {r.get('option')!r}: W(l) is the T runs' walls")
        if r.get("state") != "ended" or r.get("ended") not in ("run", "stopped"):
            raise DutyInputError(f"{p}:{n}: {key} is state {r.get('state')!r}, ended {r.get('ended')!r}: a run in flight or of an unknown ending has no wall to take")
        w, lay = r.get("wall_time_s"), r.get("layout")
        if not _num(w) or w <= 0 or not isinstance(lay, str) or not lay:
            raise DutyInputError(f"{p}:{n}: {key}: wall_time_s {w!r}, layout {lay!r}")
        layouts.setdefault(lay, []).append({"key": key[0], "attempt": key[1], "wall_s": float(w), "censored": r["ended"] == "stopped"})
    stopped = {(x["key"], x["attempt"]): x["wall_s"] for rs in layouts.values() for x in rs if x["censored"]}
    if stopped != {k: (float(v) if _num(v) else v) for k, v in cut.items()}:
        raise DutyInputError(f"{p}: the runs ended 'stopped' ({sorted(stopped)}) are not the censored runs its cutoff_done row lists ({sorted(cut)}), or their walls differ")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "layouts": layouts}


def w_of_layout(walls: list[float], method: str, pct: int = W_PERCENTILE) -> float:
    """The 10th percentile of a layout's walls: numpy's linear interpolation, or nearest rank (the ceil(pct x n / 100)th smallest, in integers)."""
    if method not in W_METHODS:
        raise DutyInputError(f"W method {method!r}: one of {W_METHODS}")
    if not walls:
        raise DutyInputError("no sizing wall to take a percentile of")
    v = sorted(walls)
    if method == "linear":
        return float(np.quantile(v, pct / 100))
    return v[max(1, -(-pct * len(v) // 100)) - 1]


def baseline_runs(dirs: Iterable, traced: bool) -> tuple[list[dict], list[dict]]:
    """(the baseline runs, one {dir, run_files, sha256} per directory). The runs are what `duty-profile` reads: `runs/*/run.json`, an infrastructure
    attempt left out, a live probe's prefix record (`extra.probe_files`: a prefix of the cell, no run of the study, as `__main__._runs_of` leaves it out) left out, the
    enforced arm in the given tracing state, and a run under contention (a pool or a curve level) refused. The sha256 of a directory is that of its sorted (run directory,
    sha256 of run.json) pairs, for every run.json in it, the prefix records too: it names what was given."""
    recs, inputs = [], []
    for d in dirs:
        files = sorted(Path(d).glob("runs/*/run.json"))
        if not files:
            raise DutyInputError(f"{d}: no runs/*/run.json under it")
        h = hashlib.sha256()
        for f in files:
            raw = f.read_bytes()
            h.update(f.parent.name.encode() + b"\0" + hashlib.sha256(raw).digest())
            try:
                r = json.loads(raw)
            except ValueError as e:
                raise DutyInputError(f"{f}: invalid JSON: {e}") from e
            if not isinstance(r, dict):
                raise DutyInputError(f"{f}: not a JSON object")
            if not r.get("infrastructure") and (r.get("extra") or {}).get("probe_files") is None:
                recs.append(r)
        inputs.append({"dir": str(d), "run_files": len(files), "sha256": h.hexdigest()})
    base = [r for r in recs if (r.get("extra") or {}).get("variant", "enforced") == "enforced" and bool((r.get("extra") or {}).get("traced")) is traced]
    contended = sorted(str(r.get("run_key", "?")) for r in base if ((r.get("extra") or {}).get("pool_workers") or 1) > 1 or "level" in (r.get("extra") or {}))
    if contended:
        raise DutyInputError(f"the baselines hold runs under contention (a pool or a curve level): {contended[:5]}")
    return base, inputs


def cell_reads(base: list[dict], cells: Iterable[tuple[str, str]]) -> dict[tuple[str, str], dict]:
    """(option, layout) -> R(o,l): the median read phase (`curve.read_phase_s`) of the cell's clean baseline runs, all instances pooled, with each
    instance's own median and the counts. A cell without a clean run, a clean run without a read phase, or a median that is not above 0 raises."""
    from . import curve as Cv
    out = {}
    for o, la in cells:
        rs = [r for r in base if (r.get("option"), r.get("layout")) == (o, la)]
        vals, by_inst = [], {}
        for r in rs:
            if not Cv.clean(r):
                continue
            v = Cv.read_phase_s(r)
            if v is None:
                raise DutyInputError(f"{r.get('run_key')}: a clean {o}/{la} baseline run without a read phase: R({o},{la}) cannot be formed")
            vals.append(v)
            by_inst.setdefault(str(r.get("instance_id")), []).append(v)
        if not vals:
            raise DutyInputError(f"no clean baseline read for {o}/{la} ({len(rs)} baseline runs of the cell): its share cannot be formed, and none is defaulted")
        med = statistics.median(vals)
        if not med > 0:
            raise DutyInputError(f"{o}/{la}: the median baseline read phase is {med}: not above 0")
        out[(o, la)] = {"read_s": med, "runs": len(vals), "not_clean": len(rs) - len(vals), "by_instance_s": {i: statistics.median(v) for i, v in sorted(by_inst.items())}}
    return out


def amendment_28_shares(cells: Iterable[tuple[str, str]], reads: dict, sizing: dict, baseline_inputs: list[dict], *, method: str = "linear",
                        factor: float = SHARE_FACTOR, sizing_path="") -> dict[str, dict]:
    """Amendment 28: s(o, l) = min(1, factor x R(o, l) / W(o, l)), W(o, l) = W(l) + R(o, l) - R(T, l). R(o, l) is the cell's baseline median read
    (`cell_reads`), W(l) the 10th percentile (`w_of_layout`) of the sizing runs' T walls on the layout, censored runs at their time so far. Every
    option, T-unpaginated too, takes the formula as it stands. Needs T among the cells (R(T, l)), the layout among the sizing runs, and W(o, l) above 0,
    else it raises. Returns "<option>/<layout>" -> {"share", "source", "provenance"}: `source` is the whole provenance in one line (it is what
    `--given-shares` carries into the hashed profile), `provenance` the same figures structured."""
    cells = list(cells)
    out = {}
    for o, la in cells:
        if ("T", la) not in reads:
            raise DutyInputError(f"{o}/{la}: R(T, {la}) is needed (W(o, l) = W(l) + R(o, l) - R(T, l)) and T is not among the block's cells")
        runs = sizing["layouts"].get(la) or []
        if not runs:
            raise DutyInputError(f"no sizing run of T on layout {la}: W({la}) cannot be formed")
        w_l = w_of_layout([x["wall_s"] for x in runs], method)
        r_o, r_t = reads[(o, la)]["read_s"], reads[("T", la)]["read_s"]
        w_o = w_l + r_o - r_t
        if not w_o > 0:
            raise DutyInputError(f"{o}/{la}: W(o,l) = W({la}) {w_l:.3f} + R({o}) {r_o:.3f} - R(T) {r_t:.3f} = {w_o:.3f} s is not above 0: refused")
        raw = factor * r_o / w_o
        share = min(1.0, raw)
        other = w_of_layout([x["wall_s"] for x in runs], "nearest-rank" if method == "linear" else "linear")
        prov = {"amendment": "28 (corrects 25(c))", "rule": "s = min(1, factor x R(o,l) / W(o,l)), W(o,l) = W(l) + R(o,l) - R(T,l)", "factor": factor,
                "R_s": r_o, "R_T_s": r_t, "W_l_s": w_l, "W_o_l_s": w_o, "uncapped": raw, "capped_at_1": raw > 1.0,
                "w_method": method, "w_percentile": W_PERCENTILE, "w_l_by_the_other_method_s": other,
                "sizing": {"file": str(sizing_path), "sha256": sizing["sha256"], "layout": la, "runs": len(runs), "censored": sum(x["censored"] for x in runs),
                           "censored_taken_at": "wall_time_s, the time so far at the cut-off"},
                "baselines": {"cell_runs": reads[(o, la)]["runs"], "cell_runs_not_clean": reads[(o, la)]["not_clean"], "t_cell_runs": reads[("T", la)]["runs"],
                              "by_instance_s": reads[(o, la)]["by_instance_s"], "inputs": baseline_inputs}}
        src = (f"amendment 28 (corrects 25(c)): s = min(1, {factor:g} x R(o,l) / W(o,l)), W(o,l) = W(l) + R(o,l) - R(T,l); "
               f"R({o},{la}) = {r_o:.3f} s (median of {reads[(o, la)]['runs']} clean baseline reads), R(T,{la}) = {r_t:.3f} s; "
               f"W({la}) = {w_l:.3f} s ({W_PERCENTILE}th percentile, {method}, of {len(runs)} T sizing walls, {prov['sizing']['censored']} censored taken at their time so far; "
               f"the other method: {other:.3f} s); W({o},{la}) = {w_o:.3f} s; uncapped {raw:.6g}, capped at 1: {'yes' if raw > 1.0 else 'no'}; "
               f"sha256 sizing {sizing['sha256']}, baselines {', '.join(i['sha256'] for i in baseline_inputs)}")
        out[f"{o}/{la}"] = {"share": share, "source": src, "provenance": prov}
    return out


def write_new(path: Path, text: str) -> None:
    """Writes `text` to a new file `path`, atomically (a temporary file in the same directory, linked into place) and never over an existing one."""
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise DutyInputError(f"{path} exists: shares are never overwritten; use a new file") from None
    finally:
        os.unlink(tmp)


def baseline_image_problem(dirs, run_image_id: str | None = None) -> str | None:
    """Why these baseline directories cannot be read against one run's image, or None. A curve, a duty profile or the shares read against baselines of another build
    give a wrong cap with no error, so every command that reads baselines asks this first (the manifests are `MANIFEST_baseline*.json`, read by `liveprobe`).
    A directory whose manifests name more than one image, or directories that name more than one between them, are a problem always. With `run_image_id` (a command
    that starts sandboxes), the baselines' image must be that one, and a directory that names no image is a problem, as an image that cannot be told is not the same
    image. Without it (`duty-profile` and `shares` start no sandbox), a directory that names no image is not a problem by itself."""
    from . import liveprobe        # a function-level import: liveprobe reaches the runner, which this module need not load to be defined
    dirs = [Path(d) for d in dirs]
    by_dir = {d: liveprobe.baseline_image_ids([d]) for d in dirs}
    for d, ids in by_dir.items():
        if len(ids) > 1:
            return f"baseline directory {d}: its manifests name more than one image ({', '.join(sorted(i[:19] for i in ids))}); its runs are not one build's"
    named = sorted(set().union(*by_dir.values()))
    if len(named) > 1:
        return f"the baseline directories name more than one image ({', '.join(i[:19] for i in named)}); their runs are not one build's"
    if run_image_id is None:
        return None
    for d, ids in by_dir.items():
        if not ids:
            return f"baseline directory {d} names no image (no MANIFEST_baseline*.json with an image_id): an image that cannot be told is not this run's image {run_image_id[:19]}"
    if named and named[0] != run_image_id:
        return f"the baselines were run on image {named[0][:19]}, this run's image is {run_image_id[:19]}: a curve read against them would give a wrong cap"
    return None


def _main_shares(a) -> int:
    from . import plans
    try:
        if a.block not in plans.BLOCK_CELLS:
            raise DutyInputError(f"block {a.block}: the blocks are {sorted(plans.BLOCK_CELLS)}")
        out = refuse_inside_code_tree(a.out, "--out")
        if out.exists():
            raise DutyInputError(f"{out} exists: shares are never overwritten; use a new file")
        if (why := baseline_image_problem(a.baseline)):
            raise SystemExit(why)
        cells = [(o.value, la.value) for o, la in plans.BLOCK_CELLS[a.block]]
        base, inputs = baseline_runs(a.baseline, traced=not a.untraced)
        shares = amendment_28_shares(cells, cell_reads(base, cells), sizing_walls(a.sizing), inputs, method=a.w_method, sizing_path=a.sizing)
        write_new(out, json.dumps(shares, indent=1) + "\n")
    except (DutyInputError, OSError, ValueError) as e:
        raise SystemExit(f"shares: {e}")
    print(json.dumps({"shares_file": str(out), "sha256": file_sha256(out), "block": a.block, "w_method": a.w_method,
                      "cells": {c: {"share": round(v["share"], 4), "capped_at_1": v["provenance"]["capped_at_1"]} for c, v in shares.items()}}, indent=1))
    return 0


def _read_profile(path, what: str) -> dict:
    prof = json.loads(Path(path).read_text())
    if prof.get("format") != FORMAT or prof.get("profile_id") != profile_id(prof):
        raise DutyInputError(f"{path}: not a duty profile, or its body does not match its profile_id")
    return prof


NO_MAIN_CAP = "NO MAIN CAP: no level passed at 8, 4, 2 (amendment 30(i)): this goes to science, and no main run starts"


def main(argv: list[str] | None = None) -> int:
    """`python -m icsa.scripted.duty main-cap --first DIR [--rerun DIR] [--first-profile FILE] [--rerun-profile FILE] [--block N] [--rep N] [--untraced]`: prints
    the main block's cap from the two curves' decision files (`main_cap`), with both curves' caps and levels. `--rerun-profile` checks that the rerun curve ran
    the profile `duty-profile --rerun-against` made from the first curve's; `--first-profile` names the first curve's profile, whose ladder the lines must
    agree with. The output's top level says `final`: true only when every curve read is final (nothing more is due: no level undecided, none the sequence has
    yet to ask for). Exit 0 when final, 2 when not (the cap printed is then provisional), and 3 when a finished curve has no cap (`NO_MAIN_CAP` on stderr, the JSON as it is: amendment 30(i)); `m_bound`: whether the cap was set by M's bound.

    `python -m icsa.scripted.duty shares --block N --baseline DIR.. --sizing MANIFEST --out FILE`: amendment 28's shares, for `duty-profile --given-shares`."""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m icsa.scripted.duty")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("main-cap", help="the main block's cap: the lower of the first curve's and the rerun's (amendment 25(d))")
    s.add_argument("--first", required=True, metavar="DIR", help="the first curve's --out (its curve_decisions.jsonl)")
    s.add_argument("--rerun", default=None, metavar="DIR", help="the rerun curve's --out; omitted: no rerun was needed and the first curve's cap stands")
    s.add_argument("--first-profile", default=None, metavar="FILE", help="the first curve's profile (duty_profile_block<N>.json): the lines' ladder must be its own")
    s.add_argument("--rerun-profile", default=None, metavar="FILE", help="the rerun profile (duty_profile_block<N>_rerun.json): checked to be made from the first curve's profile")
    s.add_argument("--block", type=int, default=1)
    s.add_argument("--rep", type=int, default=1)
    s.add_argument("--untraced", action="store_true")
    sh = sub.add_parser("shares", help="amendment 28's shares s = min(1, 1.5 x R(o,l) / W(o,l)) from the baselines and the sizing runs, for duty-profile --given-shares")
    sh.add_argument("--block", type=int, required=True)
    sh.add_argument("--baseline", nargs="+", required=True, metavar="DIR", help="the single-run baselines' results directories (runs/*/run.json): R(o,l) is each cell's median read phase")
    sh.add_argument("--sizing", required=True, metavar="MANIFEST", help="the sizing runs' manifest.jsonl (results/34-sizing/manifest.jsonl): W(l) is the 10th percentile of its T walls on the layout")
    sh.add_argument("--out", required=True, metavar="FILE", help="the shares file (never inside the code tree the hosts hash; an existing file is never overwritten)")
    sh.add_argument("--untraced", action="store_true", help="untraced baselines")
    sh.add_argument("--w-method", choices=W_METHODS, default="linear", help="how W(l)'s 10th percentile is formed (amendment 25(c) does not say): numpy's linear interpolation, as the shares' own p90, or nearest rank, as the sizing report")
    a = ap.parse_args(argv)
    if a.cmd == "shares":
        return _main_shares(a)
    try:
        first_prof = _read_profile(a.first_profile, "first") if a.first_profile else None
        rerun_prof = _read_profile(a.rerun_profile, "rerun") if a.rerun_profile else None
        first = cap_from_decisions(Path(a.first) / "curve_decisions.jsonl", a.block, a.rep, traced=not a.untraced)
        rerun = cap_from_decisions(Path(a.rerun) / "curve_decisions.jsonl", a.block, a.rep, traced=not a.untraced) if a.rerun else None
        if a.rerun_profile and rerun is None:
            raise DutyInputError("--rerun-profile needs --rerun")
        if rerun is not None and rerun["profile_id"] == first["profile_id"]:
            raise DutyInputError("the two decision files are of the same profile: a rerun curve runs the rerun profile, not the first one again")
        if rerun_prof is not None:
            if (rerun_prof.get("provenance") or {}).get("rerun_of_profile_id") != first["profile_id"]:
                raise DutyInputError(f"the rerun profile {a.rerun_profile} is not made from the first curve's profile {first['profile_id'][:12]}..")
            if rerun_prof["profile_id"] != rerun["profile_id"]:
                raise DutyInputError(f"the rerun curve ran profile {rerun['profile_id'][:12]}.., not the rerun profile {rerun_prof['profile_id'][:12]}..")
        if first_prof is not None:        # the profiles' own ladders judge what is still due (`cap_from_decisions` checks the lines name them)
            first = cap_from_decisions(Path(a.first) / "curve_decisions.jsonl", a.block, a.rep, traced=not a.untraced, profile=first_prof)
        if rerun_prof is not None:
            rerun = cap_from_decisions(Path(a.rerun) / "curve_decisions.jsonl", a.block, a.rep, traced=not a.untraced, profile=rerun_prof)
    except (DutyInputError, OSError, ValueError) as e:
        raise SystemExit(f"main-cap: {e}")
    res = main_cap(first["cap"], None if rerun is None else rerun["cap"], rerun_made=rerun is not None)
    curves = {"first": first, **({"rerun": rerun} if rerun is not None else {})}
    final = all(c["final"] for c in curves.values())          # a cap read before a curve is final is provisional: it may still rise or fall
    no_cap = res["cap"] is None and any(c["cap"] is None and c["final"] for c in curves.values())      # a curve that is done and has none: the main cap is none whatever the other says (it never rises)
    setting = {n: c for n, c in curves.items() if c["cap"] == res["cap"]}          # the curves whose cap is the main cap
    m_bound = any(c["cap_bound_by"] == "m_bound" for c in setting.values())
    ran = {lv for c in curves.values() for lv, st in c["levels"].items() if st != "undecided"}      # the levels the curves ran: "one level below the cap means a level the curve ran" (30(a))
    start_equals_cap = None if res["cap"] is None else not any(lv < res["cap"] for lv in ran)      # the cap is the lowest level run: none below it, so main starts at the cap
    print(json.dumps({"block": a.block, "rep": a.rep, "main_cap": res["cap"], "start_equals_cap": start_equals_cap, "final": final, "m_bound": m_bound,
                      "cap_bound_by": {n: c["cap_bound_by"] for n, c in curves.items()},
                      **({"provisional_because": {n: {"next_level_due": c["next_level_due"], "stopped_at": c["stopped_at"]} for n, c in curves.items() if not c["final"]}} if not final else {}),
                      **{k: v for k, v in res.items() if k != "cap"}, "first": first, "rerun": rerun}, indent=1))
    if no_cap:
        print(NO_MAIN_CAP, file=sys.stderr)
        return 3
    return 0 if final else 2


def profile_id(prof: dict) -> str:
    body = {k: v for k, v in prof.items() if k != "profile_id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def single_totals(rows: Iterable[dict]) -> dict[tuple[str, str, str], float]:
    """(option, layout, instance) -> median `total_s` (the whole `run_one`, sandbox start to teardown) of its clean single runs."""
    from . import curve as Cv
    got: dict[tuple[str, str, str], list[float]] = {}
    for r in rows:
        if Cv.clean(r) and _num(r.get("total_s")) and r["total_s"] > 0:
            got.setdefault((r["option"], r["layout"], r["instance_id"]), []).append(float(r["total_s"]))
    return {k: statistics.median(v) for k, v in got.items()}


def build_profile(shares: dict[str, dict], single_total: dict[tuple[str, str, str], float], single_read: dict[tuple[str, str, str], float], *,
                  block: int, cells: Iterable[tuple[str, str]], instances: Iterable[str], seed: int, traced: bool, levels: Iterable[int] = (),
                  jitter: float = JITTER, max_m_runs: int = MAX_M_RUNS, shares_kind: str | None = None, provenance: dict | None = None,
                  climb: Iterable[int] | None = None, floor_level: int | None = None) -> dict:
    """The frozen schedule: per (option, layout, instance) the gap after its run, `read / share - total` (0 and flagged when negative), and the
    levels the curve will try, frozen with it (strictly ascending: the search goes upward).

    `climb` and `floor_level` (science, #34, 3 Nov 00:33Z; the sequence is `curve.sequence_state`): the frozen levels are 4, 8, 12, 16, 24, 32, 42, the
    climb is the subset that runs in order (8, 16, 24, 32, 42), and a failure tests the frozen level below it; the floor is the one level below the
    first frozen one (2), run only after a failing 4. Both are frozen with the levels and recorded (hashed) only when set, so a profile without them
    keeps its hash and is read as before: every level in order, stopping at the first failure."""
    levels = [int(x) for x in levels]
    if levels and (levels[0] < 2 or any(b <= a for a, b in zip(levels, levels[1:]))):
        raise DutyInputError(f"levels {levels}: must start at 2 or more (the baselines are level 1) and be strictly ascending")
    if floor_level is not None and (isinstance(floor_level, bool) or not isinstance(floor_level, int) or not levels or not 2 <= floor_level < levels[0]):
        raise DutyInputError(f"floor level {floor_level!r}: must be a whole number from 2 up to below the first level {levels[:1]}")
    if climb is not None:
        climb = [int(x) for x in climb]
        if not climb or any(b <= a for a, b in zip(climb, climb[1:])) or not set(climb) <= set(levels) | ({floor_level} if floor_level is not None else set()):
            raise DutyInputError(f"climb {climb}: must be a non-empty, strictly ascending subset of the levels {levels} and the floor {floor_level} "
                                 f"(the rerun of a first curve whose cap is the floor climbs [floor])")
    gaps = {}
    for o, la in cells:
        sh = shares[f"{o}/{la}"]["share"]
        for i in instances:
            w, rd = single_total.get((o, la, i)), single_read.get((o, la, i))
            if not _num(w) or not _num(rd) or w <= 0 or rd <= 0:
                raise DutyInputError(f"{o}/{la}/{i}: no single-run total ({w}) or read phase ({rd}) to set its gap from")
            g = rd / sh - w
            gaps[f"{o}/{la}/{i}"] = {"gap_s": round(max(g, 0.0), 3), "loaded_above_share": g < 0, "single_total_s": w,
                                     "single_read_s": rd, "share": sh}
    prof = {"format": FORMAT, "block": block, "cells": [f"{o}/{la}" for o, la in cells], "instances": list(instances), "seed": seed,
            "traced": traced, "levels": levels, "tau_s": TAU_S, "jitter": jitter, "max_m_runs": max_m_runs, "shares": shares, "gaps": gaps}
    if shares_kind:                  # recorded (and hashed) only when not the measured default, so a measured profile's hash is unchanged
        prof["shares_kind"] = shares_kind
    if climb is not None:
        prof["climb"] = climb
    if floor_level is not None:
        prof["floor_level"] = int(floor_level)
    if provenance:                   # the rerun profile's: which profile it was made from, and which cells were over (hashed, so it cannot be changed after)
        prof["provenance"] = provenance
    prof["profile_id"] = profile_id(prof)
    return prof


def load_profile(path, *, block: int, instances: Iterable[str], seed: int, traced: bool) -> dict:
    """A frozen profile, refused when its hash does not match its body or it was made for another block, instance set, seed or tracing state."""
    prof = json.loads(Path(path).read_text())
    if prof.get("format") != FORMAT or prof.get("profile_id") != profile_id(prof):
        raise DutyInputError(f"{path}: not a duty profile, or its body does not match its profile_id")
    want = {"block": block, "instances": list(instances), "seed": seed, "traced": traced}
    diff = {k: (prof.get(k), v) for k, v in want.items() if prof.get(k) != v}
    if diff:
        raise DutyInputError(f"{path}: made for another run ((profile, now): {diff})")
    return prof


def paced_waits(runs: Iterable[dict], over_s: float = 1.0) -> list[str]:
    """The counted runs that waited longer than `over_s` for the pacer's guards (a live slot, an M slot): the level's offered load was capped
    there, so it cannot pass. A run without the record of its wait counts as having waited: it cannot show it did not."""
    out = []
    for r in runs:
        w = (r.get("extra") or {}).get("pace_wait_s")
        v = w.get("live_wait_s") if isinstance(w, dict) else None
        if not _num(v) or v > over_s:
            out.append(r.get("run_key", "?"))
    return sorted(out)


M_IDLE_OVER_S = 1.0          # science, #34, 22:16Z: an M-only tail that waited idle for an M slot longer than this left its slot without a sandbox
GUARD_CAP_REASON = "load capped by the guards (host memory or M runs above max_m_runs): the level's load was not tested"
M_BOUND_REASON = "load capped by M's bound: a slot sat idle for an M slot (its host at its share of M users) for more than 1 s, so the level's load was not tested"


def m_idle_waits(runs: Iterable[dict], over_s: float = M_IDLE_OVER_S) -> list[dict]:
    """The counted runs that waited IDLE for an M slot longer than `over_s` (`extra.m_deferral.idle_s`, written by `mgate.cells` when only M cells were
    left and the host was at its share of M slot users: the slot then holds no sandbox). Like a wait for the pacer's guards, it caps the level's offered
    load, so it cannot pass. A deferral that only reordered the slot's cells (`idle_s` 0: a non-M cell ran first) is by design and never counts, however
    long it lasted. A record with no `m_deferral` was never deferred: it has no idle wait, which is not an unknown one. A deferral whose idle time is not a
    number cannot show it did not idle, and counts (with `idle_s` None). [{run_key, slot, idle_s}], by run key."""
    out = []
    for r in runs:
        ex = r.get("extra") or {}
        d = ex.get("m_deferral")
        if ex.get("padding") or d is None:
            continue
        v = d.get("idle_s") if isinstance(d, dict) else None
        if not _num(v) or v > over_s:
            out.append({"run_key": r.get("run_key", "?"), "slot": ex.get("slot"), "idle_s": round(float(v), 3) if _num(v) else None})
    return sorted(out, key=lambda w: str(w["run_key"]))


def duty_verdict(passed: bool, guard_waits: list, m_waits: list, gaps: Iterable[str] = ()) -> dict:
    """The paced level's verdict and why, in one place for `cmd_curve` and `curve-multi` alike. `passed`: everything the rule says before the paced waits
    (every cell's wall and read ratio, no error or OOM, no earlyoom kill, M within its share). `failed_on`:
    - "m_bound": the level would have passed but for M's idle waits (`m_waits`): the table passes, no guard waits, nothing else failing;
    - "not_m_bound": any other failing level, whatever failed it (not a claim that site_g was the limit: the fields beside it say what), including one that ALSO has M idle waits or lacks part of its plan (`gaps`: `level_gaps`), which did not fail only on M's bound;
    - None: a pass.
    Returns {"passed", "failed_on", "failed_for"}."""
    if not passed:
        return {"passed": False, "failed_on": "not_m_bound", "failed_for": None}
    why = ([GUARD_CAP_REASON] if guard_waits else []) + ([f"the level's counted runs are not the whole plan: {'; '.join(gaps)}"] if gaps else [])
    if why:                   # a pass under a capped load would not show the level holds its load, and one on part of the plan would not show it at all
        return {"passed": False, "failed_on": "not_m_bound", "failed_for": "; ".join(why)}
    if m_waits:
        return {"passed": False, "failed_on": "m_bound", "failed_for": M_BOUND_REASON}
    return {"passed": True, "failed_on": None, "failed_for": None}


def apply_verdict(rec: dict, passed: bool, guard_waits: list, m_waits: list, gaps: Iterable[str] = ()) -> bool:
    """Writes `duty_verdict` into a duty level's decision line (`passed`, and `failed_on` / `failed_for` where there is one; `m_bound_waits` wherever any
    exist) and returns whether the level passed. Infrastructure lines never come here."""
    gaps = list(gaps)
    v = duty_verdict(passed, guard_waits, m_waits, gaps)
    rec["passed"] = v["passed"]
    if gaps:
        rec["coverage_gaps"] = gaps
    if v["failed_on"]:
        rec["failed_on"] = v["failed_on"]
        rec["m_bound"] = v["failed_on"] == "m_bound"         # the cause as a plain boolean: "not_m_bound" is easy to misread as a claim about the limit
    if v["failed_for"]:
        rec["failed_for"] = v["failed_for"]
    if m_waits:
        rec["m_bound_waits"] = m_waits
    return v["passed"]


def mount_reads(counted: Iterable[dict], own_read: dict, host_ratios: dict | None = None) -> dict:
    """Each M sandbox's own read figures at a level (science, #34, 3 Nov 00:11Z: "record each mount's reads at every curve level"), so a level can be
    judged per mount later. A counted M run is one sandbox with its own mount; per mount: the host it ran on (`extra.host`; "local" on a one-host curve,
    as `mgate.m_report` has it), its slot and slot user, the run's read phase (`curve.read_phase_s`, the quantity the rule judges), its ratio to that
    instance's single-run read phase (`own_read`, which `curve.level_table` uses, given as `single_read_s`), and its reads: the number of per-day reads in
    `script.per_day_s` and their median. A figure the record cannot show is None and `not_shown` says why: never a 0. With `host_ratios` (a curve judged
    with a host reference) the `single_read_s` of a mount is its host's reference (`curve.run_reference`), so its `ratio` is what the rule judged."""
    from . import curve as Cv
    mounts = []
    for r in counted:
        if r.get("option") not in MOUNT:
            continue
        ex, tok, script = r.get("extra") or {}, r.get("token") or {}, r.get("script") or {}
        rv = Cv.read_phase_s(r)
        base = own_read.get((r.get("option"), r.get("layout"), r.get("instance_id"))) if host_ratios is None else Cv.run_reference({}, own_read, r, host_ratios)[1]
        base = float(base) if _num(base) and base > 0 else None
        pd = script.get("per_day_s")
        pd = pd if isinstance(pd, list) and pd and all(_num(x) and x >= 0 for x in pd) else None
        why = ([] if rv is not None else ["no read phase on the record (a stamp is missing)"]) + ([] if base else ["no single-run read phase for its instance"]) \
            + ([] if pd else ["no per-read times on the record"])
        m = {"run_key": r.get("run_key"), "host": ex.get("host", "local"), "slot": ex.get("slot"), "m_user": tok.get("subject"), "instance_id": r.get("instance_id"),
             "layout": r.get("layout"), "clean": Cv.clean(r), "read_phase_s": None if rv is None else round(rv, 3), "single_read_s": None if base is None else round(base, 3),
             "ratio": None if rv is None or base is None else round(rv / base, 3), "reads": None if pd is None else len(pd),
             "per_read_median_s": None if pd is None else round(statistics.median(pd), 6)}
        if why:
            m["not_shown"] = "; ".join(why)
        mounts.append(m)
    mounts.sort(key=lambda m: (str(m["host"]), str(m["slot"]), str(m["run_key"])))
    shown = [m for m in mounts if m["ratio"] is not None and m["clean"]]
    worst = max(shown, key=lambda m: m["ratio"], default=None)
    hosts: dict[str, dict] = {}
    for m in mounts:
        h = hosts.setdefault(str(m["host"]), {"mounts": 0, "shown": 0, "worst_ratio": None})
        h["mounts"] += 1
        if m in shown:
            h["shown"] += 1
            h["worst_ratio"] = m["ratio"] if h["worst_ratio"] is None else max(h["worst_ratio"], m["ratio"])
    return {"unit": "one counted M run: its own sandbox and mount", "mounts": mounts, "n": len(mounts), "n_shown": len(shown), "n_not_shown": len(mounts) - len(shown),
            "worst_ratio": None if worst is None else worst["ratio"], "worst_run_key": None if worst is None else worst["run_key"], "by_host": hosts}


def ran_on(counts: dict, multi: bool, counted: Iterable[dict] | None, m_shares: dict | None) -> dict:
    """Where a duty level ran, on the decision line itself: `two_hosts` (a level across both hosts is a different line from the same level on one),
    `hosts` (the host -> its sandboxes), and per host its M users: the slot users seen on the level's M runs (`token.subject`; None for a line with no
    records, which is not "none") and the host's M share where the launcher has it (None otherwise: unknown is not 0)."""
    seen: dict[str, set | None] = {h: (None if counted is None else set()) for h in counts}
    nouser = {h: 0 for h in counts}
    for r in counted or []:
        if r.get("option") in MOUNT:
            h = (r.get("extra") or {}).get("host", "local")
            u = (r.get("token") or {}).get("subject")
            if u is None:
                nouser[h] = nouser.get(h, 0) + 1
            else:
                seen.setdefault(h, set()).add(u)
    return {"two_hosts": bool(multi), "hosts": {h: int(n) for h, n in counts.items()},
            "m_users": {h: {"seen": None if seen[h] is None else sorted(seen[h]), "n_seen": None if seen[h] is None else len(seen[h]), "runs_without_user": nouser.get(h, 0),
                            "share": (m_shares or {}).get(h)} for h in sorted(seen)}}


def ladder_stamp(prof: dict) -> dict:
    """The profile's sequence on every decision line (`ladder`), so a reader of the lines alone knows which levels were asked for and in what order."""
    return {"ladder": ladder_of(prof)}


def level_record(prof: dict, counted: Iterable[dict] | None, own_read: dict, counts: dict, multi: bool, m_shares: dict | None = None,
                 host_ratios: dict | None = None) -> dict:
    """The fields a duty-cycle level's decision line carries beside the verdict: its `ladder`, where it `ran_on`, and (with records) each mount's reads,
    `m_reads`. One function for `cmd_curve` and `curve-multi`, so a one-host and a two-host line differ only in what they ran on."""
    counted = None if counted is None else list(counted)
    return {**ladder_stamp(prof), "ran_on": ran_on(counts, multi, counted, m_shares),
            **({"m_reads": mount_reads(counted, own_read, host_ratios)} if counted is not None else {})}


def level_gaps(rows: Iterable[dict], block: int, level: int, rep: int) -> list[str]:
    """What the counted records of a duty level lack of its plan, [] when they are all there (review S1, finding 5). The level's counted runs are
    `plans.duty_slots`: every slot s of the `level` slots runs `plans.duty_cycles` cycles n, tagged `mix-b<block>-c<level>-r<rep>-s<s>-n<n>`, which
    every record carries, so the expected set needs neither the seed nor the instances. A level cut short has fewer records, and each cell's ratio list
    is nonempty from its first read, so `curve.level_table` alone passes it: the level is accepted only with every planned run recorded once and at
    least `plans.DUTY_MIN_READS` counted reads in every cell of the block. Padding and warm-up runs are not counted; records of another block, level or
    rep are not this level's."""
    from collections import Counter
    from . import curve as Cv
    from . import plans
    cells = [(o.value, la.value) for o, la in plans.BLOCK_CELLS[block]]

    def mine(r: dict) -> bool:
        e = r.get("extra") or {}
        return (e.get("block"), e.get("level"), e.get("rep")) == (block, level, rep)
    got = [r for r in Cv.counted(rows) if mine(r)]
    tags = [str(r.get("tag")) for r in got]
    want = {f"mix-b{block}-c{level}-r{rep}-s{s}-n{j}" for s in range(level) for j in range(plans.duty_cycles(level, len(cells)))}
    gaps = []
    missing = sorted(want - set(tags))
    if missing:
        gaps.append(f"{len(missing)} of {len(want)} counted runs of the plan have no record (first: {missing[:3]})")
    unexpected = sorted(set(tags) - want)
    if unexpected:
        gaps.append(f"{len(unexpected)} counted runs are not in the plan (first: {unexpected[:3]})")
    dup = sorted({t for t in tags if tags.count(t) > 1})
    if dup:
        gaps.append(f"{len(dup)} counted runs duplicated (first: {dup[:3]})")
    reads = Counter((r.get("option"), r.get("layout")) for r in got)
    short = {f"{o}/{la}": reads.get((o, la), 0) for o, la in cells if reads.get((o, la), 0) < plans.DUTY_MIN_READS}
    if short:
        gaps.append(f"cells below {plans.DUTY_MIN_READS} reads: {short}")
    return gaps


def report_vetoes(counted: Iterable[dict], decisions: dict[tuple[int, int, int], str | None] | None = None) -> dict[int, dict[int, list[str]]]:
    """block -> level -> why the duty-cycle rule fails that level, for `emit.scripted_timing`: the part of `cmd_curve`'s decision that
    `curve.level_table` cannot see (review S1, findings 4 and 5). Over the counted records that carry a duty profile (the registered mix has none, and
    is judged as it always was): (a) any run that waited over 1 s for the pacer's guards (`paced_waits`: the offered load was capped), (b) a level
    that lacks part of its plan (`level_gaps`), and, if `decisions` is given, (c) a level with no decision line (it was cut short), and (d) a
    level whose last decision line says it failed, whatever the reason (earlyoom, the M gate's share, an infrastructure failure of a part): a
    failure recorded stays one, also for a level none of whose records survived. `decisions`: (block, level, rep) -> None for a passing line, else why
    it failed (`curve.duty_decisions`); None: no decision file was read, and (c) and (d) are not applied."""
    groups: dict[tuple[int, int, int], list[dict]] = {}
    for r in counted:
        e = r["extra"]
        if e.get("duty_profile"):
            groups.setdefault((int(e["block"]), int(e["level"]), int(e["rep"])), []).append(r)
    out: dict[int, dict[int, list[str]]] = {}

    def add(b: int, lv: int, why: str) -> None:
        out.setdefault(b, {}).setdefault(lv, []).append(why)
    for (b, lv, rep), rs in sorted(groups.items()):
        waits = paced_waits(rs)
        if waits:
            add(b, lv, f"rep {rep}: {len(waits)} counted runs waited over 1 s for the pacer's guards (first: {waits[:3]}): the level's load was capped")
        for g in level_gaps(rs, b, lv, rep):
            add(b, lv, f"rep {rep}: {g}")
        if decisions is not None and (b, lv, rep) not in decisions:
            add(b, lv, f"rep {rep}: no decision line for the level: it was cut short or never finished")
    for (b, lv, rep), why in sorted((decisions or {}).items()):
        if why is not None:
            add(b, lv, f"rep {rep}: recorded as failed: {why}")
    return out


def composed_id(baseline_id: str, prof_id: str) -> str:
    """The id a duty-cycle level's decision is judged against: the baselines and the profile together, so a resume under another profile is refused."""
    return hashlib.sha256(f"{baseline_id}:{prof_id}".encode()).hexdigest()


class Pacer:
    """The schedule at one level, for `run_mix`: offsets, gaps and the concurrency guards. Seeded per (seed, block, level, rep, slot), apart from the
    padding plans' stream. `max_live` caps the sandboxes up at once (host memory) and `max_m_runs` the M runs; a run that waited records it."""

    def __init__(self, prof: dict, *, level: int, rep: int, max_live: int):
        if max_live < 1:
            raise DutyInputError(f"max_live {max_live}: no sandbox fits")
        self.prof, self.level, self.rep = prof, level, rep
        self.id = prof["profile_id"]
        self.live = threading.BoundedSemaphore(max_live)
        self.mounts = threading.BoundedSemaphore(int(prof["max_m_runs"]))
        self.max_live = max_live
        self._lock, self._waiting = threading.Lock(), 0          # counted runs waiting for a slot: padding defers to them
        self.up, self.peak = 0, 0                                 # this level's sandboxes holding a live slot now, and at most
        self.overruns: list[dict] = []                            # runs that overran their fixed cycle: no gap left after them

    def rng(self, slot: int) -> np.random.Generator:
        return np.random.default_rng([self.prof["seed"], self.prof["block"], self.level, self.rep, slot, 0xD07])

    def _gap(self, plan) -> dict:
        k = f"{plan.option.value}/{plan.layout.value}/{plan.instance_id}"
        if k not in self.prof["gaps"]:
            raise DutyInputError(f"the profile has no gap for {k}")
        return self.prof["gaps"][k]

    def offset_s(self, plan, rng: np.random.Generator) -> float:
        g = self._gap(plan)
        return float(rng.uniform(0.0, g["single_total_s"] + g["gap_s"]))

    def gap_s(self, plan, rng: np.random.Generator, rec: dict | None) -> float:
        """The idle after a run that took `rec["total_s"]`: the cycle is held fixed at the baseline's total plus the jittered gap (mean: read /
        share), so a run that overran its baseline idles less (the lead, 2 Nov: the conservative choice; a slowdown on the host does not lower
        site_g's load). Never below 0; a run that leaves no gap, or whose time is unknown, is flagged in `overruns`. A cell loaded above its share
        never idles."""
        g = self._gap(plan)
        j = float(self.prof["jitter"])
        u = float(rng.uniform(1.0 - j, 1.0 + j))          # drawn every time, so the stream does not depend on the branch
        if g["loaded_above_share"]:
            return 0.0
        cycle = g["single_total_s"] + g["gap_s"] * u
        took = (rec or {}).get("total_s")
        left = cycle - float(took) if _num(took) else None
        if left is None or left <= 0:
            with self._lock:
                self.overruns.append({"run_key": (rec or {}).get("run_key", plan.key()), "total_s": took, "cycle_s": round(cycle, 3)})
            return 0.0
        return left

    @contextlib.contextmanager
    def guard(self, plan, wait: bool = True):
        """Holds a live slot (and an M slot for a mount) while the run is up; yields the seconds waited for them. With `wait=False` (padding)
        it takes them only if free, and yields None otherwise: padding must never hold a slot a counted run is waiting for."""
        t0 = time.monotonic()
        held = []
        if wait:
            with self._lock:
                self._waiting += 1
        try:
            try:
                for sem in ([self.mounts] if plan.option.value in MOUNT else []) + [self.live]:
                    if not wait and self._waiting:
                        break                # a counted run is waiting: a semaphore is not fair, so padding steps aside
                    if not sem.acquire(blocking=wait):
                        break
                    held.append(sem)
            finally:
                if wait:
                    with self._lock:
                        self._waiting -= 1
            ok = len(held) == (2 if plan.option.value in MOUNT else 1)
            if ok:
                with self._lock:
                    self.up += 1
                    self.peak = max(self.peak, self.up)
            try:
                yield {"live_wait_s": round(time.monotonic() - t0, 3), "mount": plan.option.value in MOUNT} if ok else None
            finally:
                if ok:
                    with self._lock:
                        self.up -= 1
        finally:
            for sem in reversed(held):
                sem.release()


class HostWatch:
    """The host beside a level's result (the lead, 2 Nov: the host limit is separate from site_g's, so it must be visible): MemAvailable and this
    level's sandboxes up, sampled every `period_s` while the level runs. A reading that fails is counted, never filled in."""

    def __init__(self, pace: Pacer, period_s: float = HOST_SAMPLE_S, mem=None):
        from . import metrics
        self.pace, self.period_s, self.mem = pace, period_s, mem or metrics.meminfo_available_gib
        self.samples: list[tuple[float | None, int]] = []
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _sample(self) -> None:
        try:
            m = float(self.mem())
        except Exception:  # noqa: BLE001 -- an unreadable meminfo is unknown, not a value
            m = None
        self.samples.append((m, self.pace.up))

    def _run(self) -> None:
        while True:
            self._sample()
            if self._stop.wait(self.period_s):
                return

    def __enter__(self) -> "HostWatch":
        self._t.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._t.join(30)
        self._sample()

    def summary(self) -> dict:
        mems = [m for m, _ in self.samples if m is not None]
        ups = [u for _, u in self.samples]
        return {"samples": len(self.samples), "period_s": self.period_s, "mem_unreadable": len(self.samples) - len(mems),
                "mem_available_gib_start": round(mems[0], 1) if mems else None, "mem_available_gib_min": round(min(mems), 1) if mems else None,
                "mem_available_gib_end": round(mems[-1], 1) if mems else None,
                "sandboxes_peak": self.pace.peak, "sandboxes_mean": round(statistics.fmean(ups), 2) if ups else None,
                "max_live": self.pace.max_live}


if __name__ == "__main__":
    raise SystemExit(main())
