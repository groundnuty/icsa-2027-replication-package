"""The live check's probe (protocol amendment 25(e); the judgement of its lines is icsa/campaign/livecheck.py, which the campaign runs every 30 minutes).

    python -m icsa.scripted live-probe --shape T|M --out DIR --baseline DIR.. [--instance I35] [--untraced] [--probe-files N]

One fixed scripted S1 read through the batch's own `run_one` (a real sandbox, `plans`' S1 cell of that option, one fixed instance), printing ONE JSON line:

    {"shape", "read_s", "single_s", "ratio", "state": "ok"|"unknown", "why", "run_key", ...}

`read_s` is the run's read phase measured as the curve measures it (`curve.read_phase_s`), `single_s` that cell's median read phase over the clean single runs in
`--baseline` for the same instance, formed as the curve forms it (`curve.single_read_phases`, from the enforced runs of the same tracing state, refusing a baseline
that holds runs under contention), and `ratio` is `read_s / single_s`. The probe does not judge: whether a ratio is a breach is the campaign's (limit 1.25).
A run that fails or is not clean, a record with no read phase, a missing baseline, a baseline from another image, a missing slot user: `unknown`, never a pass
or a breach. When there is no baseline, no sandbox is started at all.

Records go under `--out/<UTC stamp>-<shape>/` (the run in its `runs/`, a manifest) and one line per probe is appended to `--out/live_probes.jsonl`: never into a
curve's, a baseline's or the campaign's directory. The run's tag is `live-<shape>-<stamp>`, so no curve's or baseline's key can be this one's.

The probe's slot user is its own. `ICSA_SLOT_KEYS` must name exactly one key, and the slot map must give that key to this shape's option (the campaign passes
`live_check_slot_keys[shape]`); the token source is the slot pool's, with a bounded wait, never the admin token.

HOW LONG IT TAKES. This is not a minute. An S1 cell reads every required daily file of the instance, 1,544 of them (1,452 baseline days and 92 target days), one
after the other. From the per-file times of 1 Nov (T 0.41 s with the fixed gate, results/scripted/gate_ab2.jsonl; M 0.25 s, results/m-throughput/NOTES.md) that is
about 630 s for T and 390 to 520 s for M, plus a sandbox start and stop of about 30 s; the 1 Nov smoke (labelled non-timing: old gate, a loaded host) read T in 1,266 s
and M in 1,030 s. The single-run baselines say what they are: `single_s`. So each probe holds one reader on the provider for that long, every 30 minutes: 23 to 37 % of
one sandbox's duty per shape, not the 3.3 % of a one-minute read. This probe is the full cell on purpose; a one-minute S1 read would be a subset of the days, a different
probe with a baseline of its own, and that is science's to decide.

`--probe-files N` (the launch's `live_check_probe_files[shape]`; none = the whole cell, which is this docstring's default): read only the FIRST N files of the cell's fixed order
(`runner.probe_days`: the baseline days, then the target days, each ascending; the same files for an instance on every run, with no seed in it), timed as for the whole cell
(`read_done - first_compute`), with nothing computed, written or scored: a probe is not a run. The record carries `extra.probe_files = N`. Its ratio is taken ONLY against baseline
records of the same shape, instance, tracing state and image that carry the same count (`baseline --probe-files`, into a directory of its own); a record without the field is a whole
cell, so a probe with no count still reads today's baselines and a probe of N never reads them. Any other combination is unknown, and says which counts the baselines do hold.

The exec is bounded: `EXEC_FACTOR` times `single_s` (at least `EXEC_MIN_S`, at most `EXEC_MAX_S`), so the probe ends by itself, with its sandbox stopped, before the
campaign's own timeout (which can only kill the process). A read that outruns it is a run that did not finish: unknown.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from ..records import Layout, Option
from . import curve as Cv
from . import plans
from .runner import Plan

SHAPES = {"T": Option.T, "M": Option.M}
DEFAULT_INSTANCE = plans.BASELINE_INSTANCES[0]
LEASE_WAIT_S = 300.0                 # a slot user held by something else for longer than this: the probe is unknown, it does not queue behind it
EXEC_FACTOR, EXEC_MIN_S, EXEC_MAX_S = 6.0, 600.0, 3600.0
LOG = "live_probes.jsonl"


def add_arguments(s: argparse.ArgumentParser) -> None:
    s.add_argument("--shape", required=True, choices=sorted(SHAPES), help="T or M: the S1 cell of that option")
    s.add_argument("--baseline", nargs="+", required=True, help="the results directories holding the single runs (as `curve --baseline`)")
    s.add_argument("--instance", default=DEFAULT_INSTANCE, help="the one fixed instance (it must have a baseline run in --baseline)")
    s.add_argument("--untraced", action="store_true", help="plain runs; the baseline must then be untraced too (the curve's flag)")
    s.add_argument("--probe-files", type=int, default=None, help="read only the first N files of the cell's fixed order (compared with baseline records of N files only); default: the whole cell")


# ---- pure: the plan, the baseline, the line ---------------------------------------------------------------------------------
def probe_plan(shape: str, instance: str, stamp: str) -> Plan:
    return Plan(instance, SHAPES[shape], Layout.S1, tag=f"live-{shape}-{stamp}")


ANY_COUNT = object()                 # `baseline_runs(files=ANY_COUNT)`: whatever the records' counts are (to say which ones the baselines hold)


def files_of(r: dict) -> Any:
    """The count of files a record read: the field `extra.probe_files` when it is a whole number, None (a whole cell) when the record has no such field. A field that is there but is
    not a whole number (a string, a boolean) is neither: it matches no count, so such a record is read as nothing."""
    v = (r.get("extra") or {}).get("probe_files")
    if v is None:
        return None
    return v if type(v) is int else ("?", repr(v))


def baseline_runs(dirs, traced: bool, files: Any = None) -> list[dict]:
    """The runs the single-run times rest on, selected as `cmd_curve` selects them: not an infrastructure failure, the enforced variant, in this tracing state, and of this count of
    files (`files`: None = a whole cell, the records without the field; N = records that carry exactly N; `ANY_COUNT` = all of them)."""
    from .summarize import load_runs
    return [r for d in dirs for r in load_runs(d) if not r.get("infrastructure") and not (r.get("extra") or {}).get("live_probe")     # a probe's own record is never a baseline
            and (r.get("extra") or {}).get("variant", "enforced") == "enforced" and bool((r.get("extra") or {}).get("traced")) is traced
            and (files is ANY_COUNT or files_of(r) == files)]


def contended(base: list[dict]) -> list[str]:
    """Baseline runs taken under contention (a pool or a curve level) would inflate the single-run time: the curve refuses them, so does the probe."""
    return sorted(r.get("run_key", "?") for r in base if ((r.get("extra") or {}).get("pool_workers") or 1) > 1 or "level" in (r.get("extra") or {}))


def baseline_image_ids(dirs) -> set[str]:
    """The image ids the baselines' manifests record. Empty when none says."""
    out: set[str] = set()
    for d in dirs:
        for f in sorted(Path(d).glob("MANIFEST_baseline*.json")):
            try:
                v = json.loads(f.read_text()).get("image_id")
            except (OSError, ValueError, AttributeError):
                continue
            if isinstance(v, str) and v:
                out.add(v)
    return out


