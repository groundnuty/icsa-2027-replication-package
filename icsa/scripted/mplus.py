"""M+: data pre-provisioned at the agent-site provider, measured by script only (#12).

Space: `icsa2027_mplus_<stamp>`, supported by the data provider site_g and the agent site site_f, holding the same bytes as the
main space (uploaded to site_g, hashed from site_g against #3's manifests). The main space stays exclusive to site_g.

Forbidden check (the issue's): M+ measured on data already cached from an earlier M run. So, before every provisioning,
site_f's replica is evicted and site_f is confirmed EMPTY through the block map; after it, the required extent is confirmed
PLACED through the block map; right before the mount the sandbox's `replicate` hook confirms it once more; every run has
a fresh oneclient process and mount. A transfer's reported status never counts as placement (PRIOR_STUDY 0003, 0006).

Provisioning scopes:
  required   S1: one replication job per required daily file. S2: Onedata's jobs replicate whole files only, so the
             required byte ranges (traced from the pipeline's reader, `s2ranges`) are read through site_f's REST
             endpoint, which fetches them from site_g on the fly.
  layout     one replication job for the s1z directory, or for the S2 file.

M cold has two variants, kept apart in the records: `cold-site_g` (mount on the data provider, the campaign's M; site_f is never
involved) and `cold-site_f` (mount on site_f with its replica evicted, so reads replicate on the fly from site_g).
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
from .runner import Plan, run_one, split_days

SITE_G, SITE_F = "site_g", "site_f"
S1, S2 = Layout.S1, Layout.S2


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclasses.dataclass(frozen=True)
class MplusSpace:
    name: str
    space_id: str
    root_id: str
    s1_dir_id: str
    s2_dir_id: str
    s2_file_id: str
    s2_size: int

    def target(self, provider: str) -> F.DataTarget:
        od = F.od_module()
        return F.DataTarget(f"mplus-{provider}", self.name, self.space_id, provider, od.PROVIDERS[provider]["host"])

    @classmethod
    def load(cls, path: Path | str) -> "MplusSpace":
        return cls(**json.loads(Path(path).read_text()))


class Campaign:
    """Operations on one M+ space. `o` is an authenticated `od.OD` (host side only, never reaches a sandbox)."""

    def __init__(self, o, sp: MplusSpace, log_path: Path):
        self.o, self.sp, self.log_path = o, sp, Path(log_path)
        od = F.od_module()
        self.site_g_id, self.site_f_id = od.PROVIDERS[SITE_G]["id"], od.PROVIDERS[SITE_F]["id"]
        V.check_space(o, SITE_G, sp.space_id, sp.root_id,
                      {V.S1_DIR: sp.s1_dir_id, V.S2_DIR: sp.s2_dir_id, f"{V.S2_DIR}/{V.S2_NAME}": sp.s2_file_id})
        self.s1_entries = V.children(o, SITE_G, sp.s1_dir_id)   # name -> entry (file id, size), the whole directory

    def log(self, event: str, **kw) -> dict:
        rec = {"utc": now(), "event": event, **kw}
        with open(self.log_path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        print(json.dumps({k: v for k, v in rec.items() if k != "short_file_ids"}, default=str)[:600], flush=True)
        return rec

    # ----------------------------------------------------------------- what a scope consists of
    def s1_required(self, rec: dict) -> dict[str, list[tuple[int, int]]]:
        """file id -> whole-file range, for the instance's 1,544 daily files."""
        out = {}
        for d in L.required_day_indices(rec):
            e = self.s1_entries[I.s1_name(int(d))]
            out[e["fileId"]] = [(0, int(e["size"]))]
        return out

    def wanted(self, layout: Layout, rec: dict | None, s2_ranges: list[tuple[int, int]] | None) -> dict[str, list[tuple[int, int]]]:
        """The placement a scope promises. rec None = the whole layout."""
        if layout == S1:
            if rec is None:
                return {e["fileId"]: [(0, int(e["size"]))] for e in self.s1_entries.values()}
            return self.s1_required(rec)
        if rec is None:
            return {self.sp.s2_file_id: [(0, self.sp.s2_size)]}
        if not s2_ranges:
            raise ValueError("the required extent of S2 needs its traced byte ranges")
        return {self.sp.s2_file_id: list(s2_ranges)}

    # ----------------------------------------------------------------- eviction
    def evict_site_f(self, layout: Layout, *, timeout_s: float = 3600) -> dict:
        """Evict site_f's replica of the whole layout, one job; returns once the block map shows site_f empty."""
        target = self.sp.s1_dir_id if layout == S1 else self.sp.s2_file_id
        files = [e["fileId"] for e in self.s1_entries.values()] if layout == S1 else [self.sp.s2_file_id]
        t0 = time.time()
        tid = V.schedule_eviction(self.o, SITE_F, target, self.site_f_id, holder_id=self.site_g_id)
        report = V.wait_transfers(self.o, SITE_F, [tid], timeout_s=timeout_s)
        self.require_ended(report, "eviction")
        empty = None
        for _ in range(60):
            empty = V.holds_nothing(self.o, SITE_F, self.site_f_id, files)
            if empty["empty"]:
                break
            time.sleep(5)
        return self.log("evict", layout=layout.value, seconds=round(time.time() - t0, 1), transfer=report, site_f=empty,
                        confirmed_empty=bool(empty and empty["empty"]))

    def require_ended(self, report: dict, what: str) -> None:
        """A transfer still running can change site_f's replica after any later check, so nothing may follow it."""
        if report["timed_out"]:
            self.log("transfer_not_ended", what=what, transfers=report["timed_out"])
            raise RuntimeError(f"{what}: transfers {report['timed_out']} had not ended at the timeout; stopping. They may "
                               "still change site_f's replica: check them before any further step (no cancel without the operator)")

    def require_empty(self, layout: Layout) -> dict:
        ev = self.evict_site_f(layout)
        if not ev["confirmed_empty"]:
            raise RuntimeError(f"site_f still holds {ev['site_f']['held_bytes']} B of {layout.value} after eviction: "
                               "M+ cannot start from a known-empty site (PRIOR_STUDY 0006); stopping")
        return ev

    # ----------------------------------------------------------------- provisioning
    def provision_jobs(self, file_ids: list[str], *, timeout_s: float) -> dict:
        t0 = time.time()
        tids = [V.schedule_replication(self.o, SITE_F, fid, self.site_f_id) for fid in file_ids]
        t_posted = time.time()
        report = V.wait_transfers(self.o, SITE_F, tids, timeout_s=timeout_s)
        self.require_ended(report, "replication")
        return {"jobs": len(tids), "post_seconds": round(t_posted - t0, 3), "transfer": report,
                "reported_seconds": round(time.time() - t0, 3)}

    def provision_ranges(self, file_id: str, ranges: list[tuple[int, int]]) -> dict:
        """Read the ranges through site_f's REST endpoint: site_f fetches what it lacks from site_g, on the fly."""
        t0 = time.time()
        n = 0
        for off, ln in ranges:
            r = self.o.op(SITE_F, "GET", f"/data/{file_id}/content", timeout=900, expect=(200, 206),
                          headers={"Range": f"bytes={off}-{off + ln - 1}"})
            n += len(r.content)
        return {"ranges": len(ranges), "bytes_read": n, "reported_seconds": round(time.time() - t0, 3)}

    def confirm_placed(self, wanted: dict[str, list[tuple[int, int]]], *, settle_s: float = 300) -> dict:
        """Poll the block map until the scope is placed or `settle_s` passes. The time it took is the placement lag."""
        t0 = time.time()
        while True:
            rep = V.placement_report(self.o, SITE_F, self.site_f_id, wanted)
            if rep["fully_placed"] or time.time() - t0 > settle_s:
                rep["lag_seconds"] = round(time.time() - t0, 3)
                return rep
            time.sleep(5)

    def provision(self, layout: Layout, rec: dict | None, s2_ranges) -> dict:
        """From a confirmed-empty site_f to a confirmed placement. `seconds` includes the block-map wait, not the eviction."""
        wanted = self.wanted(layout, rec, s2_ranges)
        scope = "required" if rec is not None else "layout"
        t0 = time.time()
        if layout == S1 and rec is not None:
            step = self.provision_jobs(list(wanted), timeout_s=4 * 3600)
        elif layout == S1:
            step = self.provision_jobs([self.sp.s1_dir_id], timeout_s=4 * 3600)
        elif rec is None:
            step = self.provision_jobs([self.sp.s2_file_id], timeout_s=4 * 3600)
        else:
            step = self.provision_ranges(self.sp.s2_file_id, list(s2_ranges))
        placed = self.confirm_placed(wanted)
        seconds = round(time.time() - t0, 3)
        out = self.log("provision", scope=scope, layout=layout.value, instance=(rec or {}).get("instance", {}).get("instance_id"),
                       seconds=seconds, step=step, placement=placed, placed_bytes=placed["held_bytes"],
                       confirmed_placed=placed["fully_placed"])
        if not out["confirmed_placed"]:
            raise RuntimeError(f"{scope} {layout.value}: {placed['bytes_short']} B not placed on site_f after the transfer "
                               f"reported {step.get('transfer', {}).get('states')} (PRIOR_STUDY 0001, 0003); stopping")
        return out

    def placement_hook(self, wanted: dict[str, list[tuple[int, int]]], state: dict):
        """`DataConfig.replicate`: the sandbox calls it right before the mount; no placement, no run. `state` tells the
        caller whether it ran and what it found, since the runner turns the exception into a failed record."""
        def check() -> None:
            rep = V.placement_report(self.o, SITE_F, self.site_f_id, wanted)
            state.update(checked=True, fully_placed=rep["fully_placed"], bytes_short=rep["bytes_short"])
            self.log("placement_before_mount", files=rep["files"], held_bytes=rep["held_bytes"],
                     fully_placed=rep["fully_placed"], bytes_short=rep["bytes_short"])
            if not rep["fully_placed"]:
                raise RuntimeError(f"refusing to run M+: {rep['bytes_short']} B of the scope are not on site_f")
        return check


