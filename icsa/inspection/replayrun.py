"""Running the dependence test by replay (#76): the sandbox side of `replaycheck`. Heavy imports are lazy; the logic is in replaycheck.

Everything about the host comes in as arguments: the data (`--data-root`, or `--s1-dir`/`--s2-file`/`--ids-json`), the scratch, the
harness config (sandbox limits), the concurrency and the caps. Nothing reads site_g or site_f: the data configuration of every arm is
built by `krun.local_sim_data_config` over a local mock and checked by `assert_local_data_config` before a sandbox starts.

One arm = one replay of a run's recorded cells through the real `execute_run` and the real `Sandbox`, untraced, with a `StubAdapter`
as the model. An arm that ends on a cap, a crash, with cells that fail differently from the control, or without a valid mask is
recorded as such and is no evidence (`not_tested`). A run whose control arm does not reproduce its own saved mask exactly is
`not_replayable` and no perturbed arm starts.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

import numpy as np

from . import replaycheck as RC

MODEL = "qwen"            # the RunId's model key, as krun uses: the stub model; no name reaches a result
SKIP_ARM_KEYS = ("mask",)


# ---------------------------------------------------------------------------------------------------------- the host
@dataclasses.dataclass
class Host:
    s1_dir: Path
    s2_file: Path
    ids_json: Path
    scratch: Path
    out: Path
    cfg: object
    spec: RC.PerturbSpec
    group_mode: str = "reduced"
    n_years: int = 2
    image_override: str | None = None
    arm_cap_s: float = 3600.0
    jobs: int = 1
    max_d: int = 1
    max_s2_copies: int = 1
    max_sandboxes: int = 0                   # sandboxes at once on this host; 0: as many as --jobs
    min_free_bytes: int = 25 * 2**30
    s2_cache: Path | None = None
    s1_bytes: int = 0
    s2_bytes: int = 0
    explicit_groups: list | None = None
    work_root: Path | None = None            # where the sandboxes' own disks live; None: the sandbox config's default

    @classmethod
    def from_args(cls, a) -> "Host":
        from icsa.harness.config import load_config
        root = Path(a.data_root)
        h = cls(s1_dir=Path(a.s1_dir or root / "s1z"), s2_file=Path(a.s2_file or root / "s2z" / "sst_s2.nc"),
                ids_json=Path(a.ids_json or root / "layout" / "ids.json"), scratch=Path(a.scratch), out=Path(a.out),
                cfg=load_config(a.config_dir), spec=RC.PerturbSpec(delta_k=a.delta_k, space_frac=a.space_frac, seed=_seed_of(a.out)),
                group_mode=a.groups if a.groups in ("reduced", "all", "plan") else "explicit",
                n_years=a.baseline_years, image_override=a.image_id, arm_cap_s=a.arm_cap_s, jobs=a.jobs, max_d=a.max_d, max_sandboxes=a.max_sandboxes,
                max_s2_copies=a.max_s2_copies, min_free_bytes=int(a.min_free_gb * 2**30),
                s2_cache=Path(a.s2_cache) if a.s2_cache else None)
        h.work_root = Path(a.sandbox_work_root) if a.sandbox_work_root else None
        h.explicit_groups = [x for x in a.groups.split(",") if x] if h.group_mode == "explicit" else None   # validated by select_groups
        for p in (h.s1_dir, h.s2_file, h.ids_json):
            if not p.exists():
                raise FileNotFoundError(f"{p} does not exist: pass --data-root (or --s1-dir/--s2-file/--ids-json)")
        h.s1_bytes = sum(p.stat().st_size for p in h.s1_dir.iterdir())
        h.s2_bytes = h.s2_file.stat().st_size
        return h


def _seed_of(out) -> str:
    return str(json.loads((Path(out) / "plan.json").read_text())["seed"])


def sandbox_disk_bytes(host: "Host", option) -> int:
    """The work disk one sandbox of this option takes from the host's root (D: 1.2 x S2; the others: the small disk). Measured on .16:
    a D sandbox on S2 took about 4.3 GB."""
    from icsa.harness import real_sandbox as rs
    from icsa.records import Option
    scfg = rs.sandbox_config("-", "-", sandbox_limits=host.cfg.sandbox_limits, s1_size=host.s1_bytes, s2_size=host.s2_bytes)
    return int(scfg.limits.disk_bytes(Option(option)))


class Limits:
    """Concurrency caps shared by the worker threads: option D arms, and full S2 copies on the scratch."""

    def __init__(self, host: Host):
        self.d = threading.Semaphore(host.max_d)
        self.sandboxes = threading.Semaphore(host.max_sandboxes or host.jobs)
        self.s2 = threading.Semaphore(host.max_s2_copies)
        self.host = host
        self._base_lock, self._base = threading.Lock(), None

    def base_root(self) -> Path:
        with self._base_lock:                  # two threads linking the same tree would race on the same names
            if self._base is None:
                self._base = base_tree(self.host)
            return self._base

    def wait_for_room(self, need_bytes: int, timeout_s: float = 900.0, poll_s: float = 15.0) -> bool:
        """True once the scratch's filesystem has `need_bytes` plus the floor free; False after `timeout_s`."""
        from icsa.sandbox.config import SandboxConfig
        t0 = time.monotonic()
        work = self.host.work_root or Path(SandboxConfig.work_root)
        while (shutil.disk_usage(self.host.scratch).free < need_bytes + self.host.min_free_bytes
               or (work.exists() and shutil.disk_usage(work).free < self.host.min_free_bytes)):
            if time.monotonic() - t0 > timeout_s or (self.host.out / "STOP").exists():
                return False
            time.sleep(poll_s)
        return True


