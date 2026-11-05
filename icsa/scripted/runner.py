"""One scripted run: a fresh sandbox, the in-sandbox script, the counters around it, the comparison.

A failed run is recorded and reported; nothing here retries, because an error is a result (the cap rule needs it).
`DataConfig`s are built per run by the caller's `make_config`, so no token outlives its run.
"""
from __future__ import annotations

import dataclasses
import gzip
import json
import shutil
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np

from ..instances import load as L
from .. import frsettings as site_g_settings
from ..records import Layout, Option
from ..sandbox import DataConfig, Sandbox, SandboxConfig
from ..sandbox import hostops as H
from . import bundle, metrics, tokens
from .compare import FrozenTruth, compare_run, sha256_file
from .insandbox import RESULT_PREFIX

RUN_PREFIX = "s12-"                # container names icsa-sbx-s12-..., so this lane can only ever clean up its own
OWN_CONTAINERS = f"icsa-sbx-{RUN_PREFIX}"
OPTIONS_REST = (Option.T, Option.T_UNPAGINATED, Option.D)
MEM_ABORT_GIB = 8.0                # a run is stopped below this, ahead of earlyoom's SIGTERM (about 6.6 GiB on the run VM): the host went out of memory twice on 31 Oct
RESULT_MAX_EXEC_S = 6 * 3600


@dataclasses.dataclass
class Plan:
    """What one run is: which instance, through which path, in which batch."""
    instance_id: str
    option: Option
    layout: Layout
    tag: str = "pilot"             # pilot | curve-c<c>-r<rep> | wan | mplus-... | perf
    attempt: int = 1

    def key(self) -> str:
        opt = self.option.value.replace("+", "plus")
        return f"{RUN_PREFIX}{self.tag}-{self.instance_id}-{opt}-{self.layout.value}-a{self.attempt}"


def split_days(rec: dict) -> tuple[np.ndarray, np.ndarray]:
    """(required baseline days, target days) of a record, from #5's `required_day_indices` and target range."""
    all_days = L.required_day_indices(rec)
    from ..instances import required as R
    import datetime as dt
    a, b, _ = rec["target_days"]
    tgt = R.target_day_indices(dt.date.fromisoformat(a), dt.date.fromisoformat(b))
    base = np.setdiff1d(all_days, tgt)
    if base.size != rec["baseline_days"] or tgt.size != rec["target_days"][2] or base[-1] >= tgt[0]:
        raise ValueError(f"{rec['instance']['instance_id']}: days do not split into baseline and target")
    return base, tgt


def probe_days(base: np.ndarray, tgt: np.ndarray, n: int | None) -> list[int] | None:
    """The days a live probe reads (amendment 25(e), `icsa/scripted/liveprobe.py`): the first `n` of the cell's fixed order (the baseline days, then the target days, each
    ascending), so the same files for an instance on every run, in T and in M alike. Pure: no seed, no randomness. None (the whole cell) -> None. `n` must be a whole number
    from 1 to the cell's days."""
    if n is None:
        return None
    total = int(base.size) + int(tgt.size)
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= total:
        raise ValueError(f"probe files {n!r}: a whole number from 1 to the cell's {total} files, or none for the whole cell")
    return [int(x) for x in np.concatenate([base, tgt])[:n]]


class MemoryGuard:
    """Stops this run's sandbox when the host runs short of memory, or when `cancel` is set (a padding run of a mix);
    records the lowest value it saw."""

    def __init__(self, stop: Callable[[], None], floor_gib: float = MEM_ABORT_GIB, period_s: float = 5.0,
                 cancel: threading.Event | None = None):
        self.stop_sandbox, self.floor, self.period, self.cancel = stop, floor_gib, period_s, cancel
        self.tripped = self.cancelled = False
        self.min_available = metrics.meminfo_available_gib()
        self._done = threading.Event()
        self._t = threading.Thread(target=self._watch, daemon=True)

    def _watch(self) -> None:
        while not self._done.wait(self.period):
            now = metrics.meminfo_available_gib()
            self.min_available = min(self.min_available, now)
            if now < self.floor and not self.tripped:
                self.tripped = True
                self.stop_sandbox()
                return
            if self.cancel is not None and self.cancel.is_set():
                self.cancelled = True
                self.stop_sandbox()
                return

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._done.set()
        self._t.join(timeout=10)