def run_mplus(camp: Campaign, scope: str, plan: Plan, rec, truth, cfg, out: Path, expected_sst: str, wanted) -> dict:
    """One M+ run on pre-placed data. What site_f held before and after is recorded, so that on-the-fly fetches during the
    run (bytes the scope did not cover) show as growth instead of passing as pre-placed."""
    target = camp.sp.target(SITE_F)
    file_ids = [camp.sp.s2_file_id] if plan.layout == S2 else list(wanted)
    before = V.holds_nothing(camp.o, SITE_F, camp.site_f_id, file_ids)["held_bytes"]
    state: dict = {"checked": False}
    r = run_one(plan, rec, truth, lambda: F.data_config(target, Option.M_PLUS, replicate=camp.placement_hook(wanted, state)),
                cfg, out, expected_sst=expected_sst, extra={"variant": "mplus", "scope": scope, "site_f_held_before": before})
    if not (state["checked"] and state.get("fully_placed")):
        camp.log("mplus_stopped", run_key=r["run_key"], placement_check=state, errors=r["errors"][:2])
        raise RuntimeError(f"{r['run_key']}: the placement check before the mount did not pass ({state}); stopping")
    after = V.holds_nothing(camp.o, SITE_F, camp.site_f_id, file_ids)["held_bytes"]
    camp.log("mplus_run", scope=scope, run_key=r["run_key"], ok=r["ok"], wall_s=r.get("wall_s"),
             site_f_held_before=before, site_f_held_after=after, on_the_fly_growth=after - before)
    return r


