"""The real-data oracle (freeze condition, #8): the literal oracle agent through every enforced data path
(T, T-unpaginated, D, M) over both layouts (S1, S2), on the frozen 50 instances.

The oracle's analysis (`oracle_analysis.py`) is a literal reading of the prompt's Method; here only its data
access is real: each (option, layout) gets an access snippet that defines `load_region` by reading the data
through that option's path inside a real sandbox (`icsa.sandbox`: gate, store-and-forward, oneclient sidecar).
The result is scored against the ground truth with the frozen parser (`icsa.scoring.report`). Nothing here
adjusts the oracle to fit the reference: a mismatch is a finding.

Credentials: tokens are minted per run, read-only and scoped to the data space, short-lived, and never printed,
logged or recorded. The admin password is read at use time from ~/.secrets/icsa-2027/onedata.pass.
"""
from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import json
import os
import textwrap
import time
from pathlib import Path

import numpy as np

from icsa import grid
from icsa.extent import CellBox
from icsa.records import Instance, Layout, Option, Period

# the data space, tokens, image and sandbox configuration are shared with the campaign's factory
from .real_sandbox import (ADMIN_PASS_FILE, ONEZONE_HOST, PROVIDER_HOST, S1_DIR, S2_BYTES, S2_FILE, SPACE_ID,  # noqa: F401
                           SPACE_NAME, build_image)
from . import real_sandbox as _rs
from .config import required_token_ttl_s

ORACLE_TIME_CAP_S = 8 * 3600     # the oracle's own wall-time cap (not the agents' 240 min); its tokens are sized from it
OPTIONS = (Option.T, Option.T_UNPAGINATED, Option.D, Option.M)
LAYOUTS = (Layout.S1, Layout.S2)


def mint_token(*, oneclient: bool, ttl_s: int | None = None, pool=None, client=None, secrets_dir=None):
    """Read-only, space-scoped, short-lived token AS A LEASED SLOT USER (the oracle uses the same path as a run: a free
    slot user of option T for REST, M for oneclient), sized from the oracle's time cap. Returns (token, lease): the
    caller releases the lease. Fails loudly; never logs a value. There is no admin fallback."""
    from .slot_lease import SlotPool
    lease = (pool or _rs_pool()).acquire("M" if oneclient else "T")
    try:
        return _rs.mint_slot_token(lease, time_cap_s=ORACLE_TIME_CAP_S, ttl_s=ttl_s, client=client, secrets_dir=secrets_dir)[0], lease
    except BaseException:
        lease.release()
        raise


def _rs_pool():
    from .slot_lease import SlotPool
    return SlotPool()


def data_config(option: Option, *, pool=None, client=None, secrets_dir=None):
    """The DataConfig of one run, with a fresh token of a leased slot user of the option; returns (config, lease)."""
    lease = (pool or _rs_pool()).acquire(Option(option).value)
    try:
        return _rs.data_config(option, ORACLE_TIME_CAP_S, lease=lease, client=client, secrets_dir=secrets_dir)[0], lease
    except BaseException:
        lease.release()
        raise


IMAGE_TAG: str | None = None          # the immutable image id, set by main() after the build; never a shared tag


def sandbox_config():
    if IMAGE_TAG is None:
        raise RuntimeError("IMAGE_TAG is not set: the oracle runs only on its own pinned image")
    from .config import load_config as _lc
    return _rs.sandbox_config(IMAGE_TAG, IMAGE_TAG, sandbox_limits=_lc().sandbox_limits)


PILOT_IDS = ("I01", "I06", "I10", "I27", "I35", "I37", "I39", "I41", "I43", "I48")


PROTOCOL_TEXTS = None      # the prompt texts used by the run: loaded straight from the verified protocol commit


