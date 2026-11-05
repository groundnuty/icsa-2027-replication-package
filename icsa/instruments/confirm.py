"""Real-path confirmation of the instrument validation (#9; the science agent's ruling, 1 Nov 14:02Z).

The full validation matrix runs on the local path (`gates: "local-sim"`): a local Range
HTTP server for T, T-unpaginated and D, local files for M and M+. This confirmation set
runs the same scripted agent, with the same code, on ONE real pilot instance's data, along
two paths:
- real: on site_g through the real `icsa.sandbox` (the platform's fsspec client behind the T,
  T-unpaginated and D gates; M through the oneclient mount, default read-ahead);
- local: on the local copy of the same compressed files (`s1z/`, `s2z/` under ICSA_DATA,
  byte-identical to site_g, #3) through the local Range server and local files.
Both are labelled by the same call. Labels, analysed and loaded extents (as sets of units
of the required space), read days and read extents, listing summaries and what the listing
returned (count and names) must be IDENTICAL; any difference keeps the dossier's criterion 2 at
MISSING until explained and fixed. The sources under test are the ones real runs use (science,
#9, 1 Nov): the ledger and the requests.Session.send listing, never a simulated platform trace.

Cells, per option (T, T-unpaginated, D, M) x layout (S1, S2):
- one complete scenario (M: read through oneclient with its default read-ahead, so FUSE
  request splitting is exercised);
- one omitting scenario: a file-level skip in S1, a chunk (time step) skip in S2;
- one stress scenario;
- T and T-unpaginated in S1: a scenario that relies on the listing. On site_g the 1,000-entry
  cut is real: T must see 1,000 names, T-unpaginated all of them (15,340), on both paths;
- T, T-unpaginated and D in S1: a listing with the agent's own requests calls (the hook sees
  it) and one in a subprocess with urllib (it does not; the gate does: `listing_disagrees`).
M+ is not in the set: it needs #12's scripted replication (a design question on #9).

Usage (after the oracle's priority is lifted; needs docker and the federation):

    python -m icsa.instruments.confirm --work DIR --instance I01 --image <icsa-sandbox image id>

`confirm_summary.json` then feeds `validate --confirmation`, which writes
`real_confirmation: {"runs": n, "differences": [...], "none_fields": [...]}` and
`gates: "local-sim+real-confirmed"` only for the complete set on a pilot instance, run with the
same code, with no difference, no field left None on a real run, and every listing, read day and
label as the scenario says.
"""
from __future__ import annotations

import argparse
import contextlib
import threading
from concurrent.futures import ThreadPoolExecutor
import dataclasses
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np

from .. import grid
from ..instances import load as instance_load
from ..instances import required as instance_required
from ..paths import DATA_ROOT as ICSA_DATA
from . import validate as V
from .fullindex import load_full_index, manifest_digest
from .labeller import label_run
from .sandbox_dir import BOOT_MODULE, build_instruments_dir

CONFIRM_OPTIONS = ("T", "T-unpaginated", "D", "M")
REAL_S1_DIR, REAL_S1_FMT, REAL_S2_REL = "s1z", "sst_%Y%m%d.nc", "s2z/sst_s2.nc"   # #3, on site_g and locally
STRESS = "stress_print"


@dataclasses.dataclass(frozen=True)
class Cell:
    option: str
    layout: str
    scenario: str
    why: str

    @property
    def name(self) -> str:
        return f"{self.option}__{self.layout}__{self.scenario}"


def cells() -> list[Cell]:
    out = []
    for o in CONFIRM_OPTIONS:
        for lay in V.LAYOUTS:
            out.append(Cell(o, lay, "complete", "complete" + (
                "; read through oneclient with its default read-ahead (FUSE request splitting)" if o == "M" else "")))
            out.append(Cell(o, lay, "skip", "omitting: " + ("a file-level skip" if lay == "S1" else "a chunk skip")))
            out.append(Cell(o, lay, STRESS, "stress: partial use and a print of everything read"))
            if o in ("T", "T-unpaginated") and lay == "S1":
                out.append(Cell(o, lay, "listing_ls",
                                "relies on the listing: T sees 1,000 names, T-unpaginated 15,340"))
            if o in ("T", "T-unpaginated", "D") and lay == "S1":
                out.append(Cell(o, lay, "listing_paged", "a listing with the agent's own requests calls"))
                out.append(Cell(o, lay, "listing_subprocess",
                                "a listing in a subprocess: the gate sees it, the tracer does not"))
    return out