def run_cold(camp: Campaign, variant: str, plan: Plan, rec, truth, cfg, out: Path, expected_sst: str) -> dict:
    """One M cold run. `cold-site_f`: mount on site_f from a confirmed-empty replica. `cold-site_g`: mount on site_g, the data provider."""
    if variant == "cold-site_f":
        camp.require_empty(plan.layout)
        target = camp.sp.target(SITE_F)
    elif variant == "cold-site_g":
        target = camp.sp.target(SITE_G)
    else:
        raise ValueError(f"unknown variant {variant!r}")
    return run_one(plan, rec, truth, lambda: F.data_config(target, Option.M), cfg, out, expected_sst=expected_sst,
                   extra={"variant": variant})


def whole_cells(runs: list[dict]) -> list[dict]:
    """The records of whole cells: one carrying `extra.probe_files` is the live probe's prefix of a cell (`baseline --probe-files`), no run of the study, and is never a sample here."""
    return [r for r in runs if (r.get("extra") or {}).get("probe_files") is None]


def break_even_inputs(prov_log: list[dict], runs: list[dict], *, wan_runs: list[dict] | None = None,
                      site_g_runs: list[dict] | None = None) -> dict:
    """Samples per (scope, layout) for the bootstrap: P from the provisioning log, W and C from the run records.

    `wan_runs`: the WAN anchor's records; its M runs give C of the scripted WAN bound. `site_g_runs`: M runs on the data
    provider from another batch (the pilot pass), counted as cold-site_g. Only clean runs count, so a failed run can never
    shorten a measured time; the excluded counts are returned."""
    out: dict[str, dict] = {}
    for layout in ("S1", "S2"):
        wall: dict[str, list[float]] = {"mplus-required": [], "mplus-layout": [], "cold-site_g": [], "cold-site_f": [],
                                        "cold-wan": []}
        first: dict[str, list[float]] = {k: [] for k in wall}
        excluded = 0
        tagged = [(r, r["extra"].get("variant")) for r in whole_cells(runs)]
        tagged += [(r, "cold-wan") for r in whole_cells(wan_runs or []) if r["option"] == "M"]
        tagged += [(r, "cold-site_g") for r in whole_cells(site_g_runs or []) if r["option"] == "M"]
        for r, key in tagged:
            if r["layout"] != layout:
                continue
            if key == "mplus":
                key = f"mplus-{r['extra'].get('scope')}"
            if key not in wall:
                continue
            if not r["ok"]:
                excluded += 1
                continue
            wall[key].append(r["wall_s"])
            first[key].append(r["script"]["first_compute_s"])
        events = [e for e in prov_log if e.get("event") == "provision" and e["layout"] == layout]
        good = [e for e in events if e.get("confirmed_placed") is True]
        prov = {s: [e["seconds"] for e in good if e["scope"] == s] for s in ("required", "layout")}
        pbytes = {s: [e["placed_bytes"] for e in good if e["scope"] == s] for s in ("required", "layout")}
        out[layout] = {"provision_s": prov, "placed_bytes": pbytes, "wall_s": wall, "first_compute_s": first,
                       "failed_runs_excluded": excluded, "unconfirmed_provisioning_excluded": len(events) - len(good)}
    return out