def texts_from_commit(c: str):
    import subprocess
    import tempfile
    from .prompt import load_prompt_texts
    repo = Path(__file__).resolve().parents[2]
    d = Path(tempfile.mkdtemp(prefix="protocol-"))
    for f in ("task-prompt.md", "access/T.md", "access/D.md", "access/M.md"):
        (d / f).parent.mkdir(parents=True, exist_ok=True)
        (d / f).write_bytes(subprocess.run(["git", "-C", str(repo), "show", f"{c}:protocol/{f}"], capture_output=True, check=True).stdout)
    return load_prompt_texts(d)


def protocol_check(new: str, old: str) -> dict:
    """Assert that the prompt rendered from protocol commit `new` is byte-identical to the one from `old`, for every
    option and layout, on a real instance; returns the evidence."""
    import subprocess
    import tempfile
    from .config import load_config
    from .prompt import load_prompt_texts, render_prompt
    repo = Path(__file__).resolve().parents[2]
    cfg = load_config()
    rec = instances_manifest()[3]
    inst = load_truth(rec).instance
    rendered = {}
    for c in (new, old):
        with tempfile.TemporaryDirectory() as d:
            for f in ("task-prompt.md", "access/T.md", "access/D.md", "access/M.md"):
                (Path(d) / f).parent.mkdir(parents=True, exist_ok=True)
                (Path(d) / f).write_bytes(subprocess.run(["git", "-C", str(repo), "show", f"{c}:protocol/{f}"],
                                                         capture_output=True, check=True).stdout)
            texts = load_prompt_texts(Path(d))
            rendered[c] = {(o.value, l.value): render_prompt(texts, inst, o, cfg.limits, cfg.slots_for(l))[1]
                           for o in OPTIONS for l in LAYOUTS}
    if rendered[new] != rendered[old]:
        diff = [k for k in rendered[new] if rendered[new][k] != rendered[old][k]]
        raise AssertionError(f"rendered prompt differs between protocol {new} and {old} for {diff}")
    import hashlib
    return {"new": new, "old": old, "identical": True,
            "sha256": {f"{o}/{l}": hashlib.sha256(t.encode()).hexdigest()[:16] for (o, l), t in rendered[new].items()}}


def sandbox_factory(run_key, option, layout, _unused=None):
    """The harness SandboxFactory over the real icsa.sandbox.Sandbox."""
    from icsa.sandbox import Sandbox
    dc, lease = data_config(option)        # a leased slot user of the option; released when the sandbox stops
    try:
        sbx = Sandbox.start(run_key, option, layout, dc, sandbox_config())
    except BaseException as e:
        _rs.release_or_quarantine(lease, e, time.time() + required_token_ttl_s(ORACLE_TIME_CAP_S))
        raise
    return _rs.bind_lease(sbx, lease, token_valid_until=time.time() + required_token_ttl_s(ORACLE_TIME_CAP_S))


# ---------------------------------------------------------------- access snippets
_COMMON = '''
import datetime, numpy as np, xarray as xr, os, shutil, time
LOC = os.environ["ICSA_DATASET_LOCATION"]
EPOCH = datetime.date(1982, 1, 1)

def _expand(date_ranges):
    out = []
    for a, b in date_ranges:
        out += [a + datetime.timedelta(days=i) for i in range((b - a).days + 1)]
    return sorted(set(out))

def _crop(ds, var, lat_min, lat_max, lon_min, lon_max):
    la = np.asarray(ds["latitude"].values, dtype=np.float64); lo = np.asarray(ds["longitude"].values, dtype=np.float64)
    jl = np.flatnonzero((la >= lat_min) & (la <= lat_max)); il = np.flatnonzero((lo >= lon_min) & (lo <= lon_max))
    return la[jl], lo[il], slice(int(jl[0]), int(jl[-1]) + 1), slice(int(il[0]), int(il[-1]) + 1)
'''