def scenario(name: str) -> tuple[int, V.Scenario]:
    for k, sc in enumerate(V.SCENARIOS):
        if sc.name == name:
            return k, sc
    raise KeyError(name)


# ---------------------------------------------------------------- the real world

def pilot_instance(instance_id: str) -> bool:
    """Whether the frozen manifest (#5) marks the instance as a pilot instance."""
    recs = [r for r in instance_load.load_instances()["instances"] if r["instance"]["instance_id"] == instance_id]
    return len(recs) == 1 and recs[0]["instance"].get("pilot") is True


def real_world(instance_id: str, root: Path = ICSA_DATA) -> V.Data:
    """A #5 pilot instance on the local copy of the real S1/S2 (byte-identical to site_g, #3).
    The layout index is built from the files every time (no cache to go stale)."""
    if not pilot_instance(instance_id):
        raise ValueError(f"{instance_id} is not a pilot instance of the frozen manifest: the ruling "
                         "confirms on one real pilot instance")
    root = Path(root)
    manifest = instance_load.load_instances()
    rec = next(r for r in manifest["instances"] if r["instance"]["instance_id"] == instance_id)
    inst = instance_load.instance(rec)
    sea = instance_load.load_sea_masks()[inst.region_id]
    days = np.arange(grid.NDAYS, dtype=np.int64)
    # The one full index: a run may read any file (a listing's first 1,000 names), and a file the
    # index does not hold would be an unidentified source.
    index = load_full_index(root)
    stamp = json.dumps({"root": str(root), "instance": instance_id, "manifests_sha256": manifest_digest(),
                        "files_indexed": len(index), "file_ids": len(index.ids),
                        "instances_sha256": V._sha256(instance_load.DATA / "instances.json")}, sort_keys=True)
    return V.Data(root, days, days, index, inst=inst, sea=sea, origin=(0, 0),
                  s1_dir=REAL_S1_DIR, s1_fmt=REAL_S1_FMT, s2_rel=REAL_S2_REL, stamp=stamp)


# ---------------------------------------------------------------- one cell, two paths

SandboxFactory = Callable[[str, str, str, Path], contextlib.AbstractContextManager]


def listed(stdout: str) -> dict | None:
    """What the scripted agent's listing returned (its LISTED line): count and names' hash."""
    for line in (stdout or "").splitlines():
        if line.startswith("LISTED "):
            parts = line.split()
            return {"count": int(parts[1]), "names_sha256": parts[2] if len(parts) > 2 else None}
    return None


def _row(cell: Cell, sc: V.Scenario, exp: dict, style: str, path: str) -> dict:
    return {"case": cell.name, "option": cell.option, "layout": cell.layout, "scenario": sc.name,
            "kind": sc.kind, "style": style, "true": exp["label"].value, "path": path}


IDENTITY = ("analysed", "loaded", "read", "read_beyond_days", "listing_summary", "listing_disagrees",
            "decoded_not_delivered", "delivered_not_decoded", "cross_check_source", "cross_check_unknown_ids",
            "none_fields")


def run_local(cell: Cell, data: V.Data, work: Path) -> dict:
    """The cell on the local path, exactly as the matrix runs it (validate.run_case)."""
    k, sc = scenario(cell.scenario)
    exp = V.expected(sc, cell.option, cell.layout, data)
    m = V.run_case(cell.option, cell.layout, k, sc, data, work / "local")
    wd = work / "local" / "runs" / cell.name
    row = _row(cell, sc, exp, m.get("style"), "local-sim")
    row.update(exit=m.get("exit"), wall_s=m.get("wall_s"))
    row["listed"] = listed((wd / "stdout.txt").read_text()) if (wd / "stdout.txt").is_file() else None
    if "label" not in m:
        row["error"] = m.get("error")
        return row
    row.update({f: m.get(f) for f in ("label", "reasons", "coverage", "notes", "analysed_exact") + IDENTITY})
    return row


def agent_code(cfg: dict) -> str:
    """The scripted agent with its configuration inline (a sandbox runs `python -`)."""
    src = Path(V.__file__).with_name("validate_agent.py").read_text()
    return ("import os\nos.environ['SCEN_CFG'] = " + repr(json.dumps(cfg)) + "\n") + src