def baseline_image_of(d) -> str | None:
    """The one image id the manifests of directory `d` name (the first run's and any resume's), or None when none names one or they name more than one. The records carry no
    image, only their directory's manifests do, so a directory that cannot be shown to be one image's is not any image's."""
    ids = baseline_image_ids([d])
    return next(iter(ids)) if len(ids) == 1 else None


def exec_timeout_s(single_s: float) -> float:
    return min(EXEC_MAX_S, max(EXEC_MIN_S, EXEC_FACTOR * single_s))


def _first_error(rec: dict) -> str:
    errs = rec.get("errors") or []
    return str(errs[0])[:200] if errs else "no error recorded"


def unknown_line(shape: str, why: str, **kw: Any) -> dict[str, Any]:
    return {"shape": shape, "read_s": kw.pop("read_s", None), "single_s": kw.pop("single_s", None), "ratio": None, "state": "unknown", "why": why[:400],
            "run_key": kw.pop("run_key", None), **kw}


def line_from(shape: str, rec: dict, single_s: float | None, **kw: Any) -> dict[str, Any]:
    """The printed line of a finished probe run. Anything that is not a clean run with a read phase and a baseline is unknown."""
    rk = rec.get("run_key")
    rs = Cv.read_phase_s(rec)
    if single_s is None or not single_s > 0:
        return unknown_line(shape, "no usable single-run read time in the baselines for this cell and instance", read_s=rs, run_key=rk, **kw)
    if not Cv.clean(rec):
        why = "the probe run was not clean" + ("" if rec.get("ok") is True else f": {_first_error(rec)}")
        return unknown_line(shape, why, read_s=None if rs is None else round(rs, 3), single_s=round(single_s, 3), run_key=rk, **kw)
    if rs is None:
        return unknown_line(shape, "the probe run's record has no read phase (a stamp is missing)", single_s=round(single_s, 3), run_key=rk, **kw)
    return {"shape": shape, "read_s": round(rs, 3), "single_s": round(single_s, 3), "ratio": round(rs / single_s, 4), "state": "ok", "why": "", "run_key": rk, **kw}