def s2_required_ranges(s2_path: Path, rec: dict) -> list[tuple[int, int]]:
    from .s2ranges import required_ranges
    base, tgt = split_days(rec)
    return required_ranges(s2_path, rec, np.concatenate([base, tgt]))


def setup_space(o, od_safe, out: Path, manifests: Path, s1_dir: Path, s2_file: Path, *, size_bytes: int = 20 * 10 ** 9) -> MplusSpace:
    """Create the M+ space on site_g + site_f, upload to site_g, hash everything from site_g against #3's manifests. The time this takes and the blocks that stalled are in the
    record as the setup's (science, #34, 2 Nov 11:37Z). They are not the break-even's: that reads only the `provision` events, the replication to site_f."""
    t_setup = time.time()
    name = "icsa2027_mplus_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    sid = V.create_space(o, od_safe, name, [SITE_G, SITE_F], size_bytes)
    (out / "space_created.json").write_text(json.dumps({"name": name, "space_id": sid, "providers": [SITE_G, SITE_F], "utc": now()}))
    root = V.space_root(o, SITE_G, sid)
    up = V.upload_dataset(o, SITE_G, root, s1_dir, s2_file, stall_retry=True)
    s1 = V.children(o, SITE_G, up["s1_dir_id"])
    s2 = V.children(o, SITE_G, up["s2_dir_id"])
    m1, m2 = V.read_manifest(manifests / "s1_sha256.txt"), V.read_manifest(manifests / "s2_sha256.txt")
    if sorted(s1) != sorted(m1) or sorted(s2) != sorted(m2):
        raise RuntimeError("the uploaded names differ from the manifests")
    check1 = V.verify_files(o, SITE_G, s1, m1)
    check2 = V.verify_files(o, SITE_G, s2, m2, workers=1)
    rec = {"space": name, "space_id": sid, "upload": up, "verify_s1": check1, "verify_s2": check2, "utc": now(),
           "setup_seconds": round(time.time() - t_setup, 1), "stalled_blocks": up["stalled_blocks"], "stall_seconds": up["stall_seconds"]}
    (out / "space_verify.json").write_text(json.dumps(rec, indent=1))
    with open(out / "mplus_log.jsonl", "a") as f:
        f.write(json.dumps({"utc": rec["utc"], "event": "setup", "space": name, "setup_seconds": rec["setup_seconds"], "stalled_blocks": rec["stalled_blocks"],
                            "stall_seconds": rec["stall_seconds"], "verified": bool(check1["ok"] and check2["ok"])}) + "\n")
    if not (check1["ok"] and check2["ok"]):
        raise RuntimeError(f"verification failed: {check1['mismatches'][:5]} {check2['mismatches'][:5]}")
    sp = MplusSpace(name, sid, root, up["s1_dir_id"], up["s2_dir_id"], s2["sst_s2.nc"]["fileId"], int(s2["sst_s2.nc"]["size"]))
    (out / "space.json").write_text(json.dumps(dataclasses.asdict(sp), indent=1))
    return sp