_S1_BODY = '''
from concurrent.futures import ThreadPoolExecutor
N_THREADS = 4                                   # the same for every option: the reads are latency-bound

def _day_path(d):
    return f"{LOC}/sst_{d:%Y%m%d}.nc"

def load_region(lat_min, lat_max, lon_min, lon_max, date_ranges):
    dates = _expand(date_ranges)
    with _open_day(_day_path(dates[0])) as ds:   # the crop of the first file serves all (one grid)
        lat, lon, sj, si = _crop(ds, "analysed_sst", lat_min, lat_max, lon_min, lon_max)
    def read(d):
        for attempt in range(5):                 # transient gateway errors (HTTP 502/timeouts) under load: retry, same for every option
            try:
                with _open_day(_day_path(d)) as ds:
                    return np.asarray(ds["analysed_sst"].isel(time=0, latitude=sj, longitude=si).values, dtype=np.float32)
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
    with ThreadPoolExecutor(N_THREADS) as ex:
        out = list(ex.map(read, dates))
    return np.stack(out), dates, lat, lon
'''

_S2_BODY = '''
def load_region(lat_min, lat_max, lon_min, lon_max, date_ranges):
    dates = _expand(date_ranges)
    with _open_s2() as ds:
        lat, lon, sj, si = _crop(ds, "analysed_sst", lat_min, lat_max, lon_min, lon_max)
        idx = [(d - EPOCH).days for d in dates]
        out = []
        a = 0
        while a < len(idx):                      # contiguous runs of days: one slice each
            b = a
            while b + 1 < len(idx) and idx[b + 1] == idx[b] + 1:
                b += 1
            out.append(np.asarray(ds["analysed_sst"].isel(time=slice(idx[a], idx[b] + 1), latitude=sj, longitude=si).values,
                                  dtype=np.float32))
            a = b + 1
    return np.concatenate(out, axis=0), dates, lat, lon
'''

_OPEN = {
    # T / T-unpaginated: the shipped fsspec client, range reads over the REST API
    "REST_T": '''
import fsspec, contextlib
fs = fsspec.filesystem("onedata")
@contextlib.contextmanager
def _open_day(path):
    with fs.open(path, "rb") as fh:
        with xr.open_dataset(fh, engine="h5netcdf", decode_times=False) as ds:
            yield ds
@contextlib.contextmanager
def _open_s2():
    with fs.open(LOC, "rb") as fh:
        with xr.open_dataset(fh, engine="h5netcdf", decode_times=False) as ds:
            yield ds
''',
    # D: whole-file download only (fs.get), then the local copy
    "REST_D": '''
import fsspec, contextlib, tempfile
fs = fsspec.filesystem("onedata")
os.makedirs("/work/dl", exist_ok=True)
@contextlib.contextmanager
def _open_day(path):
    local = "/work/dl/" + os.path.basename(path)
    fs.get(path, local)
    try:
        with xr.open_dataset(local, engine="h5netcdf", decode_times=False) as ds:
            yield ds
    finally:
        os.remove(local)
@contextlib.contextmanager
def _open_s2():
    local = "/work/dl/" + os.path.basename(LOC)
    fs.get(LOC, local)
    try:
        with xr.open_dataset(local, engine="h5netcdf", decode_times=False) as ds:
            yield ds
    finally:
        os.remove(local)
''',
    # M: files of the read-only mount, opened as local files
    "MOUNT": '''
import contextlib
@contextlib.contextmanager
def _open_day(path):
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as ds:
        yield ds
@contextlib.contextmanager
def _open_s2():
    with xr.open_dataset(LOC, engine="h5netcdf", decode_times=False) as ds:
        yield ds
''',
}


def real_snippets(option: Option, layout: Layout, _data_config: dict | None = None) -> str:
    """Access snippet that defines `load_region(lat_min, lat_max, lon_min, lon_max, date_ranges)` by reading the data
    through the option's enforced path (the sandbox gives the dataset location in ICSA_DATASET_LOCATION)."""
    kind = {Option.T: "REST_T", Option.T_UNPAGINATED: "REST_T", Option.D: "REST_D", Option.M: "MOUNT"}[option]
    body = _S1_BODY if layout is Layout.S1 else _S2_BODY
    return textwrap.dedent(_COMMON) + textwrap.dedent(_OPEN[kind]) + textwrap.dedent(body)


