"""The WAN anchor: the scripted pipeline through T, D and M from the off-site provider `site_c` (#12, operator decision).

Inbound from site_c is about 10 Mbit/s (#10), so this runs in the background and never blocks the main campaign. The data
sits in an `icsa2027_wan_*` space supported by site_c only. Every run traces per-request times client-side (T, D) or
per-day times (M; the script's `per_day_s`); the gate log stamps completions only, and the gate is not changed for this.
"""
from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path

import numpy as np

from ..instances import load as L
from ..records import Layout, Option
from . import federation as F
from . import insandbox as I
from . import provision as V
from .plans import WAN
from .runner import Plan, run_one

SITE_C = "site_c"
OPTIONS = (Option.T, Option.D, Option.M)


@dataclasses.dataclass(frozen=True)
class WanSpace:
    name: str
    space_id: str
    root_id: str
    s1_dir_id: str
    s2_dir_id: str

    def target(self) -> F.DataTarget:
        return F.DataTarget("wan", self.name, self.space_id, SITE_C, F.od_module().PROVIDERS[SITE_C]["host"])


def wan_plan(seed: int, *, s2_instance: str | None = "I35") -> list[Plan]:
    """S1 for the three anchors in a seeded order, then S2 for one instance (the part dropped if time runs out)."""
    s1 = [Plan(i, o, Layout.S1, tag="wan") for i in WAN for o in OPTIONS]
    order = np.random.default_rng(seed).permutation(len(s1))
    out = [s1[int(k)] for k in order]
    if s2_instance is not None:
        s2 = [Plan(s2_instance, o, Layout.S2, tag="wan") for o in OPTIONS]
        order = np.random.default_rng(seed + 1).permutation(len(s2))
        out += [s2[int(k)] for k in order]
    return out


def setup_space(o, od_safe, out: Path, manifests: Path, s1_dir: Path, s2_file: Path, recs: dict, *,
                size_bytes: int = 20 * 10 ** 9) -> WanSpace:
    """Create, upload, then check: every size, and the sha256 of the anchors' required files only, because a whole
    download at 10 Mbit/s takes hours. Each run's SST hash then checks the values it read against the local reference."""
    name = "icsa2027_wan_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    sid = V.create_space(o, od_safe, name, [SITE_C], size_bytes)
    (out / "space_created.json").write_text(json.dumps({"name": name, "space_id": sid, "providers": [SITE_C]}))
    root = V.space_root(o, SITE_C, sid)
    up = V.upload_dataset(o, SITE_C, root, s1_dir, s2_file, workers=4)   # a few streams (the lead's bound)
    s1 = V.children(o, SITE_C, up["s1_dir_id"])
    s2 = V.children(o, SITE_C, up["s2_dir_id"])
    m1, m2 = V.read_manifest(manifests / "s1_sha256.txt"), V.read_manifest(manifests / "s2_sha256.txt")
    if sorted(s1) != sorted(m1) or sorted(s2) != sorted(m2):
        raise RuntimeError("the uploaded names differ from the manifests")
    local = {p.name: p.stat().st_size for p in Path(s1_dir).glob("*.nc")}
    wrong = sorted(n for n, e in s1.items() if int(e["size"]) != local[n])
    if int(s2["sst_s2.nc"]["size"]) != Path(s2_file).stat().st_size:
        wrong.append("sst_s2.nc")
    needed = {I.s1_name(int(d)) for i in WAN for d in L.required_day_indices(recs[i])}
    check = V.verify_files(o, SITE_C, {n: s1[n] for n in sorted(needed)}, m1, workers=4)
    rec = {"space": name, "space_id": sid, "upload": up, "size_mismatches": wrong, "verify_required_s1": check,
           "not_hashed": "the other S1 files and S2: sizes only; every run hashes the values it read"}
    (out / "space_verify.json").write_text(json.dumps(rec, indent=1))
    if wrong or not check["ok"]:
        raise RuntimeError(f"verification failed: sizes {wrong[:5]}, hashes {check['mismatches'][:5]}")
    sp = WanSpace(name, sid, root, up["s1_dir_id"], up["s2_dir_id"])
    (out / "space.json").write_text(json.dumps(dataclasses.asdict(sp), indent=1))
    return sp


def run(sp: WanSpace, plans: list[Plan], recs: dict, truth, refs: dict, cfg, out: Path, *, o, say=print,
        pause_file: Path | None = None) -> list[dict]:
    """`pause_file`: if it exists before a run starts, the batch stops there, at a run boundary, with nothing half-done; the
    next `--resume` carries on (the queue removes the file to resume)."""
    V.check_space(o, SITE_C, sp.space_id, sp.root_id, {V.S1_DIR: sp.s1_dir_id, V.S2_DIR: sp.s2_dir_id})
    target = sp.target()
    done = []
    for p in plans:
        if pause_file is not None and Path(pause_file).exists():
            say({"run_key": "(paused)", "ok": True, "errors": [], "host_before": {"load1": None, "other_sandboxes": None},
                 "note": f"paused at a run boundary by {pause_file}; next: {p.key()}"})
            break
        r = run_one(p, recs[p.instance_id], truth, lambda o=p.option: F.data_config(target, o, ttl_s=12 * 3600), cfg, out,
                    expected_sst=refs[p.instance_id], timeout_s=8 * 3600, trace_http=True, extra={"variant": "wan"})
        say(r)
        done.append(r)
    return done