# ------------------------------------------------------------------------------------------------ instances, references
def build_reference_lite(instance, required, refdet, sst_loader):
    """`scoring.reference.build_reference` without the published-field detection, which the mode-agreement report alone uses and which
    needs the 1.9 GB published-fields file: the same loader calls, the same sea rule, the same `_computed_detection` (the study's
    reference code) for `gt` and `full`. A test proves it equal to `build_reference` on every field this check reads."""
    import icsa.scoring.reference as ref
    from icsa.extent import CellBox
    box = CellBox(instance.lat0, instance.lat1, instance.lon0, instance.lon1)
    tdays = ref.target_days_of(instance)
    if not np.array_equal(required.target.days, tdays):
        raise ValueError("required target extent days differ from the instance's target period")
    sst_b, sst_t = sst_loader(box, required.baseline.days), sst_loader(box, tdays)
    sea = refdet.sea_cells(sst_b, sst_t)
    full = ref._computed_detection(refdet, box, sea, tdays, required, sst_b, sst_t, required.baseline.mask, required.target.mask)
    return ref.Reference(instance, box, required, tdays, sea, sst_b, sst_t, full, full, refdet, None)


class Book:
    """Instances, required extents and the unperturbed references of this process (built once, thread-safe)."""

    def __init__(self, host: Host):
        from icsa.instances import load as L
        self.host, self._L = host, L
        m = L.load_instances()
        self._recs = {r["instance"]["instance_id"]: r for r in m["instances"]}
        self._masks = L.load_sea_masks(L.DATA / m["sea_masks"]["file"], m["sea_masks"]["sha256"])
        self._cache: dict = {}
        self._lock = threading.Lock()
        self._keyed: dict = {}

    def _once(self, key, fn):
        with self._lock:
            lk = self._keyed.setdefault(key, threading.Lock())
        with lk:
            if key not in self._cache:
                self._cache[key] = fn()
            return self._cache[key]

    def instance(self, iid: str):
        return self._once(("inst", iid), lambda: self._L.instance(self._recs[iid]))

    def required(self, iid: str):
        def build():
            rec = self._recs[iid]
            sea = self._masks[rec["instance"]["region_id"]]
            if int(sea.sum()) != rec["sea_cells"]:
                raise ValueError(f"{iid}: the sea mask disagrees with the manifest")
            return self._L.required_extent(rec, sea)
        return self._once(("req", iid), build)

    def events_free(self, iid: str) -> bool:
        return bool(self._recs[iid]["event_free"])

    def ref0(self, iid: str, layout: str):
        """The reference on the unperturbed data of the run's own layout (S1's daily files or S2's one file)."""
        import icsa.refdet as refdet
        return self._once(("ref0", iid, layout), lambda: build_reference_lite(
            self.instance(iid), self.required(iid), refdet, base_loader(self.host, layout)))

    def ref_under(self, iid: str, layout: str, edit: RC.GroupEdit):
        """The reference on the SST of the same data with the edit applied: the study's real reference code, fed the edited arrays
        (the files are read back and proved to hold exactly these values before any arm runs)."""
        import icsa.refdet as refdet
        r0 = self.ref0(iid, layout)

        def loader(box, days):
            days = np.asarray(days, dtype=np.int64)
            if np.array_equal(days, r0.required.baseline.days):
                base = r0.sst_baseline
            elif np.array_equal(days, r0.target_days):
                base = r0.sst_target
            else:
                raise ValueError("the reference asked for days it does not read")
            return RC.apply_edit_to_series(base, days, edit)
        return build_reference_lite(self.instance(iid), self.required(iid), refdet, loader)