# ---------------------------------------------------------------- reference and scoring
@dataclasses.dataclass
class Truth:
    instance: Instance
    box: CellBox
    target_days: np.ndarray
    cell_mask: np.ndarray        # bool (days, h, w): the ground truth
    sea: np.ndarray              # bool (h, w)
    events: list                 # [(onset_day, end_day)] global day indices


def instances_manifest() -> list[dict]:
    p = Path(__file__).resolve().parents[2] / "data" / "instances" / "instances.json"
    return json.loads(p.read_text())["instances"]


def load_truth(rec: dict) -> Truth:
    from icsa.instances.load import instance as to_instance, load_sea_masks
    inst = to_instance(rec)
    i = rec["instance"]
    box = CellBox(i["lat0"], i["lat1"], i["lon0"], i["lon1"])
    days = np.arange(grid.day_index(inst.target.start), grid.day_index(inst.target.end) + 1, dtype=np.int64)
    import hashlib
    man = json.loads((Path(__file__).resolve().parents[2] / "data" / "instances" / "instances.json").read_text())["cell_masks"]
    cm_path = Path(man["file"])
    if hashlib.sha256(cm_path.read_bytes()).hexdigest() != man["sha256"]:
        raise RuntimeError(f"{cm_path} does not match the manifest's sha256: not a valid ground truth")
    z = np.load(cm_path)
    h, w = box.shape
    cm = np.unpackbits(z[i["instance_id"]], count=days.size * h * w).reshape(days.size, h, w).astype(bool)
    sea = load_sea_masks()[i["region_id"]]
    sea = sea[box.lat0:box.lat1, box.lon0:box.lon1] if sea.shape == (grid.NLAT, grid.NLON) else sea
    act = cm.any(axis=(1, 2))
    d = np.diff(np.concatenate(([0], act.astype(np.int8), [0])))
    ev = [(int(days[a]), int(days[b - 1])) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))]
    want = [(grid.day_index(dt.date.fromisoformat(a)), grid.day_index(dt.date.fromisoformat(b))) for a, b in rec["events"]]
    if ev != want:
        raise RuntimeError(f"{i['instance_id']}: events derived from the packed truth differ from the manifest's")
    return Truth(inst, box, days, cm, sea, ev)


def score(run_dir: Path, out_dir: str, t: Truth) -> dict:
    """The frozen parser, then the comparison with the ground truth. `exact` = identical masks and identical events."""
    from icsa.scoring import events as E, masks as M
    from icsa.scoring.report import parse_run_output
    from .report import NETCDF_LOCK
    with NETCDF_LOCK:                       # netCDF4 is not thread-safe
        out = parse_run_output(Path(run_dir) / out_dir, t.box, t.target_days)
    row = {"parse_valid": out.valid, "parse_reasons": out.reasons}
    if not out.valid:
        return {**row, "exact": False, "iou": None, "event_f1": None}
    m = out.mask
    agent_active = M.day_active(m)
    ev = E.active_runs(agent_active)
    ref_ev = E.active_runs(M.day_active(t.cell_mask))
    iou = 1.0 if (not m.any() and not t.cell_mask.any()) else float((m & t.cell_mask).sum() / (m | t.cell_mask).sum())
    f1 = None
    if ref_ev:
        mt = E.match_events([E.event_units(m, a, b) for a, b in ev], [E.event_units(t.cell_mask, a, b) for a, b in ref_ev])
        f1 = mt.f1
    agent_ev = [(int(t.target_days[a]), int(t.target_days[b - 1])) for a, b in ev]
    reported = sorted(out.report.events)          # report.json events as stated (global day indices)
    return {**row, "iou": iou, "event_f1": f1, "n_agent_events": len(agent_ev), "n_ref_events": len(t.events),
            "events_identical": agent_ev == t.events, "reported_events_identical": reported == sorted(t.events),
            "mask_identical": bool(np.array_equal(m, t.cell_mask)),
            "land_cell_days": int((m & ~t.sea).sum()),
            "exact": bool(np.array_equal(m, t.cell_mask) and agent_ev == t.events and reported == sorted(t.events))}