def transfer_health(camp: Campaign) -> dict:
    """site_g -> site_f -> evicted, on one small file, confirmed by the block map: the path works before anything is measured."""
    name = sorted(camp.s1_entries)[0]
    fid, size = camp.s1_entries[name]["fileId"], int(camp.s1_entries[name]["size"])
    t0 = time.time()
    tid = V.schedule_replication(camp.o, SITE_F, fid, camp.site_f_id)
    rep = V.wait_transfers(camp.o, SITE_F, [tid], timeout_s=600)
    camp.require_ended(rep, "health replication")
    placed = camp.confirm_placed({fid: [(0, size)]}, settle_s=120)
    tid2 = V.schedule_eviction(camp.o, SITE_F, fid, camp.site_f_id, holder_id=camp.site_g_id)
    ev = V.wait_transfers(camp.o, SITE_F, [tid2], timeout_s=600)
    camp.require_ended(ev, "health eviction")
    empty = None
    for _ in range(24):
        empty = V.holds_nothing(camp.o, SITE_F, camp.site_f_id, [fid])
        if empty["empty"]:
            break
        time.sleep(5)
    rec = camp.log("transfer_health", file=name, size=size, replication=rep, placed=placed["fully_placed"], eviction=ev,
                   evicted=bool(empty and empty["empty"]), seconds=round(time.time() - t0, 1))
    if not rec["placed"] or not rec["evicted"]:
        raise RuntimeError(f"site_g -> site_f transfer path is not healthy: {rec}; stopping (no restart without the operator)")
    return rec