def _s2_time_ok(path: Path, days) -> None:
    """The S2 time axis is the day axis (index = global day index); proved on the days read, never assumed."""
    import netCDF4
    from icsa import grid
    from icsa.ncio import NETCDF_LOCK
    days = [int(d) for d in days]
    with NETCDF_LOCK, netCDF4.Dataset(path) as ds:
        t = ds["time"]
        vals = np.asarray(t[:])[days]
        dates = netCDF4.num2date(vals, t.units, calendar=getattr(t, "calendar", "standard"),
                                 only_use_cftime_datetimes=False, only_use_python_datetimes=True)
    for d, x in zip(days, dates):
        if (x.year, x.month, x.day) != (lambda y: (y.year, y.month, y.day))(grid.day_date(d)):
            raise RC.PerturbationError(f"{path}: time index {d} is {x}, not {grid.day_date(d)}")


def base_loader(host: Host, layout: str):
    """sst_loader for `build_reference` over the host's own data: S1 daily files, or the S2 file by time index."""
    import netCDF4
    from icsa import grid
    from icsa.ncio import NETCDF_LOCK
    from icsa.refdet.data import _read_var, s1_index, s1_file

    def load(box, days):
        days = np.asarray(days, dtype=np.int64)
        out = np.full((days.size, *box.shape), np.nan, np.float32)
        with NETCDF_LOCK:
            if layout == "S1":
                index = s1_index(host.s1_dir)
                for k, d in enumerate(days):
                    with netCDF4.Dataset(s1_file(index, d)) as ds:
                        out[k] = _read_var(ds, box, 0).reshape(box.shape)
            else:
                _s2_time_ok(host.s2_file, days[slice(None, None, max(1, days.size // 50))])
                with netCDF4.Dataset(host.s2_file) as ds:
                    for k, d in enumerate(days):
                        out[k] = _read_var(ds, box, int(d)).reshape(box.shape)
        return out
    return load


# ---------------------------------------------------------------------------------------------------------- data trees
def tree_names():
    from icsa.harness import real_sandbox as rs
    return rs.SPACE_NAME, rs.S1_DIR, rs.S2_FILE


def base_tree(host: Host) -> Path:
    """The unperturbed stub root on the scratch: hard links of the host's data (built once; read-only for every control arm)."""
    from . import krun
    arm = host.scratch / "base"
    RC.mark(arm)
    root = arm / "root"
    krun.prepare_stub(root, src_s1=host.s1_dir, src_s2=host.s2_file)
    return root


def s1_name(day: int) -> str:
    from icsa import grid
    from icsa.instances.required import S1_PATTERN
    return S1_PATTERN.format(grid.day_date(int(day)))


def build_perturbed_tree(host: Host, layout: str, edit: RC.GroupEdit, name: str, *, cache_key: str | None = None) -> tuple[Path, Path, dict]:
    """A stub root identical to the host's data but for the edit. Returns (arm dir to delete, stub root, record).

    S1: the group's day files are new files (copy, then edit in place), every other file a hard link of the master.
    S2: the one file is a full private copy, edited in place. A file is opened for writing only after `assert_private_copy`.
    Every edited day is read back and compared bit for bit with the intended edit; the files not meant to change are checked to be
    the master's own inodes (S1) or, for S2, a seeded sample of other days is compared (and the full metadata signature)."""
    from . import krun
    space, s1d, s2f = tree_names()
    arm = RC.mark(host.scratch / "arms" / name)
    root = arm / "root"
    rec = {"layout": layout, **edit.describe()}
    t0 = time.monotonic()
    krun.prepare_stub(root, src_s1=host.s1_dir, src_s2=host.s2_file)
    rec["links_s"] = round(time.monotonic() - t0, 2)
    box = edit.box
    if layout == "S1":
        t0 = time.monotonic()
        for d, off, cells in zip(edit.days, edit.offsets, edit.cells):
            dst = root / space / s1d / s1_name(d)
            src = host.s1_dir / dst.name
            dst.unlink()
            shutil.copyfile(src, dst)
            RC.assert_private_copy(dst, src, host.scratch)
            RC.write_day_edit(dst, 0, box, cells, float(off))
            RC.verify_edited_day(src, 0, dst, 0, box, cells, float(off))
        rec["rewrite_and_verify_s"] = round(time.monotonic() - t0, 2)
        rec["files_rewritten"] = int(edit.days.size)
        edited = {s1_name(d) for d in edit.days}
        bad = [p.name for p in (root / space / s1d).iterdir() if p.name not in edited and not os.path.samefile(p, host.s1_dir / p.name)]
        if bad:
            raise RC.PerturbationError(f"{len(bad)} S1 files that should be the master's own are not, e.g. {bad[0]}")
        rec["other_files_are_masters"] = True
    else:
        dst, src = root / space / s2f, host.s2_file
        dst.unlink()
        t0 = time.monotonic()
        shutil.copyfile(src, dst)
        rec["s2_copy_s"], rec["s2_copy_bytes"] = round(time.monotonic() - t0, 2), dst.stat().st_size
        RC.assert_private_copy(dst, src, host.scratch)
        _s2_time_ok(dst, edit.days[slice(None, None, max(1, edit.days.size // 50))])
        t0 = time.monotonic()
        for d, off, cells in zip(edit.days, edit.offsets, edit.cells):
            RC.write_day_edit(dst, int(d), box, cells, float(off))
        for d, off, cells in zip(edit.days, edit.offsets, edit.cells):
            RC.verify_edited_day(src, int(d), dst, int(d), box, cells, float(off))
        import random
        rest = sorted(set(range(0, 15340)) - {int(x) for x in edit.days})
        sample = random.Random(f"{host.spec.seed}|s2check|{name}").sample(rest, 48)
        for d in sample:
            if not np.array_equal(RC._bits(RC.read_day(src, d)), RC._bits(RC.read_day(dst, d))):
                raise RC.PerturbationError(f"{dst}: day {d} changed but was not meant to")
        if RC.file_signature(src) != RC.file_signature(dst):
            raise RC.PerturbationError(f"{dst}: attributes, storage or coordinates differ from the master")
        rec["rewrite_and_verify_s"] = round(time.monotonic() - t0, 2)
        rec["files_rewritten"], rec["other_days_sampled"] = 1, len(sample)
    rec["verified"] = True
    return arm, root, rec


# ------------------------------------------------------------------------------------------------------- one replay arm
def image_present(image_id: str, _cache={}) -> bool:
    if image_id not in _cache:
        r = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", image_id], capture_output=True, text=True)
        _cache[image_id] = r.returncode == 0 and r.stdout.strip() == image_id
    return _cache[image_id]


def load_source(entry: dict, host: Host) -> dict:
    """What a replay needs from a run directory: the recorded cells, the final message, the run's identity and its image."""
    rd = Path(entry["run_dir"])
    cells = json.loads((rd / "code_cells.json").read_text())
    rec = json.loads((rd / "run_record.json").read_text())
    run = rec["run"]
    sb = rec.get("sandbox") or {}
    return {"run_dir": rd, "cells": cells, "option": run["option"], "layout": run["layout"], "instance_id": run["instance_id"],
            "final": ((rec.get("extras") or {}).get("final_text") or "Done."),
            "image_id": host.image_override or sb.get("pinned_image_id") or sb.get("image_id"),
            "orig_exit": [c.get("exit_code") for c in cells]}


class Sandboxes:
    """The exact sandbox directories this process started (recorded the moment each starts), and the exact-identity cleanup."""

    def __init__(self, host: Host):
        self.log = host.out / "sandbox-dirs.jsonl"
        self.leftovers = host.out / "leftovers.jsonl"
        self.lock = threading.Lock()

    def record(self, name: str, run_key: str, d) -> None:
        with self.lock, open(self.log, "a") as fh:
            fh.write(json.dumps({"arm": name, "run_key": run_key, "sbx_dir": str(d), "t": time.time()}) + "\n")

    def verify_gone(self, sbx_dir: Path) -> dict:
        from icsa.sandbox import hostops as H
        sid = sbx_dir.name

        def state():
            mounts = []
            for line in Path("/proc/self/mountinfo").read_text().splitlines():
                f = line.split()
                if len(f) > 4:
                    mp = f[4].replace("\\040", " ")
                    if mp == str(sbx_dir) or mp.startswith(str(sbx_dir) + "/"):
                        mounts.append(mp)
            r = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}", "--filter", f"name=^icsa-sbx-{re.escape(sid)}"],
                               capture_output=True, text=True)
            return {"dir_exists": sbx_dir.exists(), "mounts": mounts, "containers": [n for n in r.stdout.split() if n.startswith(f"icsa-sbx-{sid}")]}
        left = state()
        left["clean"] = not (left["dir_exists"] or left["mounts"] or left["containers"])
        if not left["clean"]:             # exactly this sandbox, never a prefix scan: other lanes' live sandboxes share run-key prefixes
            for c in left["containers"]:
                subprocess.run(["docker", "rm", "-f", c], capture_output=True)
            for m in sorted(left["mounts"], key=len, reverse=True):
                H.unmount(Path(m))
            H.sudo("rm", "-rf", "--one-file-system", str(sbx_dir), check=False)
            after = state()
            left["cleaned"] = not (after["dir_exists"] or after["mounts"] or after["containers"])
            with self.lock, open(self.leftovers, "a") as fh:
                fh.write(json.dumps({"sid": sid, **left}) + "\n")
        return left


def set_aside(path: Path) -> Path | None:
    """An unfinished earlier attempt in this arm's directory is moved aside, never reused or deleted: a stale output file must not be
    taken for this replay's."""
    path = Path(path)
    if not path.exists():
        return None
    dest = path.with_name(f"{path.name}.unfinished-{time.strftime('%Y%m%dT%H%M%S')}")
    k = 0
    while dest.exists():
        k += 1
        dest = path.with_name(f"{path.name}.unfinished-{time.strftime('%Y%m%dT%H%M%S')}-{k}")
    shutil.move(str(path), str(dest))
    return dest


def run_arm(host: Host, limits: Limits, sbxs: Sandboxes, src: dict, tree_root: Path, name: str, arm_dir: Path, book: Book) -> dict:
    """Replay the recorded cells once on `tree_root`. Never raises for a failed replay: the failure is the record."""
    from icsa.harness.adapters import StubAdapter
    from icsa.harness.errors import InfraError
    from icsa.harness.prompt import load_prompt_texts
    from icsa.harness.runner import RunContext, execute_run
    from icsa.harness import real_sandbox as rs
    from icsa.records import Layout, Option, RunId, Termination
    from icsa.sandbox import Sandbox
    from . import krun
    arm = {"name": name, "status": "infra", "detail": "", "wall_s": None, "sandbox_starts": 0, "termination": None,
           "memory_peak_bytes": None, "exit_codes": None, "mask": None}
    set_aside(arm_dir)
    image = src["image_id"]
    if not image or not image_present(image):
        arm["detail"] = f"image {image} is not present on this host"
        return arm
    option = Option(src["option"])
    need = sandbox_disk_bytes(host, option)
    if not limits.wait_for_room(need):            # a host condition, not a finding: the run is infra and is retried on resume
        raise RC.ScratchError(f"no room in time for a {option.value} sandbox's work disk ({need / 2**30:.1f} GiB beyond the floor)")
    inst = book.instance(src["instance_id"])
    script = [[("python", {"code": c["code"]})] for c in src["cells"]] + [src["final"]]
    seed = 700000 + int(hashlib.sha256(f"{src['run_dir']}|{name}".encode()).hexdigest()[:6], 16) % 200000
    run = RunId(src["instance_id"], option, Layout(src["layout"]), MODEL, seed)
    cfg = host.cfg
    started: list[Path] = []
    mock = None
    d_held = sbx_held = False
    try:
        limits.sandboxes.acquire()           # this host's own ceiling on sandboxes at once, whatever --jobs says
        sbx_held = True
        if option is Option.D:
            limits.d.acquire()
            d_held = True
        ids = json.loads(host.ids_json.read_text())
        sim = krun.LOCAL_SIM_TOKEN
        mock = krun.real_id_mock_class()(krun.mock_files(tree_root), ids=ids, space_name=rs.SPACE_NAME, zone_host=rs.ONEZONE_HOST,
                                         provider_host=rs.PROVIDER_HOST, token=sim).start()

        def factory(run_key, opt, layout, _dc=None):
            dc = krun.local_sim_data_config(opt, tree_root, mock)
            RC.assert_local_data_config(dc, opt, local_token=krun.LOCAL_SIM_TOKEN, real_hosts=(rs.ONEZONE_HOST, rs.PROVIDER_HOST))
            scfg = rs.sandbox_config(image, image, sandbox_limits=cfg.sandbox_limits, s1_size=host.s1_bytes, s2_size=host.s2_bytes,
                                     instruments=None)
            if host.work_root is not None:
                scfg = dataclasses.replace(scfg, work_root=host.work_root)
            sbx = Sandbox.start(run_key, opt, layout, dc, scfg)
            started.append(Path(sbx.dir))
            sbxs.record(name, run_key, sbx.dir)
            arm["sandbox_starts"] += 1
            sbx.record(pinned_image_id=image, instruments_sha256=None, instrument_module=None)
            return sbx
        ctx = RunContext(cfg=cfg, texts=load_prompt_texts(), instances={src["instance_id"]: inst}, sandbox_factory=factory,
                         adapter_factory=lambda spec, s, slot: StubAdapter(script, name="replay", seed=s))
        t0 = time.monotonic()
        try:
            rec = asyncio.run(asyncio.wait_for(execute_run(run, 1, arm_dir, None, ctx), timeout=host.arm_cap_s))
            arm["wall_s"] = round(time.monotonic() - t0, 1)
        except asyncio.TimeoutError:
            arm.update(status="capped", detail=f"the arm hit its wall cap of {host.arm_cap_s:.0f} s", wall_s=round(time.monotonic() - t0, 1))
            return arm
        except InfraError as e:
            arm.update(detail=f"{e.kind}: {e.detail}"[:300], wall_s=round(time.monotonic() - t0, 1))
            return arm
        except Exception as e:  # noqa: BLE001 -- recorded; the arm is no evidence
            arm.update(detail=f"{type(e).__name__}: {e}"[:300], wall_s=round(time.monotonic() - t0, 1))
            return arm
        sb = rec.sandbox or {}
        arm["termination"] = rec.termination.value
        arm["memory_peak_bytes"] = sb.get("memory_peak_bytes")
        cells = json.loads((arm_dir / "code_cells.json").read_text()) if (arm_dir / "code_cells.json").is_file() else []
        arm["exit_codes"] = [c.get("exit_code") for c in cells]
        if rec.termination is not Termination.REPORT:
            arm.update(status="capped", detail=f"the replay ended on {rec.termination.value}")
            return arm
        r0 = book.ref0(src["instance_id"], src["layout"])
        mask, why = read_mask(arm_dir / "output", r0.box, r0.target_days)
        if mask is None:
            arm.update(status="no_mask", detail=f"mask: {why}")
            return arm
        arm.update(status="ok", mask=mask)
        return arm
    finally:
        if mock is not None:
            try:
                mock.stop()
            except Exception:  # noqa: BLE001
                pass
        if d_held:
            limits.d.release()
        if sbx_held:
            limits.sandboxes.release()
        left = [sbxs.verify_gone(d) for d in started]
        if left and not all(x["clean"] for x in left):
            arm["sandbox_cleanup"] = left


# ----------------------------------------------------------------------------------------------------------- one run
def read_mask(output_dir: Path, box, target_days) -> tuple[np.ndarray | None, str]:
    """The canonical mask of a run's output (the scoring parser's own: dims, coordinates and values are checked as scoring checks them),
    or (None, why). A mask that scoring would call invalid is not replayable: the test compares masks, and this one has none."""
    from icsa.scoring.report import InvalidOutput, parse_mask
    try:
        return parse_mask(Path(output_dir) / "mhw_mask.nc", box, target_days), ""
    except InvalidOutput as e:
        return None, str(e)[:200]


def _arm_record(a: dict) -> dict:
    return {k: v for k, v in a.items() if k not in SKIP_ARM_KEYS}


def check_run(host: Host, limits: Limits, sbxs: Sandboxes, book: Book, entry: dict) -> dict:
    """The control, then each group, for one planned run. Returns the run's result (never a verdict about the run's coverage)."""
    t_run = time.monotonic()
    res = {"format": RC.FORMAT_RUN, "pos": entry["pos"], "run_key": entry["run_key"], "segment": entry.get("segment"), "kind": entry.get("kind"),
           "phase": entry.get("phase"), "option": entry["option"], "layout": entry["layout"], "instance_id": entry["instance_id"],
           "label": entry["label"], "status": "infra", "reason": None, "control_state": "not_run", "control": None, "groups": [],
           "perturbation": host.spec.as_dict(), "timing": {}, "notes": {"report": RC.REPORT_NOTE, "limit": RC.LIMIT_NOTE}}
    name = hashlib.sha256(entry["run_key"].encode()).hexdigest()[:12]
    arms_dir = host.out / "arms" / name
    timing = res["timing"]
    try:
        src = load_source(entry, host)
        if (src["option"], src["layout"], src["instance_id"]) != (entry["option"], entry["layout"], entry["instance_id"]):
            res.update(status="not_replayable", reason="the plan entry disagrees with the run's own record")
            return res
        iid, layout = src["instance_id"], src["layout"]
        t0 = time.monotonic()
        r0 = book.ref0(iid, layout)
        timing["reference_wall_s"] = round(time.monotonic() - t0, 1)
        saved_mask, why = read_mask(src["run_dir"] / "output", r0.box, r0.target_days)
        if saved_mask is None:
            res.update(status="not_replayable", reason=f"the run's saved mask is not valid ({why})")
            return res
        # ---- the control: the unperturbed replay must reproduce the saved mask exactly
        ctl = run_arm(host, limits, sbxs, src, limits.base_root(), f"{name}-control", arms_dir / "control", book)
        res["control"] = _arm_record(ctl)
        timing["replay_wall_s"] = ctl["wall_s"] or 0.0
        if ctl["status"] == "infra":      # the harness or the host failed, not the run: no statement about the run, retried on resume
            raise RuntimeError(f"control arm infrastructure failure: {ctl['detail']}")
        if ctl["status"] != "ok":
            res.update(status="not_replayable", reason=f"control arm {ctl['status']}: {ctl['detail']}", control_state="not_reproduced")
            return res
        if not RC.masks_equal(ctl["mask"], saved_mask):
            res.update(status="not_replayable", control_state="not_reproduced",
                       reason=f"the control replay differs from the saved mask in {RC.n_differing(ctl['mask'], saved_mask)} cell-days")
            return res
        res["control_state"] = "reproduced"
        # ---- the groups
        groups = RC.select_groups(host.group_mode, host.spec.seed, entry["run_key"], n_years=host.n_years,
                                  explicit=entry.get("groups") or getattr(host, "explicit_groups", None))
        ref_base = r0.gt.cell_mask & r0.sea
        for g in groups:
            res["groups"].append(check_group(host, limits, sbxs, book, src, ctl, r0, ref_base, g, name, arms_dir, timing))
        res["status"] = "replayed"
        return res
    except Exception as e:  # noqa: BLE001 -- the run's own failure: infra, retried on the next invocation, never labelled
        res.update(status="infra", reason=f"{type(e).__name__}: {e}"[:400], tb=traceback.format_exc()[-1200:])
        return res
    finally:
        timing["total_wall_s"] = round(time.monotonic() - t_run, 1)


def check_group(host, limits, sbxs, book, src, ctl, r0, ref_base, g, name, arms_dir, timing) -> dict:
    iid, layout = src["instance_id"], src["layout"]
    out = {"group": g, "outcome": "not_tested", "reason": None, "arm": None}
    t0 = time.monotonic()
    edit = RC.build_edit(g, book.required(iid), host.spec, iid)
    ref_g = book.ref_under(iid, layout, edit)
    ref_pert = ref_g.gt.cell_mask & ref_g.sea
    timing["reference_wall_s"] = round(timing.get("reference_wall_s", 0) + time.monotonic() - t0, 1)
    out["edit"] = edit.describe()
    pre = RC.compare_group(ref_base, ref_pert, None, None, r0.sea, arm_ok=False)
    if pre["reason"] == "reference_did_not_move":              # nothing to compare against: no arm is run, no evidence is claimed
        out.update(pre)
        out["event_free_instance"] = book.events_free(iid)
        return out
    need = int(host.s2_bytes * 1.25) if layout == "S2" else 0     # the copy grows as its day chunks are rewritten (4.4 GB for space)
    s2_held = False
    arm_dir = None
    try:
        if layout == "S2":
            limits.s2.acquire()
            s2_held = True
        if not limits.wait_for_room(need):       # a transient host condition, not a finding: the run is infra and is retried on resume
            raise RC.ScratchError(f"the scratch or the sandbox disk had no room in time (need {need / 2**30:.1f} GiB beyond the floor)")
        t0 = time.monotonic()
        try:
            arm_dir, root, prec = build_perturbed_tree(host, layout, edit, f"{name}-{g.replace(':', '')}")
        except RC.PerturbationError as e:
            out.update(pre, reason="perturbation_unverified", detail=str(e)[:300])
            return out
        finally:
            timing["perturb_wall_s"] = round(timing.get("perturb_wall_s", 0) + time.monotonic() - t0, 1)
        timing["s2_copy_s"] = round(timing.get("s2_copy_s", 0) + prec.get("s2_copy_s", 0), 1)
        timing["s2_copy_bytes"] = timing.get("s2_copy_bytes", 0) + prec.get("s2_copy_bytes", 0)
        out["perturbed_tree"] = prec
        arm = run_arm(host, limits, sbxs, src, root, f"{name}-{g.replace(':', '')}", arms_dir / g.replace(":", "-"), book)
    finally:
        if arm_dir is not None:
            try:
                RC.safe_rmtree(arm_dir, host.scratch)
            except Exception as e:  # noqa: BLE001
                out["cleanup_error"] = f"{type(e).__name__}: {e}"[:200]
        if s2_held:
            limits.s2.release()
    timing["replay_wall_s"] = round(timing.get("replay_wall_s", 0) + (arm["wall_s"] or 0), 1)
    ok = arm["status"] == "ok"
    detail = arm["detail"]
    if ok and arm["exit_codes"] != ctl["exit_codes"]:         # cells that fail differently from the control: the data broke the code
        arm["status"], ok = "cells_differ", False
        bad = [i for i, (x, y) in enumerate(zip(arm["exit_codes"], ctl["exit_codes"]), 1) if x != y]
        detail = f"cell exit codes differ from the control in cells {bad[:10]}"
        arm["detail"] = detail
    cmp = RC.compare_group(ref_base, ref_pert, ctl["mask"], arm["mask"], r0.sea, arm_ok=ok, arm_detail=f"{arm['status']}: {detail}")
    out.update(cmp)
    out["arm"] = _arm_record(arm)
    return out


# ------------------------------------------------------------------------------------------------------------- the CLI
def log(host: Host, msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    with open(host.out / "driver.log", "a") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def run_main(a) -> int:
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    from icsa.sandbox.termination import exit_on_sigterm
    host = Host.from_args(a)
    host.out.mkdir(parents=True, exist_ok=True)
    plan = json.loads((host.out / "plan.json").read_text())
    try:
        info = RC.check_scratch(host.scratch, [host.s1_dir, host.s2_file], need_bytes=host.s2_bytes * host.max_s2_copies,
                                min_free_bytes=host.min_free_bytes)
    except RC.ScratchError as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 2
    exit_on_sigterm()           # a real-sandbox driver: a SIGTERM is an orderly exit, never a mount left to the reaper
    (host.out / "results").mkdir(exist_ok=True)
    (host.out / "driver.pid").write_text(str(os.getpid()))
    book = Book(host)
    limits, sbxs = Limits(host), Sandboxes(host)
    done = {r["run_key"] for r in RC.load_results(host.out) if r["status"] in ("replayed", "not_replayable")}
    todo = [e for e in plan["entries"] if e["run_key"] not in done]
    log(host, f"start: python {sys.version.split()[0]}; {len(plan['entries'])} planned, {len(done)} finished, {len(todo)} to do; groups {a.groups}; "
              f"delta {host.spec.delta_k} K; jobs {host.jobs}; scratch free {info['free_bytes'] / 2**30:.0f} GiB")
    n_done = 0

    def work(e):
        res = check_run(host, limits, sbxs, book, e)
        if res["status"] == "infra":
            k = 1
            while (host.out / "results" / "infra" / f"{RC.result_name(e['run_key'])[:-5]}-{k}.json").exists():
                k += 1
            (host.out / "results" / "infra").mkdir(exist_ok=True)
            RC._write_json(host.out / "results" / "infra" / f"{RC.result_name(e['run_key'])[:-5]}-{k}.json", res)
        else:
            RC._write_json(host.out / "results" / RC.result_name(e["run_key"]), res)
        RC._write_json(host.out / "progress.json", RC.progress(plan, host.out))
        log(host, f"pos {e['pos']} {e['option']}/{e['layout']}: {res['status']}"
                  + (f" ({res['reason'][:80]})" if res.get("reason") else "")
                  + (" groups " + ",".join(g["outcome"] for g in res["groups"]) if res["groups"] else "") + f" in {res['timing'].get('total_wall_s')} s")
        return res

    pending = list(todo)
    running: dict = {}
    with ThreadPoolExecutor(host.jobs) as ex:
        while pending or running:
            stop = (host.out / "STOP").exists() or (a.limit is not None and n_done + len(running) >= a.limit)
            while pending and len(running) < host.jobs and not stop:
                e = pending.pop(0)
                running[ex.submit(work, e)] = e
                stop = a.limit is not None and n_done + len(running) >= a.limit
            if not running:
                break
            dn, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for f in dn:
                running.pop(f)
                n_done += 1
                if f.exception():
                    log(host, f"worker raised {type(f.exception()).__name__}: {str(f.exception())[:200]}")
    s = RC.summarise(plan, RC.load_results(host.out))
    RC._write_json(host.out / "summary.json", s)
    RC._write_json(host.out / "replay_status.json", RC.replay_status(s))
    log(host, f"finished: {s['progress']['reached_note']}")
    return 0