# ---------------------------------------------------------------- driver
def code_sha() -> str:
    import subprocess
    repo = Path(__file__).resolve().parents[2]
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    return git("rev-parse", "HEAD") + ("+dirty" if git("status", "--porcelain", "--untracked-files=no") else "")


def run_cell(rec: dict, option: Option, layout: Layout, out_root: Path, truth: Truth | None = None) -> dict:
    """One (instance, option, layout): a fresh real sandbox, the oracle through its path, scored."""
    import asyncio
    from icsa.records import RunId
    from .adapters import StubAdapter  # noqa: F401
    from .config import load_config
    from .oracle import oracle_adapter
    from .prompt import load_prompt_texts
    from .runner import RunContext, execute_run
    t0 = time.monotonic()
    truth = truth or load_truth(rec)
    inst = truth.instance
    cfg = load_config()
    cfg = dataclasses.replace(cfg, limits=dataclasses.replace(cfg.limits, time_cap_s=ORACLE_TIME_CAP_S))
    ctx = RunContext(cfg=cfg, texts=PROTOCOL_TEXTS or load_prompt_texts(), instances={inst.instance_id: inst}, sandbox_factory=sandbox_factory,
                     adapter_factory=lambda spec, seed, slot: oracle_adapter(inst, option, layout, {}, access_snippets=real_snippets, seed=seed))
    run = RunId(inst.instance_id, option, layout, "qwen", 1)
    run_dir = Path(out_root) / "runs" / run.key()
    import shutil
    shutil.rmtree(run_dir, ignore_errors=True)         # never score stale files from an earlier attempt
    base = {"instance": inst.instance_id, "kind": rec.get("kind"), "option": option.value, "layout": layout.value}
    try:
        r = asyncio.run(execute_run(run, 1, run_dir, None, ctx))
    except Exception as e:  # noqa: BLE001 -- infra failure: recorded, never scored as a pass
        return {**base, "ending": f"INFRA:{type(e).__name__}", "detail": str(e)[:300], "exact": False, "iou": None,
                "wall_s": round(time.monotonic() - t0, 1)}
    sc = score(run_dir, r.output_dir, truth)
    sc["exact"] = bool(sc["exact"] and r.extras.get("finished") and r.termination.value == "report")
    gt = (r.sandbox or {}).get("gate_transfers") or {}
    return {**base, "image_id": (r.sandbox or {}).get("image_id"), "image": (r.sandbox or {}).get("image"),
            "oneclient_tls": (r.sandbox or {}).get("oneclient_tls"), "ending": r.extras.get("ending"), "finished": r.extras.get("finished"), "wall_s": round(r.wall_time_s, 1),
            "bytes_to_sandbox": gt.get("bytes_to_sandbox"), "upstream_bytes": gt.get("upstream_bytes"),
            "whole_file_transfers": gt.get("whole_file_transfers"), "n_exec": len(json.loads((run_dir / r.code_cells_path).read_text())),
            "outputs_reason": r.extras.get("outputs_reason"), **sc}