def measure(camp: Campaign, recs: dict, truth, refs: dict, cfg, out: Path, s2_path: Path, *, instances,
            layouts=(S1, S2), layout_instances=None, done=frozenset()) -> None:
    """M+ on site_f and M cold on site_f interleaved in one window (science's condition on #12: it runs during the campaign, so a
    contended M+ is never compared with a quiet M cold). Per layout and instance: one of each, in an order that alternates,
    each from a confirmed-empty replica; then the whole layout, provisioned once and read by `layout_instances`.

    `done`: (instance, layout, step) of clean runs already made (`done_steps`; step is cold-site_f, mplus-required or mplus-layout). They are not
    repeated, so a probe's runs count as the campaign's M+ runs (science, #34, 01:03Z). `layout_instances=()` makes no layout scope at all;
    None reads it with `instances`."""
    for layout in layouts:
        for j, iid in enumerate(instances):
            rec = recs[iid]

            def cold() -> None:
                run_cold(camp, "cold-site_f", Plan(iid, Option.M, layout, tag=f"cold-site_f-p{j}"), rec, truth, cfg, out, refs[iid])

            def placed() -> None:
                ranges = s2_required_ranges(s2_path, rec) if layout == S2 else None
                camp.require_empty(layout)
                camp.provision(layout, rec, ranges)
                run_mplus(camp, "required", Plan(iid, Option.M_PLUS, layout, tag=f"mplus-required-p{j}"), rec, truth, cfg, out,
                          refs[iid], camp.wanted(layout, rec, ranges))

            for step, name in (((cold, "cold-site_f"), (placed, "mplus-required")) if j % 2 == 0 else ((placed, "mplus-required"), (cold, "cold-site_f"))):
                if (iid, layout.value, name) not in done:
                    step()
        wide = list(instances if layout_instances is None else layout_instances)
        left = [(j, iid) for j, iid in enumerate(wide) if (iid, layout.value, "mplus-layout") not in done]
        if not left:
            continue
        camp.require_empty(layout)
        camp.provision(layout, None, None)
        for j, iid in left:
            run_mplus(camp, "layout", Plan(iid, Option.M_PLUS, layout, tag=f"mplus-layout-p{j}"), recs[iid], truth, cfg, out, refs[iid],
                      camp.wanted(layout, None, None))


# ---- the quiet window's size (science, #34, 01:03Z) ----------------------------------------------------------------------------------------------
WINDOW_LIMIT_S = 4 * 3600      # all 30 runs if the projected window, the drain excluded, is at most this; else the first REDUCED_N instances per layout
REDUCED_N = 3
LAYOUT_CODE = {S1: 1, S2: 2}
ASSUMPTIONS = ("the layout scope's provisioning takes the required scope's measured time scaled by bytes (the layout's bytes over the bytes the probe placed)",
               "S2's required scope is read by ranges and its layout scope is one replication job, so the byte scaling is the roughest figure for S2",
               "a layout-scope M+ run takes as long as a required-scope M+ run",
               "every eviction takes the probe's mean eviction of that layout",
               "the drain (runs in flight finishing before the window opens) is not in it")


def seeded_order(instances, seed: int, layout: Layout) -> list[str]:
    """The instances in an order fixed by the seed and the layout alone (the listed order does not matter: the names are sorted first)."""
    ids = sorted(set(instances))
    rng = np.random.default_rng([int(seed), 0x4D50, LAYOUT_CODE[layout]])
    return [ids[int(k)] for k in rng.permutation(len(ids))]


def select_instances(instances, seed: int, layout: Layout, n: int | None) -> list[str]:
    """The first `n` of the seeded order (all of them for None): a probe is the first, a reduced window the first 3."""
    order = seeded_order(instances, seed, layout)
    return order if n is None else order[:n]