# ---- one probe (the runner is the real sandbox run, or a test's stand-in) ----------------------------------------------------
Runner = Callable[[Plan, Path, float], dict]


def counts_held(baselines, traced: bool, opt: str, instance: str) -> list[str]:
    """Which counts of files the baselines hold clean read phases for, for this cell: "whole" or the number. Said when the probe's own count has none."""
    held = {files_of(r) for r in baseline_runs(baselines, traced, ANY_COUNT) if r.get("option") == opt and r.get("layout") == "S1" and r.get("instance_id") == instance
            and Cv.clean(r) and Cv.read_phase_s(r) is not None}
    return sorted("whole" if h is None else str(h) for h in held)


def probe(shape: str, *, instance: str, out: Path, baselines, traced: bool, runner: Runner, image_id: str | None = None, stamp: str | None = None,
          seed: int | None = None, files: int | None = None) -> dict[str, Any]:
    """One probe: look up the single-run time, run the cell once, form the line, append it to `live_probes.jsonl`. Never raises for a run that went wrong.
    `files`: read only that many files (see the module text); the single-run time is then taken from baseline records of that count alone, and from their directories' image id.
    Only the directories whose manifests name the probe's image (and no other) feed the single-run time; a set with none of the probe's image for the cell is unknown."""
    stamp = stamp or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    meta = {"instance": instance, "traced": traced, "stamp": stamp, "seed": seed, **({} if files is None else {"probe_files": files})}
    out = Path(out)
    line: dict[str, Any]
    base = baseline_runs(baselines, traced, files)
    opt = SHAPES[shape].value
    bad = contended(base)
    single = Cv.single_read_phases(base).get((opt, "S1", instance))
    # the image the baselines were made on is the one their manifests name: for a count, those of the directories that hold records of that count
    ids = baseline_image_ids(baselines if files is None else [d for d in baselines if baseline_runs([d], traced, files)])
    # the single-run figure rests on the directories made on the probe's own image alone: baselines of two images are not pooled (a median across them is neither's)
    mine = baseline_runs([d for d in baselines if image_id and baseline_image_of(d) == image_id], traced, files)
    single_mine = Cv.single_read_phases(mine).get((opt, "S1", instance))
    if bad:
        line = unknown_line(shape, f"the baseline holds runs under contention, which would inflate the single-run time: {bad[:3]}", **meta)
    elif single is None:
        others = counts_held(baselines, traced, opt, instance)
        why = f"no clean {'traced' if traced else 'untraced'} single run with a read phase for {opt}/S1/{instance} in the baselines"
        if files is not None or others:
            why = (f"no clean {'traced' if traced else 'untraced'} single run with a read phase of {'a whole cell' if files is None else f'{files} files'} for {opt}/S1/{instance} in the baselines"
                   + (f" (they hold {others} for it: a ratio is never taken across counts)" if others else ""))
        line = unknown_line(shape, why, **meta)
    elif not image_id or not ids:      # an image that cannot be told is not "the same image": the ratio would compare what nobody checked
        line = unknown_line(shape, "the probe's image id" + (" is unknown" if not image_id else " is known but no MANIFEST_baseline*.json of --baseline records an image id")
                            + ": the ratio would compare two images that were not shown to be one", **meta)
    elif image_id not in ids:
        line = unknown_line(shape, f"the probe's image {image_id[:19]} is not the baselines' ({sorted(i[:19] for i in ids)}): the ratio would compare two images", **meta)
    elif single_mine is None:
        line = unknown_line(shape, f"no clean {'traced' if traced else 'untraced'} single run with a read phase for {opt}/S1/{instance} in the baselines made on the probe's image {image_id[:19]} "
                                   f"(the baselines' images: {sorted(i[:19] for i in ids)}): a ratio is never taken across images", **meta)
    else:
        single = single_mine
        plan = probe_plan(shape, instance, stamp)
        try:
            rec = runner(plan, out / f"{stamp}-{shape}" / "runs", exec_timeout_s(single))
            read = (rec.get("script") or {}).get("days_read")
            if files_of(rec) != files or (files is not None and read != files):      # the count asked for is the count on record, and the count the script says it read
                line = unknown_line(shape, f"the probe's record carries probe_files {files_of(rec)!r} and the script read {read!r} files, not the {files if files is not None else 'whole cell'} asked for: "
                                    "the ratio would compare two counts", single_s=round(single, 3), run_key=rec.get("run_key"), **meta)
            else:
                line = line_from(shape, rec, single, **meta, image_id=image_id, baseline_image_checked=bool(ids), wall_s=rec.get("wall_s"), total_s=rec.get("total_s"))
        except Exception as e:  # noqa: BLE001 - a probe that could not run is unknown, and says why
            line = unknown_line(shape, f"{type(e).__name__}: {e}", single_s=round(single, 3), run_key=plan.key(), **meta)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / LOG, "a") as f:
        f.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **line}) + "\n")
    return line