def run_real(cell: Cell, data: V.Data, work: Path, factory: SandboxFactory,
             sandbox_paths: tuple[str, str] = ("/work/output", "/work/dl")) -> dict:
    """One cell through the factory's sandbox. sandbox_paths: the output and download
    directories inside it (icsa.sandbox: /work/output, which collect() copies out)."""
    k, sc = scenario(cell.scenario)
    exp = V.expected(sc, cell.option, cell.layout, data)
    style = "netCDF4" if sc.masked else V.style_of(cell.option, cell.layout, k)
    cfg = V.agent_cfg(cell.option, cell.layout, sc, data, exp, style, out=sandbox_paths[0],
                      download_dir=sandbox_paths[1], access="sandbox")
    cfg["provider_host"] = getattr(factory, "provider_host", None)     # for the agent's own listing calls
    code = agent_code(cfg)
    dest = work / "real" / cell.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    # one instruments directory per cell: cells run side by side, and a sandbox mounts its copy for its life
    instruments = build_instruments_dir(work / "real" / "instruments" / cell.name)[0]
    row = _row(cell, sc, exp, style, "real")
    t0 = time.time()
    with factory(f"confirm-{cell.name}", cell.option, cell.layout, instruments) as sbx:
        r = sbx.exec(code, V.RUN_TIMEOUT_S)
        sbx.collect(dest)
        meta = sbx.metadata() if hasattr(sbx, "metadata") else {}
    (dest / "stdout.txt").write_text(r.stdout or "")
    (dest / "stderr.txt").write_text(r.stderr or "")
    row.update(exit=r.exit_code, wall_s=round(time.time() - t0, 1), listed=listed(r.stdout),
               sandbox={k: meta.get(k) for k in ("image", "io_mode", "io_mode_observed", "io_mode_counts",
                                                  "mount_kind", "dataset_location", "host_aliases", "host") if k in meta})
    if r.exit_code != 0:
        row["error"] = (r.stderr or "")[-2000:]
        return row
    # the entry point as the campaign calls it; platform_dir: the directory collect() filled
    lab = label_run(cell.option, dest / "trace", dest / "output", data.index, V.required_of(data, exp),
                    platform_dir=dest, dir_sizes={data.s1_dir: int(len(data.s1_days))}, code_text=[code])
    an = lab.analysis
    want_a, got_a = V.expected_vs(exp, an.analysed, data, "used_days")
    row.update({"label": an.label.value, "reasons": an.reasons, "coverage": an.coverage, "notes": an.notes,
                "analysed_exact": bool(np.array_equal(want_a, got_a)), **V.identity_fields(lab, data)})
    return row


# Compared between the two paths. The cross-check's source differs by design (the local server's
# log, strace or perf log), so only its verdicts are compared, listing_disagrees among them.
COMPARED = ("exit", "label", "analysed", "loaded", "read", "read_beyond_days", "listed", "listing_summary",
            "listing_disagrees")


def compare(cell: Cell, local: dict, real: dict) -> list[dict]:
    """Every difference between the two paths: the label, the analysed, loaded and read extents
    (as unit sets of the required space), the read days beyond them, the listing summaries, what
    the listing returned, the exit."""
    diffs = [{"cell": cell.name, "field": k, "local": local.get(k), "real": real.get(k)}
             for k in COMPARED if local.get(k) != real.get(k)]
    for side, row in (("local", local), ("real", real)):
        if "label" not in row:
            diffs.append({"cell": cell.name, "field": "no_label", side: row.get("error") or f"exit {row.get('exit')}"})
    return diffs