def done_steps(runs: list[dict]) -> set[tuple[str, str, str]]:
    """(instance, layout, step) of every clean M cold on site_f and M+ run: what a later window must not repeat."""
    out = set()
    for r in runs:
        if not r.get("ok"):
            continue
        variant = (r.get("extra") or {}).get("variant")
        if variant == "cold-site_f":
            out.add((r["instance_id"], r["layout"], "cold-site_f"))
        elif variant == "mplus":
            out.add((r["instance_id"], r["layout"], f"mplus-{r['extra'].get('scope')}"))
    return out


def step_times(log: list[dict], runs: list[dict]) -> dict[str, dict]:
    """Per layout, the means the window's projection uses, from the probe: an eviction, the required scope's provisioning (and the bytes it placed),
    M cold on site_f's wall and M+ required's wall. A step with no clean sample is None, and the projection refuses it."""
    mean = lambda xs: sum(xs) / len(xs) if xs else None      # noqa: E731
    out = {}
    for layout in ("S1", "S2"):
        ev = [e for e in log if e.get("event") == "evict" and e.get("layout") == layout and e.get("confirmed_empty") is True]
        pr = [e for e in log if e.get("event") == "provision" and e.get("layout") == layout and e.get("scope") == "required"
              and e.get("confirmed_placed") is True]

        def walls(variant, scope=None):
            return [r["wall_s"] for r in runs if r.get("ok") and r.get("layout") == layout and (r.get("extra") or {}).get("variant") == variant
                    and (scope is None or r["extra"].get("scope") == scope)]
        out[layout] = {"evict_s": mean([e["seconds"] for e in ev]), "provision_required_s": mean([e["seconds"] for e in pr]),
                       "placed_bytes_required": mean([e["placed_bytes"] for e in pr]),
                       "cold_site_f_wall_s": mean(walls("cold-site_f")), "mplus_required_wall_s": mean(walls("mplus", "required")),
                       "samples": {"evict": len(ev), "provision": len(pr), "cold_site_f": len(walls("cold-site_f")), "mplus_required": len(walls("mplus", "required"))}}
    return out


def project_window(steps: dict, layout_bytes: dict, chosen: dict[str, list[str]], done=frozenset()) -> dict:
    """Seconds the window takes for `chosen` (layout -> instances), the drain excluded, minus the steps in `done`. Per layout, per instance: M cold
    (an eviction and its wall), M+ required (an eviction, the provisioning, its wall); then once the layout scope (an eviction, the provisioning scaled
    by bytes, and one M+ wall per instance left). A step the probe did not measure is refused: no number from nothing."""
    per, total = {}, 0.0
    for layout, ids in chosen.items():
        st = steps[layout]
        missing = [k for k in ("evict_s", "provision_required_s", "placed_bytes_required", "cold_site_f_wall_s", "mplus_required_wall_s") if not st.get(k)]
        if missing:
            raise ValueError(f"{layout}: the probe measured no {missing}: the window cannot be projected")
        e, p, c, m = st["evict_s"], st["provision_required_s"], st["cold_site_f_wall_s"], st["mplus_required_wall_s"]
        s = 0.0
        for iid in ids:
            if (iid, layout, "cold-site_f") not in done:
                s += e + c
            if (iid, layout, "mplus-required") not in done:
                s += e + p + m
        left = [iid for iid in ids if (iid, layout, "mplus-layout") not in done]
        if left:
            s += e + p * layout_bytes[layout] / st["placed_bytes_required"] + len(left) * m
        per[layout] = {"instances": list(ids), "seconds": s}
        total += s
    return {"layouts": per, "seconds": total}