# ---- the real thing ---------------------------------------------------------------------------------------------------------
def require_own_slot_user(shape: str, pool_factory: Callable[[], Any] | None = None) -> str:
    """ICSA_SLOT_KEYS names exactly one key, and the slot map gives it to this shape's option: the probe's own user, shared with no run. Returns the key."""
    from ..harness import slot_lease
    keys = slot_lease.allowed_keys()
    if keys is None or len(keys) != 1:
        raise SystemExit(f"live-probe: ICSA_SLOT_KEYS must name the probe's one slot user (the campaign passes live_check_slot_keys[{shape!r}]), not {sorted(keys) if keys else keys}")
    have = [k for k, _ in (pool_factory or slot_lease.SlotPool)().slots_of(SHAPES[shape].value)]
    if have != sorted(keys):
        raise SystemExit(f"live-probe: slot key {sorted(keys)} is not a {shape} slot user in the slot map ({have}); it must be created first")
    return next(iter(keys))


def cmd_live_probe(args, M=None) -> None:
    """`M` is icsa.scripted.__main__ (its helpers: the manifest, the common inputs). Prints the probe's one line; exit 0 for ok and for unknown."""
    from .. import codestamp
    from . import federation as F
    from . import metrics, tokens
    from .reference import load_or_build_reference
    from .runner import run_one
    from .slot_tokens import SlotTokens
    shape = args.shape
    instance = plans.parse_instances(args.instance)
    if len(instance) != 1:
        raise SystemExit("live-probe: --instance names one instance")
    instance = instance[0]
    traced = not args.untraced
    files = getattr(args, "probe_files", None)
    if files is not None and files < 1:
        raise SystemExit(f"live-probe: --probe-files {files}: a whole number of at least 1, or leave it out for the whole cell")
    require_own_slot_user(shape)
    tokens.set_source(SlotTokens(timeout_s=LEASE_WAIT_S))        # the probe's slot user, with a bounded wait; whatever ICSA_TOKEN_SOURCE says, never admin
    codestamp.require_known("live-probe", Path(__file__).resolve().parents[2])
    if metrics.meminfo_available_gib() < M.MIN_MEM_PER_RUN_GIB + 5:
        print(json.dumps(unknown_line(shape, "host MemAvailable too low to start the probe's sandbox")), flush=True)
        return
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = Path(args.out)
    pdir = out / f"{stamp}-{shape}"
    man, recs, truth = M._common(args)
    m = M._manifest(pdir, f"live_probe_{shape}", seed=args.seed, shape=shape, instance=instance, traced=traced, baseline=[str(d) for d in args.baseline],
                    **({} if files is None else {"probe_files": files}))
    refs = _reference(out, args.baseline, recs[instance], load_or_build_reference)
    slot, tracer = F.traced_slot() if traced else (None, None)
    cfg = F.sandbox_config(F.MAIN, m["image"], instruments=slot)

    def runner(plan: Plan, runs_dir: Path, timeout_s: float) -> dict:
        return run_one(plan, recs[instance], truth, lambda o=plan.option: F.data_config(F.MAIN, o), cfg, runs_dir, expected_sst=refs[instance],
                       timeout_s=timeout_s, extra={"live_probe": True, "shape": shape}, read_files=files)
    line = probe(shape, instance=instance, out=out, baselines=args.baseline, traced=traced, runner=runner, image_id=m.get("image_id"), stamp=stamp, seed=args.seed, files=files)
    print(json.dumps(line), flush=True)


def _reference(out: Path, baselines, rec: dict, build: Callable) -> dict[str, str]:
    """The instance's SST reference hash: from a baseline directory that has it (it was built there from the verified local copy), else built into `out` once."""
    iid = rec["instance"]["instance_id"]
    for d in baselines:
        try:
            have = json.loads((Path(d) / "reference_sst_sha256.json").read_text())
        except (OSError, ValueError):
            continue
        if isinstance(have, dict) and isinstance(have.get(iid), str):
            return {iid: have[iid]}
    return build(out, [rec])