def expectations(cell: Cell, data: V.Data, local: dict, real: dict, *, outside_view: bool = True) -> list[dict]:
    """What the scenario says each path must show, independently of the other path: the
    listing's count (T 1,000 = the client's page, T-unpaginated every name) and summary, the
    read days beyond the required set, whether the listing cross-check disagrees, and for every
    cell but the stress one the true label and the exact analysed extent. The real path must
    also have its outside view, with every file id known, and nothing decoded undelivered."""
    k, sc = scenario(cell.scenario)
    exp = V.expected(sc, cell.option, cell.layout, data)
    out = []

    def fail(side, field, want, got):
        out.append({"cell": cell.name, "path": side, "field": field, "expected": want, "got": got})
    for side, row in (("local", local), ("real", real)):
        if "label" not in row:
            continue
        want_listed = exp["listing"]["entries_listed"] if exp["listing"] else None
        if sc.listing == "subprocess":
            want_listed = len(data.s1_days) if cell.option == "T-unpaginated" else V.CFG["page"]
        if sc.listing != "construct" and cell.layout == "S1" and (row.get("listed") or {}).get("count") != want_listed:
            fail(side, "listed_count", want_listed, (row.get("listed") or {}).get("count"))
        if row.get("read_beyond_days") != exp["beyond_days"]:
            fail(side, "read_beyond_days", exp["beyond_days"], row.get("read_beyond_days"))
        got = (row.get("listing_summary") or {}).get(data.s1_dir)
        if exp["listing"] is None:
            if got is not None:
                fail(side, "listing_summary", None, got)
        elif got is None or any(got.get(f) != exp["listing"][f] for f in exp["listing"]):
            fail(side, "listing_summary", exp["listing"], got)
        if bool(row.get("listing_disagrees")) != exp["listing_disagrees"]:
            fail(side, "listing_disagrees", exp["listing_disagrees"], row.get("listing_disagrees"))
        if row.get("decoded_not_delivered"):
            fail(side, "decoded_not_delivered", False, True)
        if cell.scenario != STRESS:
            if row["label"] != exp["label"].value:
                fail(side, "label", exp["label"].value, row["label"])
            elif row["label"] != "unknown" and not row["analysed_exact"]:
                fail(side, "analysed_exact", True, False)
    if outside_view and "label" in real:
        if real.get("cross_check_source") not in ("gate", "oneclient_perf"):
            fail("real", "cross_check_source", "gate or oneclient_perf", real.get("cross_check_source"))
        if real.get("cross_check_unknown_ids"):
            fail("real", "cross_check_unknown_ids", 0, real.get("cross_check_unknown_ids"))
    return out


def confirm_cell(cell: Cell, data: V.Data, work: Path, factory: SandboxFactory, *, outside_view: bool = True,
                 **kw) -> dict:
    local = run_local(cell, data, work)
    real = run_real(cell, data, work, factory, **kw)
    diffs = compare(cell, local, real)
    none = [{"cell": cell.name, "field": f} for f in real.get("none_fields", ["read", "read_beyond_days"])]
    return {"cell": dataclasses.asdict(cell), "local": local, "real": real, "identical": not diffs,
            "differences": diffs, "none_fields": none,
            "expectation_failures": expectations(cell, data, local, real, outside_view=outside_view)}


# ---------------------------------------------------------------- the real sandbox

def real_sandbox_factory(image: str) -> SandboxFactory:
    """icsa.sandbox.Sandbox with the oracle's data configuration (fresh read-only tokens) and
    #9's instruments in the instrumentation slot. M runs oneclient as the campaign does: no
    forced I/O mode and no extra options, so its default read-ahead applies, and its performance
    log on: M's outside view (science, #9: on in every M run from the pilot)."""
    def factory(run_key: str, option: str, layout: str, instruments: Path):
        from ..harness import real_sandbox as rs
        from ..harness.config import load_config, required_token_ttl_s
        from ..harness.oracle_real import ORACLE_TIME_CAP_S, S2_BYTES, data_config
        from ..records import Layout, Option
        from ..sandbox import Sandbox
        # a leased slot user of the option, as the oracle's runs: released when the sandbox stops, quarantined
        # until its token expires if a failed start may have left a sandbox using it
        dc, lease = data_config(Option(option))
        valid_until = time.time() + required_token_ttl_s(ORACLE_TIME_CAP_S)
        try:
            from ..sandbox.route import configured_provider_port as _p
            if dc.io_mode is not None or list(dc.oneclient_extra_args) not in ([], ['-P', str(_p())]):
                raise RuntimeError("the confirmation runs oneclient with its defaults (no forced I/O mode or options)")
            if Option(option) in (Option.M, Option.M_PLUS):
                dc.oneclient_perf_log = True
            s1 = sum(p.stat().st_size for p in (ICSA_DATA / REAL_S1_DIR).iterdir())
            # the agent runs' own limits (config/harness.toml [sandbox_limits]: memory = allowance + tracer headroom,
            # cpus, pids, open files), through the harness's own builder, on the image pinned by its id
            cfg = rs.sandbox_config(image, image, sandbox_limits=load_config().sandbox_limits, s1_size=s1,
                                    s2_size=S2_BYTES, instruments=(instruments, BOOT_MODULE, rs.instruments_hash(instruments)))
            sbx = Sandbox.start(run_key, Option(option), Layout(layout), dc, cfg)
        except BaseException as e:
            rs.release_or_quarantine(lease, e, valid_until)
            raise
        return rs.bind_lease(sbx, lease, token_valid_until=valid_until)
    from ..harness.oracle_real import PROVIDER_HOST
    factory.provider_host = PROVIDER_HOST
    return factory