def plan_window(instances, seed: int, steps: dict, layout_bytes: dict, done=frozenset(), *, limit_s: float = WINDOW_LIMIT_S,
                reduced_n: int = REDUCED_N) -> dict:
    """Science's size rule, on duration alone: every instance of both layouts (30 runs) when the projected window is at most `limit_s`, else the first
    `reduced_n` of each layout's seeded order (18 runs for 3 of 5). The probe's runs are in `done` and count; the projection is of what is left."""
    order = {la.value: select_instances(instances, seed, la, None) for la in (S1, S2)}
    everything = project_window(steps, layout_bytes, order, done)
    keep = everything["seconds"] <= limit_s
    chosen = order if keep else {la: ids[:reduced_n] for la, ids in order.items()}
    now = everything if keep else project_window(steps, layout_bytes, chosen, done)
    return {"seed": seed, "limit_s": limit_s, "all_instances": keep, "instances": chosen, "seeded_order": order,
            "projected_all_s": everything["seconds"], "projected_chosen_s": now["seconds"], "per_layout": now["layouts"],
            "rule": (f"all {len(order['S1'])} instances per layout" if keep else f"the first {reduced_n} of {len(order['S1'])} instances per layout, in the seeded order")
                    + f"; projected {everything['seconds'] / 3600:.2f} h for all against a limit of {limit_s / 3600:g} h, the drain excluded",
            "assumptions": list(ASSUMPTIONS)}


ROWS = {"cold-site_f": "primary: M+ on site_f vs M cold on site_f, interleaved in one window (replica evicted, reads replicate on the fly from site_g)",
        "cold-site_g": "secondary, different conditions: M+ on site_f during the campaign vs M cold on site_g from the quiet baselines, the path the agent runs use",
        "cold-wan": "scripted bound: the same P and W, C from M's runs in the WAN anchor (site_c), no extra runs"}


WAN_NOTE = ("off-site rates varied more than 20x between measurements (science, #12, 21:02Z): the WAN figures are the link at the UTC "
            "time shown, not a property of it. Day-0 measured the site_c provider at 1.6-12.6 Mbit/s (about 02:07Z); the rate check "
            "and the S2 runs on 1 Nov measured 163-371 Mbit/s (20:00-20:40Z).")


def wan_figures(wan_runs: list[dict]) -> dict:
    """The WAN anchor's M runs behind the scripted bound, per layout, each with its UTC time (S1 and S2 both count)."""
    out: dict[str, list[dict]] = {"S1": [], "S2": []}
    for r in whole_cells(wan_runs):
        if r["option"] == "M" and r["layout"] in out:
            out[r["layout"]].append({"run_key": r["run_key"], "utc": r.get("exec_started_utc"), "ok": bool(r["ok"]),
                                     "wall_s": r.get("wall_s")})
    for rows in out.values():
        rows.sort(key=lambda x: x["utc"] or "")
    return out


def report(results_dir: Path, seed: int = 20271201, *, wan_dir: Path | None = None, site_g_dir: Path | None = None) -> dict:
    """The break-even per layout, scope and row (science, #12: primary, secondary, scripted WAN bound), in seconds,
    with a bootstrap interval; written next to the runs. A row without samples says what is missing."""
    from .breakeven import bootstrap_interval, json_safe
    from .summarize import load_runs
    log = [json.loads(x) for x in (results_dir / "mplus_log.jsonl").read_text().splitlines()]
    x = break_even_inputs(log, load_runs(results_dir), wan_runs=load_runs(wan_dir) if wan_dir else None,
                          site_g_runs=load_runs(site_g_dir) if site_g_dir else None)
    out: dict = {"inputs": x, "rows": ROWS, "break_even": {}, "seed": seed,
                 "wan_runs": wan_figures(load_runs(wan_dir)) if wan_dir else None, "wan_note": WAN_NOTE,
                 "labels": "client caches fresh per run; provider and storage page caches not controlled"}
    for layout, d in x.items():
        for scope in ("required", "layout"):
            for variant in ROWS:
                p, c, w = d["provision_s"][scope], d["wall_s"][variant], d["wall_s"][f"mplus-{scope}"]
                key = f"{layout}/{scope}/{variant}"
                out["break_even"][key] = (bootstrap_interval(p, c, w, seed=seed) if p and c and w
                                          else {"missing": {"provision": len(p), "cold": len(c), "mplus": len(w)}})
    (results_dir / "breakeven.json").write_text(json.dumps(json_safe(out), indent=1))
    return out