def _parse_result(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.startswith(RESULT_PREFIX):
            return json.loads(line[len(RESULT_PREFIX):])
    return None


def run_one(plan: Plan, rec: dict, truth: FrozenTruth, make_config: Callable[[], DataConfig], sb_cfg: SandboxConfig,
            out_dir: Path, *, expected_sst: str | None = None, barrier: threading.Barrier | None = None,
            timeout_s: float = 2 * 3600, trace_http: bool = False, perf: bool = False,
            extra: dict | None = None, cancel: threading.Event | None = None, keep_trace: bool = False, read_files: int | None = None) -> dict:
    """Run `plan` and write `<out_dir>/<key>/run.json`. The record is returned whatever happened. `keep_trace` leaves the run's trace/ and
    cells/ in its directory, for a caller that labels the run (tools/host_equivalence.py); the default removes them, as every batch does.

    `read_files` (the live probe and its baseline cell, amendment 25(e)): read only the first n files of the cell's fixed order (`probe_days`), timed as for the whole cell, and
    compute and score nothing. The record carries the count as `extra.probe_files`; a record without it is a whole cell. None (every other caller): the run as it always was."""
    out = Path(out_dir) / plan.key()
    out.mkdir(parents=True, exist_ok=False)
    base, tgt = split_days(rec)
    read_days = probe_days(base, tgt, read_files)
    spec = bundle.spec_for(rec, plan.option.value, plan.layout.value, base, tgt, trace_http=trace_http, read_days=read_days)
    code = bundle.pipeline_code(spec)
    r: dict = {"run_key": plan.key(), "tag": plan.tag, "attempt": plan.attempt, "instance_id": plan.instance_id,
               "option": plan.option.value, "layout": plan.layout.value,
               # whether it is traced is read from the configuration it runs under, not from what the caller says
               "extra": {**(extra or {}), "traced": bool(sb_cfg.instruments_dir), **({} if read_files is None else {"probe_files": read_files})},
               "host_aliases": dict(sorted(sb_cfg.host_aliases.items())),      # also when the lease or the start fails
               "host": H.host_facts(),
               "refdet_source_sha256": bundle.source_sha256(), "truth_cell_masks_sha256": truth.sha256,
               "site_g_settings_sha256": site_g_settings.hash_for_record(),
               "host_before": metrics.host_state(sb_cfg.work_root, OWN_CONTAINERS), "ok": False, "errors": []}
    t_begin = time.monotonic()

    def finalize() -> None:
        r["total_s"] = round(time.monotonic() - t_begin, 3)
        r["host_after"] = metrics.host_state(sb_cfg.work_root, OWN_CONTAINERS)
        (out / "run.json").write_text(json.dumps(r, indent=1, default=str))

    return tokens.leased(plan.key(), plan.option.value, r,
                         lambda: _run_leased(plan, rec, truth, make_config, sb_cfg, out, r, spec, code, t_begin, barrier=barrier,
                                             expected_sst=expected_sst, timeout_s=timeout_s, trace_http=trace_http, perf=perf,
                                             cancel=cancel, keep_trace=keep_trace),
                         finalize, on_no_lease=(barrier.abort if barrier is not None else None))


def _collect(sbx, out: Path, r: dict) -> dict:
    """It stops what the script left running first, so nothing goes on changing its outputs while they are read. Failed: host infrastructure, not this run's result: retried, the disks kept."""
    try:
        return sbx.collect(out)
    except H.SandboxError:
        r.setdefault("infrastructure", "collect")
        raise


def _note_records(r: dict, meta: dict, rest: bool) -> None:
    """As for an agent run: a missing or failed record is not a result. A traced run must show that it was traced, cell by cell, and a REST run's gate log must stand for the whole
    run; otherwise a request count defaults to zero. Retried."""
    from ..harness.runner import _instrument_problem, _record_problem
    from ..sandbox.infradeath import OWN_LIMIT_AGENT
    problem = _record_problem(meta, rest)
    if problem:
        if not any(problem in e for e in r["errors"]):
            r["errors"].append(problem)
        r.setdefault("infrastructure", "instrument" if _instrument_problem(meta) else "record")
        r["ok"] = False
    # Only an agent can own a sidecar's own-limit kill (amendment 24). With no agent, a script's sidecar at its limit means the limit is wrong for the
    # measurement: a failed run, an infrastructure failure of the curve or the baseline (the lead, 2 Nov)
    own = [d for d in meta.get("container_deaths") or [] if isinstance(d, dict) and d.get("cause") == OWN_LIMIT_AGENT]
    if own:
        r["errors"].append("the sidecar reached its own memory limit in a scripted run, which has no agent to own it: " + "; ".join(str(d.get("basis")) for d in own))
        r.setdefault("infrastructure", "record")
        r["ok"] = False


def _note_earlyoom(r: dict, meta: dict) -> None:
    """Host infrastructure, never this run's result, whatever the script managed to report. The normal end and the `finally` both call it, and a kill found by the later
    read counts even if the earlier one could not read the journal. Anything it notes makes the run not clean, also after `ok` was set."""
    if r.get("infrastructure") == "earlyoom":
        return
    if meta.get("earlyoom_kills"):            # before any other infrastructure cause: killcause.PRECEDENCE
        r["errors"].append(f"earlyoom killed {len(meta['earlyoom_kills'])} process(es) of this run")
        r["infrastructure"], r["ok"] = "earlyoom", False
    elif meta.get("earlyoom_unsampled_kills_of_this_uid"):     # born and killed between two samples: it may have been this run's, and nothing tells
        r["errors"].append(f"earlyoom killed {len(meta['earlyoom_unsampled_kills_of_this_uid'])} process(es) of the agents' uid that no sandbox here ever saw")
        r["infrastructure"], r["ok"] = "earlyoom", False
    elif meta.get("earlyoom_log_readable") is False:
        if not any("journal could not be read" in e for e in r["errors"]):
            r["errors"].append("earlyoom's journal could not be read: whether this run was hit is not known")
        r.setdefault("infrastructure", "earlyoom_journal")       # not known is not this run's result: retried
        r["ok"] = False


def _run_leased(plan, rec, truth, make_config, sb_cfg, out, r, spec, code, t_begin, *, barrier, expected_sst, timeout_s,
                trace_http, perf, cancel, keep_trace=False) -> dict:
    sbx = None
    try:
        sbx = Sandbox.start(plan.key(), plan.option, plan.layout, make_config(), sb_cfg)
        r["sandbox_start_s"] = round(time.monotonic() - t_begin, 3)
        gate, side = f"{sbx.name}-gate", f"{sbx.name}-oneclient"
        # a oneclient sidecar exists only with the real mount; the local tests bind a plain directory instead
        mount = sbx.metadata().get("mount_kind") == "oneclient"
        roles = {"agent": sbx.name, "gate": gate, **({"sidecar": side} if mount else {})}
        cg0 = {role: metrics.cgroup(c) for role, c in roles.items()}
        c0 = {"agent": metrics.iface_counters(sbx.name), "gate": metrics.iface_counters(gate)}
        if mount:
            c0["sidecar"] = metrics.iface_counters(side)
        up_mac = metrics.bridge_mac(gate)
        side_mac = metrics.bridge_mac(side) if mount else None
        nic0 = metrics.nic_rx()
        if barrier is not None:
            barrier.wait(timeout=1800)     # every sandbox of a level is up before any of them reads
        r["exec_started_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with MemoryGuard(sbx.stop, cancel=cancel) as guard:
            ex = sbx.exec(code, timeout_s)
        r.update(wall_s=round(ex.duration_s, 3), exit_code=ex.exit_code, timed_out=ex.timed_out,
                 mem_available_min_gib=round(guard.min_available, 1), stopped_for_memory=guard.tripped)
        if guard.tripped:
            r["errors"].append(f"stopped: host MemAvailable below {MEM_ABORT_GIB} GiB")
        if guard.cancelled:
            r["errors"].append("cancelled: the level's counted runs had finished")
            return r
        result = _parse_result(ex.stdout)
        if result is None or ex.exit_code != 0:
            r["errors"].append(f"script failed: exit {ex.exit_code}; stderr tail: {ex.stderr[-1500:]}")
        # per run, per container (science, #9); "no OOM kill" is part of the cap rule's "no errors", and an unreadable
        # counter is unknown: an unknown does not pass, so the run is not clean until each container is known to have none
        r["containers"] = metrics.container_stats(cg0, {role: metrics.cgroup(c) for role, c in roles.items()})
        r["oom_kills"] = {role: st["oom_kills"] for role, st in r["containers"].items()}
        hit = {k: v for k, v in r["oom_kills"].items() if v}
        if hit:
            r["errors"].append(f"OOM kill: {hit}")
        unknown = sorted(k for k, v in r["oom_kills"].items() if v is None)
        if unknown:
            r["errors"].append(f"OOM state unknown: {unknown}")
        if guard.tripped:
            return r
        c1 = {"agent": metrics.iface_counters(sbx.name), "gate": metrics.iface_counters(gate)}
        if mount:
            c1["sidecar"] = metrics.iface_counters(side)
        nic1 = metrics.nic_rx()
        gate_up = metrics.delta(metrics.iface_by_mac(c1["gate"], up_mac), metrics.iface_by_mac(c0["gate"], up_mac))
        by = {"agent_eth0": metrics.delta(c1["agent"]["eth0"], c0["agent"]["eth0"]), "gate_upstream": gate_up,
              "host_ens3_rx_delta": None if nic0 is None or nic1 is None else nic1 - nic0}
        if mount:
            by["sidecar_bridge"] = metrics.delta(metrics.iface_by_mac(c1["sidecar"], side_mac),
                                                 metrics.iface_by_mac(c0["sidecar"], side_mac))
            by["sidecar_bridge_total_since_mount"] = metrics.iface_by_mac(c1["sidecar"], side_mac)["rx"]
            by["between_sites_rx"] = by["sidecar_bridge"]["rx"]
        elif plan.option in OPTIONS_REST:
            by["between_sites_rx"] = gate_up["rx"]
        else:
            by["between_sites_rx"] = None     # no real mount, no sites: a local test, never a measurement
        r["bytes"] = by
        got = _collect(sbx, out, r)      # with DataConfig.oneclient_perf_log, #7 copies the sidecar's CSV to oneclient_perf/
        if perf:
            csvs = sorted((out / "oneclient_perf").glob("read_write_perf-*.csv"))
            if not csvs:
                r["errors"].append("perf log requested but no read_write_perf CSV was collected")
            text = "".join(c.read_text() for c in csvs)
            r["oneclient_perf"] = metrics.parse_perf_csv(text)
            with gzip.open(out / "read_write_perf.csv.gz", "wt") as f:
                f.write(text)
            shutil.rmtree(out / "oneclient_perf", ignore_errors=True)
        r["collected"] = got
        meta = sbx.metadata()
        r["sandbox"] = meta
        _note_earlyoom(r, meta)
        gl = out / "gate_requests.jsonl"
        if gl.exists():
            lines = gl.read_text().splitlines()
            r["gate_requests"] = metrics.summarize_gate_requests(lines)
            r["client_requests"] = r["gate_requests"]["requests"]
            with gzip.open(out / "gate_requests.jsonl.gz", "wt") as f:
                f.write("\n".join(lines) + "\n")
            gl.unlink()
        if not keep_trace:
            shutil.rmtree(out / "cells", ignore_errors=True)   # the script is identical for all runs: kept once, by sha
        tr = out / "trace"
        r["trace_bytes"] = sum(f.stat().st_size for f in tr.rglob("*") if f.is_file()) if tr.is_dir() else 0
        err = tr / "instrument-error.log"
        if r["extra"]["traced"]:            # sitecustomize swallows an import failure: a traced run must prove it was traced
            if err.exists():
                r["errors"].append(f"the tracer did not start: {err.read_text()[-500:]}")
                r.setdefault("infrastructure", "instrument")
            elif not r["trace_bytes"]:
                r["errors"].append("traced, but the tracer wrote nothing")
                r.setdefault("infrastructure", "instrument")
        if not keep_trace:
            shutil.rmtree(tr, ignore_errors=True)
        r["code_sha256"] = __import__("hashlib").sha256(code.encode()).hexdigest()
        if result is not None and spec.get("read_days") is not None:
            r["script"] = result              # a probe's prefix read: not scored, there is no output to compare; but the count on record must be the count read
            if not result.get("read_only") or result.get("days_read") != len(spec["read_days"]):
                r["errors"].append(f"a prefix read of {len(spec['read_days'])} files came back as read_only={result.get('read_only')!r}, days_read={result.get('days_read')!r}")
        elif result is not None:
            r["script"] = result
            report = out / "output" / "report.json"
            mask = out / "output" / "mhw_mask.nc"
            if report.exists() and mask.exists():
                r["mask_sha256"] = sha256_file(mask)
                r["compare"] = compare_run(truth, plan.instance_id, mask, json.loads(report.read_text()), result,
                                           expected_sst)
                if not r["compare"]["equal"]:
                    r["errors"].append("result differs from the ground truth")
            else:
                r["errors"].append(f"outputs missing: {got}")
        non_2xx = (r.get("gate_requests") or {}).get("non_2xx", 0)
        r["ok"] = not r["errors"] and non_2xx == 0
        if non_2xx:
            r["errors"].append(f"{non_2xx} requests with a non-2xx status at the gate")
    except H.SandboxError as e:          # Docker failed, or the mount never appeared: host infrastructure, not this run's result, so it is retried and no baseline counts it
        r["errors"].append(f"sandbox: {e}")
        r.setdefault("infrastructure", "sandbox")
    except threading.BrokenBarrierError:
        r["errors"].append("barrier broken: another sandbox of this level did not start")
    except Exception as e:  # noqa: BLE001 - a failed run is a result; the batch goes on
        r["errors"].append(f"{type(e).__name__}: {e}"[:1500])
    finally:
        if barrier is not None and sbx is None:
            barrier.abort()                # a sandbox that never started must not block the others
        if sbx is not None:
            try:                           # also when a victim stopped the run before the record's normal end: the gate or oneclient gone, the counters unreadable
                meta = sbx.metadata()
                _note_earlyoom(r, meta)
                if not getattr(sbx, "_stopped", False):       # stopped for memory or cancelled: its containers and logs are gone, which says nothing about its records
                    _note_records(r, meta, plan.option in OPTIONS_REST)
            except Exception as e:  # noqa: BLE001
                r["errors"].append(f"earlyoom state not read: {type(e).__name__}: {e}"[:300])
                r["ok"] = False
            sbx.stop()
        r["total_s"] = round(time.monotonic() - t_begin, 3)
        (r.get("token") or {})["end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        r["host_after"] = metrics.host_state(sb_cfg.work_root, OWN_CONTAINERS)
        (out / "run.json").write_text(json.dumps(r, indent=1, default=str))
    return r


def cleanup_own_containers() -> list[str]:
    """Remove leftovers of THIS lane only (name prefix), e.g. after a killed batch."""
    names = H.docker("ps", "-a", "--format", "{{.Names}}", check=False).stdout.split()
    mine = [n for n in names if n.startswith(OWN_CONTAINERS)]
    # an M sandbox's sidecar first, in order (readers, unmount, sidecar, agent); one whose FUSE mount could not be released
    # is left running rather than SIGKILLed with the mount live
    from icsa.sandbox import teardown
    held = teardown.fuse_first(mine)
    for n in mine:
        if n not in held:
            H.docker("rm", "-f", n, check=False)
    return mine