def run(instance_id: str, work: Path, factory: SandboxFactory, only: str | None = None,
        data: V.Data | None = None, image: str | None = None, jobs: int = 1, resume: bool = False, **kw) -> dict:
    """The cells matching `only`, `jobs` at a time. Each cell's result is kept on disk as it finishes
    (`cells/<name>.json`, with the stamp of the code, the confirmation code, the image and the data), so a stop
    loses only the cells in flight and slices run apart add up: the summary covers every cell on disk with this
    run's stamp. `resume` reuses a cell already done with the same stamp."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    data = data if data is not None else real_world(instance_id)
    code, confirm_code = V.code_stamp(), V.confirm_stamp()
    stamp = {"instance": instance_id, "instruments_sha256": code["instruments_sha256"],
             "confirm_sha256": confirm_code, "image": image, "data": data.stamp}
    cdir = work / "cells"
    cdir.mkdir(exist_ok=True)

    def saved(c: Cell) -> dict | None:
        f = cdir / f"{c.name}.json"
        if not f.is_file():
            return None
        got = json.loads(f.read_text())
        return got["result"] if got.get("stamp") == stamp else None

    changed = []

    def one(c: Cell) -> None:
        if resume and saved(c) is not None:
            return
        r = confirm_cell(c, data, work, factory, **kw)
        if (V.code_stamp()["instruments_sha256"], V.confirm_stamp()) != (code["instruments_sha256"], confirm_code):
            changed.append(c.name)         # not published: it may have run on other code
            return
        tmp = cdir / f"{c.name}.json.tmp"
        tmp.write_text(json.dumps({"stamp": stamp, "result": r}, default=str))
        tmp.replace(cdir / f"{c.name}.json")

    todo = [c for c in cells() if not only or only in c.name]
    stop = threading.Event()

    def guarded(c: Cell) -> None:
        if not stop.is_set():              # a stop starts no new cell; the ones running finish
            one(c)

    ex = ThreadPoolExecutor(max(1, int(jobs)))
    futures = []
    interrupted = False
    try:
        for c in todo:
            futures.append(ex.submit(guarded, c))
        for f in futures:
            f.result()
    except KeyboardInterrupt:
        interrupted = True
        stop.set()
        for f in futures:
            f.cancel()
    finally:
        ex.shutdown(wait=True)
    results = [r for r in (saved(c) for c in cells()) if r is not None]
    diffs = [d for r in results for d in r["differences"]]
    summary = {"instance": instance_id, "pilot": pilot_instance(instance_id), "image": image,
               "runs": len(results), "confirm_sha256": confirm_code,
               "complete_set": [r["cell"] for r in results] == [dataclasses.asdict(c) for c in cells()],
               "differences": diffs, "all_identical": bool(results) and not diffs,
               "none_fields": [n for r in results for n in r["none_fields"]],
               "expectation_failures": [e for r in results for e in r["expectation_failures"]],
               "cells": results, "data": data.stamp, **code}
    if changed or (V.code_stamp()["instruments_sha256"], V.confirm_stamp()) != (code["instruments_sha256"], confirm_code):
        summary["expectation_failures"].append({"field": "code", "expected": "unchanged during the run",
                                                "got": "changed", "cells_not_kept": changed})
    if interrupted:
        summary["interrupted"] = True
    (work / "confirm_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    if interrupted:
        raise KeyboardInterrupt
    return summary


def main(argv=None) -> int:
    from ..sandbox.termination import exit_on_sigterm
    exit_on_sigterm()     # a SIGTERM is an orderly exit: the sandboxes are stopped in order
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--instance", required=True, help="a #5 pilot instance id, e.g. I01")
    ap.add_argument("--image", required=True, help="the icsa-sandbox image (an immutable id) to run in")
    ap.add_argument("--only", default=None, help="substring filter on option__layout__scenario")
    ap.add_argument("--jobs", type=int, default=1, help="cells at a time (each a real sandbox and a local run)")
    ap.add_argument("--resume", action="store_true", help="reuse cells done with the same code, image and data")
    a = ap.parse_args(argv)
    s = run(a.instance, a.work, real_sandbox_factory(a.image), a.only, image=a.image, jobs=a.jobs, resume=a.resume)
    print(json.dumps({k: s[k] for k in ("instance", "runs", "complete_set", "all_identical", "differences",
                                        "none_fields", "expectation_failures")}, indent=1, default=str))
    return 0 if s["all_identical"] and s["complete_set"] and not s["expectation_failures"] and not s["none_fields"] else 1


if __name__ == "__main__":
    sys.exit(main())