def main(argv=None) -> int:
    import argparse
    import concurrent.futures as cf

    from icsa.sandbox.termination import exit_on_sigterm
    exit_on_sigterm()     # a SIGTERM is an orderly exit: the sandboxes are stopped in order
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="all", help="comma list of instance ids, or all")
    ap.add_argument("--set", default="all", choices=["all", "pre"],
                    help="pre = the pre-registration set: all 50 instances in S2 plus the 10 pilot instances in S1, through all four options")
    ap.add_argument("--protocol", default="a1b4c94:2aaa857", help="NEW:OLD protocol commits whose rendered prompts must be byte-identical")
    ap.add_argument("--cells", default="all", help="comma list of OPTION:LAYOUT (e.g. T:S1,M:S2), or all")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    recs = instances_manifest()
    if a.instances != "all":
        want = set(a.instances.split(","))
        recs = [r for r in recs if r["instance"]["instance_id"] in want]
    if a.instances != "all" and len(recs) != len(set(a.instances.split(","))):
        raise SystemExit("unknown instance id in --instances")
    cells = [(o, l) for o in OPTIONS for l in LAYOUTS]
    if a.cells != "all":
        ol = {o.value: o for o in OPTIONS}
        cells = [(ol[c.split(":")[0]], Layout(c.split(":")[1])) for c in a.cells.split(",")]
    if len(set(cells)) != len(cells):
        raise SystemExit("duplicate cells in --cells")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = Path(a.out or Path(__file__).resolve().parents[2] / "results" / "oracle" / stamp)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: a counted run needs a fresh result directory")
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(r, o, l) for r in recs for (o, l) in cells]
    if a.set == "pre":
        jobs = [(r, o, l) for (r, o, l) in jobs if l is Layout.S2 or r["instance"]["instance_id"] in PILOT_IDS]
    if not jobs:
        raise SystemExit("no jobs selected")
    sha = code_sha()
    if sha.endswith("+dirty") and not os.environ.get("ICSA_ORACLE_ALLOW_DIRTY"):
        raise SystemExit("refusing to run the counted oracle on a dirty checkout: commit first")
    global IMAGE_TAG
    IMAGE_TAG = build_image(sha.split("+")[0])
    pn, po = a.protocol.split(":")
    pcheck = protocol_check(pn, po)
    global PROTOCOL_TEXTS
    PROTOCOL_TEXTS = texts_from_commit(pn)             # the run renders prompts from this commit, not from the checkout
    import subprocess
    repo = Path(__file__).resolve().parents[2]
    snap = subprocess.run(["git", "-C", str(repo), "rev-parse", pn], capture_output=True, text=True, check=True).stdout.strip()
    for f in ("task-prompt.md", "access/T.md", "access/D.md", "access/M.md"):     # the checkout's protocol/ is that commit's
        if (repo / "protocol" / f).read_bytes() != subprocess.run(["git", "-C", str(repo), "show", f"{pn}:protocol/{f}"],
                                                                  capture_output=True, check=True).stdout:
            raise SystemExit(f"protocol/{f} in this checkout differs from {pn}")
    (out / "meta.json").write_text(json.dumps({"code_sha": sha, "started_utc": stamp, "n_jobs": len(jobs),
                                                "concurrency": a.concurrency, "protocol_dir": "protocol",
                                                "protocol_commit": snap, "protocol_check": pcheck, "image_tag": IMAGE_TAG,
                                                "set": a.set}, indent=1))
    rows, truths = [], {}

    def one(job):
        rec, o, l = job
        iid = rec["instance"]["instance_id"]
        row = run_cell(rec, o, l, out, truths.get(iid))
        with open(out / "rows.jsonl", "a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(f"{iid} {o.value:13s} {l.value} exact={row.get('exact')} iou={row.get('iou')} ending={row.get('ending')} {row.get('wall_s')}s", flush=True)
        return row
    for r in recs:                                   # ground truths are cheap (packed masks): load once
        truths[r["instance"]["instance_id"]] = load_truth(r)
    with cf.ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        rows = list(ex.map(one, jobs))
    import csv
    cols = ["instance", "option", "layout", "exact", "iou", "event_f1", "n_agent_events", "n_ref_events", "mask_identical",
            "events_identical", "wall_s", "bytes_to_sandbox", "upstream_bytes", "ending", "image_id", "oneclient_tls"]
    with open(out / "table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["instance"], r["option"], r["layout"])))
    ids = {r.get("image_id") for r in rows}
    (out / "image_ids.json").write_text(json.dumps(sorted(map(str, ids))))
    if ids != {IMAGE_TAG}:
        print(f"IMAGE EVIDENCE FAILED: pinned {IMAGE_TAG}, recorded {sorted(map(str, ids))}")
        return 3
    bad = [r for r in rows if not r.get("exact")]
    print(f"{len(rows) - len(bad)}/{len(rows)} cells exact; {len(bad)} not")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
