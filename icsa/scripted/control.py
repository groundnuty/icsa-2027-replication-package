"""Enforcement overhead (science, #7/#12): the same scripted run with and without the enforcement around it.

What enforces each option, and what the control removes:
  T, T-unpaginated, D   the gate (policy, TLS termination, D's store-and-forward, T-unpaginated's merge) and the
                        sandbox container. Control: the same image, script and spec in a plain container on docker's
                        bridge, talking to the provider directly, with the same --cpus and --memory. T-unpaginated has
                        no control of its own: without the gate it IS T (the merge lives in the gate), which is stated.
  M                     the sandbox around the reader: read-only root, no capabilities, internal network, quota disk,
                        the mount reaching it by bind propagation. Control: the same oneclient sidecar mount (started
                        by a sandbox of the same run), read by a plain container with the same --cpus and --memory.
The script, the spec, the comparison with the frozen truth and the record are those of `runner.run_one`, and the tracer, when
the batch is traced, sits in the same slot; bytes come from the control container's own eth0 (REST) or the sidecar's bridge
interface (M), as in the sandboxed runs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .. import frsettings as site_g_settings
from ..records import Option
from ..sandbox import Sandbox, SandboxConfig
from ..sandbox import earlyoom as EO
from ..sandbox import hostops as H
from ..sandbox.config import AGENT_OOM_SCORE_ADJ, dataset_location, host_alias_args, study_env
from ..sandbox.forwarder import ProviderForwarder, redirected_alias_args
from ..sandbox.route import TRAEFIK_PORT, path_name
from . import bundle, metrics, tokens
from .compare import FrozenTruth, compare_run, sha256_file
from .runner import OWN_CONTAINERS, Plan, _parse_result, split_days

CERT = "/usr/local/lib/python3.12/site-packages/certifi/cacert.pem"
COUNTER = "/sys/class/net/eth0/statistics/rx_bytes"
_BEFORE = f"""
_rx0 = int(open({COUNTER!r}).read())
def _cg():
    import json as _j
    out = {{}}
    for name in ("cpu.stat", "memory.peak", "memory.events"):
        try:
            out[name] = open("/sys/fs/cgroup/" + name).read()
        except OSError:
            out[name] = ""
    return out
_cg0 = _cg()
"""
_AFTER = f"""
import json as _j, pathlib as _p
_trace = [f for f in _p.Path("/trace").rglob("*") if f.is_file()] if _p.Path("/trace").is_dir() else []
_err = _p.Path("/trace/instrument-error.log")
print("ICSA_CONTROL_STATS " + _j.dumps({{"rx": int(open({COUNTER!r}).read()) - _rx0, "cg0": _cg0, "cg1": _cg(),
      "trace_bytes": sum(f.stat().st_size for f in _trace), "instrument_error": _err.read_text()[-500:] if _err.exists() else None,
      "tracer_marker": _p.Path(f"/trace/ok.{{__import__('os').getpid()}}").exists()}}), flush=True)
"""


def control_env_args(dc, plan: Plan) -> list[str]:
    """The study's environment, as the enforced arm's (config.study_env). Without it the tracer hashed M's dataset file through the mount: 3.8 GB and 69 s more than its enforced twin."""
    return [x for k, v in study_env(dc, plan.option, plan.layout).items() for x in ("-e", f"{k}={v}")]


def _start_control(args: list[str], image: str, env: dict) -> None:
    """The container on its own, as the enforced arm's: an init and a `sleep`, with the script started in it afterwards, so its start and removal are in neither arm's wall time."""
    p = subprocess.run(["docker", *args, image, "sleep", "infinity"], env=env, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise H.SandboxError(f"the control container did not start: {p.stderr.strip()[:300]}")


def _exec_control(name: str, code: str, env: dict, timeout_s: float) -> tuple[subprocess.CompletedProcess, float]:
    """The script and the time it took: the same window as `Sandbox.exec` measures, a `docker exec` from its launch to its end."""
    t1 = time.monotonic()
    p = subprocess.run(["docker", "exec", "-i", name, "python", "-"], input=code, env=env, capture_output=True, text=True, timeout=timeout_s)
    return p, round(time.monotonic() - t1, 3)


def _traced_problem(st: dict) -> str | None:
    """Why a traced control's statistics cannot show that it was traced. The tracer removes its marker when a write fails, so bytes on disk alone are no proof."""
    if not st:
        return "traced, and the run left no statistics to show it"
    if st.get("instrument_error"):
        return f"the tracer did not start: {st['instrument_error']}"
    if not st.get("trace_bytes"):
        return "traced, but the tracer wrote nothing"
    if not st.get("tracer_marker"):
        return "traced, but the tracer's marker is gone: a write of its failed"
    return None


def _remove_control(name: str, key: str, r: dict) -> None:
    """A control dials the providers itself with the run's token: one that may still be running keeps its slot user from the next run (Astra's Sandbox #5). Gone already is fine."""
    from ..sandbox.sandbox import _note_up, note_unfinished

    def again(p=None):
        p = p or H.docker("rm", "-f", name, check=False)
        if p.returncode != 0 and "no such container" not in (p.stderr or "").lower():
            raise H.SandboxError(f"the control container could not be removed: {(p.stderr or '').strip()[:200]}")

    def later():
        again()
        _note_up(key, -1)
    try:
        again(H.docker("rm", "-f", name, check=False))
    except H.SandboxError as e:
        r["errors"].append(str(e))
        r["ok"] = False
        _note_up(key, +1)
        note_unfinished(key, later)


def _stats(stdout: str) -> dict | None:
    for line in stdout.splitlines():
        if line.startswith("ICSA_CONTROL_STATS "):
            return json.loads(line[len("ICSA_CONTROL_STATS "):])
    return None


def _cg_parse(d: dict) -> dict:
    return metrics.parse_cgroup("\n".join(d.get(n, "") for n in ("cpu.stat", "memory.peak", "memory.events")))


def run_control(plan: Plan, rec: dict, truth: FrozenTruth, make_config, cfg: SandboxConfig, out_dir: Path, *,
                expected_sst: str | None, timeout_s: float = 2 * 3600, extra: dict | None = None) -> dict:
    """One control run, under the same token lease as an enforced run (so a slot source mints its tokens too, and the record
    carries the interval); writes `<out_dir>/<key>/run.json` with `extra.variant = "no-enforcement"`."""
    out = Path(out_dir) / plan.key()
    out.mkdir(parents=True, exist_ok=False)
    box: dict = {}
    t0 = time.monotonic()
    head = {"run_key": plan.key(), "tag": plan.tag, "attempt": plan.attempt, "instance_id": plan.instance_id,
            "option": plan.option.value, "layout": plan.layout.value,
            "extra": {"variant": "no-enforcement", **(extra or {}), "traced": bool(cfg.instruments_dir)},
            "host_aliases": dict(sorted(cfg.host_aliases.items())), "host": H.host_facts(), "ok": False, "errors": []}

    def body() -> None:
        box.update(_run_control(plan, rec, truth, make_config, cfg, out, expected_sst=expected_sst, timeout_s=timeout_s, extra=extra))

    def finalize() -> None:
        if box:                                  # the control wrote its record: add the lease's part, and the verdict of the lease
            box.setdefault("errors", [])
            box["errors"] += [e for e in head["errors"] if e not in box["errors"]]
            box["ok"] = bool(box["ok"]) and not head["errors"]
            box["token"] = head.get("token")
            r = box
        else:
            head["total_s"] = round(time.monotonic() - t0, 3)
            r = head
        (out / "run.json").write_text(json.dumps(r, indent=1, default=str))

    tokens.leased(plan.key(), plan.option.value, head, body, finalize)
    return box or head


def control_resource_args(lim) -> list[str]:
    """The agent container's resource flags (icsa/sandbox/sandbox.py, the agent container's `docker run`): memory = the
    agent's allowance + the tracer's headroom (also the swap limit, so no swap), cpus, pids, open files and /tmp, so the
    control arm differs from the enforced arm by the enforcement only. `container_memory_bytes` refuses an unset headroom."""
    mem = str(lim.container_memory_bytes)
    return ["--oom-score-adj", str(AGENT_OOM_SCORE_ADJ), "--cpus", str(lim.cpus), "--memory", mem, "--memory-swap", mem, "--pids-limit", str(lim.pids),
            "--ulimit", f"nofile={lim.nofile}:{lim.nofile}", "--tmpfs", f"/tmp:size={lim.tmp_bytes},mode=1777",
            "--shm-size", str(lim.shm_bytes)]


class _ControlPids(threading.Thread):
    """The host PIDs of the control's container, once a second: it runs outside `Sandbox.exec`, and earlyoom's log names a PID that has gone by the time anyone reads it."""

    def __init__(self, name: str):
        super().__init__(daemon=True, name=f"pids-{name}"[:40])
        self.container, self.seen, self._stop_event, self._dir = name, {}, threading.Event(), None

    def run(self) -> None:
        while not self._stop_event.wait(1.0):
            try:
                if self._dir is None:
                    cid = H.docker("inspect", "-f", "{{.Id}}", self.container, check=False).stdout.strip()
                    d = Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope")
                    self._dir = d if cid and d.is_dir() else None
                if self._dir is not None:
                    EO.note_pids(self.seen, (self._dir / "cgroup.procs").read_text(), time.time())
            except (OSError, ValueError, H.SandboxError):
                pass                   # gone, or not yet there: what was seen stays

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *a):
        self._stop_event.set()
        self.join(5)


def _earlyoom_of_control(r: dict, seen: dict, sbx, since: float) -> None:
    """As for an enforced run: a kill of this run's container, or of its sidecar, is host infrastructure, whatever the exit code. Not known is not clean."""
    kills = EO.read_kills(since)
    found = EO.attribute(kills or [], {"control": seen})
    if sbx is not None:
        meta = sbx.metadata()
        found += meta.get("earlyoom_kills") or []
        if meta.get("earlyoom_log_readable") is False:
            kills = None
    if found:
        r["earlyoom_kills"], r["infrastructure"] = found, "earlyoom"
        r["errors"].append(f"earlyoom killed {len(found)} process(es) of this run")
    elif kills is None:
        r["errors"].append("earlyoom's journal could not be read: whether this run was hit is not known")
        r.setdefault("infrastructure", "earlyoom_journal")       # not known is not this run's result: retried


def control_route(dc, mount: bool) -> tuple[list[str], int, bool]:
    """(provider hosts, the config's provider port, whether a forwarder is needed): T, T-unpaginated and D controls dial the provider
    themselves, so a route other than 443 needs the forwarder; M and M+ go through the sandbox's oneclient (-P)."""
    phosts = list(getattr(dc, "provider_hosts", None) or [])
    port = int((getattr(dc, "upstream", None) or {}).get(phosts[0], {}).get("port", TRAEFIK_PORT)) if phosts else TRAEFIK_PORT
    return phosts, port, (not mount) and port != TRAEFIK_PORT


def _run_control(plan: Plan, rec: dict, truth: FrozenTruth, make_config, cfg: SandboxConfig, out: Path, *,
                 expected_sst: str | None, timeout_s: float = 2 * 3600, extra: dict | None = None) -> dict:
    work = Path(cfg.work_root) / f"{plan.key()}-{os.getpid()}-control"
    work.mkdir(parents=True)
    os.chmod(work, 0o777)
    base, tgt = split_days(rec)
    dc = make_config()
    rel = (dc.s1_path if plan.layout.value == "S1" else dc.s2_path).strip("/")
    mount = plan.option in (Option.M, Option.M_PLUS)
    r: dict = {"run_key": plan.key(), "tag": plan.tag, "attempt": plan.attempt, "instance_id": plan.instance_id,
               "option": plan.option.value, "layout": plan.layout.value,
               "extra": {"variant": "no-enforcement", **(extra or {}), "traced": bool(cfg.instruments_dir)},
               "refdet_source_sha256": bundle.source_sha256(),
               "truth_cell_masks_sha256": truth.sha256, "site_g_settings_sha256": site_g_settings.hash_for_record(), "host_before": metrics.host_state(cfg.work_root, OWN_CONTAINERS),
               "ok": False, "errors": []}
    name = f"{OWN_CONTAINERS}{plan.key()}-control"[:120]
    lim = cfg.limits
    # no gate in this arm: the container dials the providers itself, by name, so it needs the host's LAN aliases as the gate does
    r["host_aliases"], r["host"] = dict(sorted(cfg.host_aliases.items())), H.host_facts()
    # T, T-unpaginated, D: no gate to carry a port, so when the route is not 443 a forwarder on the bridge relays 443 to it and the
    # container's /etc/hosts points the provider's NAME at the forwarder (the client and its TLS name check are unchanged).
    # M's sandbox (oneclient -P) records its own route.
    phosts, route_port, forward = control_route(dc, mount)
    if not mount:
        r["provider_route"] = {"hosts": phosts, "port": route_port, "path": path_name(route_port), "via": "forwarder" if forward else None}
    args = ["run", "-d", "--init", "--name", name, "--network", "bridge", *([] if forward else host_alias_args(cfg.host_aliases)), *control_resource_args(lim),
            "--tmpfs", f"/trace:size={lim.trace_bytes}", "-v", f"{work}:/work", *control_env_args(dc, plan)]
    if cfg.instruments_dir:     # the same tracer in the same slot as the enforced arm, so the arms differ by the enforcement
        args += ["-v", f"{Path(cfg.instruments_dir).resolve()}:/opt/icsa/instruments:ro",
                 "-e", "PYTHONPATH=/opt/icsa/instruments:/opt/icsa/hooks", "-e", f"ICSA_INSTRUMENT_MODULE={cfg.instrument_module}"]
    sbx, fwd = None, None
    t0 = time.monotonic()
    try:
        if mount:
            sbx = Sandbox.start(plan.key(), Option.M, plan.layout, dc, cfg)    # starts the sidecar and its mount
            sbx.extra_reader_containers = [name]                               # this container binds the mount: stopped first, by any path that stops the sandbox
            if sbx.metadata().get("mount_kind") != "oneclient":
                raise H.SandboxError("the M control needs the real oneclient mount")
            side = f"{sbx.name}-oneclient"
            side_mac = metrics.bridge_mac(side)
            c0 = metrics.iface_by_mac(metrics.iface_counters(side), side_mac)
            side_cg0 = metrics.cgroup(side)
            r["provider_route"] = sbx.metadata().get("provider_route")
            location = dataset_location(dc, plan.option, plan.layout)
            args += ["--mount", f"type=bind,src={sbx.dir / 'mount'},dst={dc.mount_path},readonly,bind-propagation=rslave"]
            env = dict(os.environ)
        else:
            if forward:
                fwd = ProviderForwarder(cfg.pinned_image_id or cfg.image, f"{name}-fwd"[:120], phosts[0], route_port, cfg.host_aliases)
                r["provider_route"]["forwarder_ip"] = fwd.start()
                args += redirected_alias_args(cfg.host_aliases, phosts, fwd.ip)
            location = dataset_location(dc, plan.option, plan.layout)
            env = dict(os.environ, ONEDATA_TOKEN=dc.token, ONEDATA_ONEZONE_HOST=dc.onezone_host)
            args += ["-e", "ONEDATA_TOKEN", "-e", "ONEDATA_ONEZONE_HOST", "-e", "ONEDATA_VERIFY_SSL=true",
                     "-e", f"SSL_CERT_FILE={CERT}", "-e", f"REQUESTS_CA_BUNDLE={CERT}"]
        spec = bundle.spec_for(rec, plan.option.value, plan.layout.value, base, tgt, location=location)
        code = bundle.pipeline_code(spec, before=_BEFORE, after=_AFTER)
        t_start = time.monotonic()
        _start_control(args, cfg.pinned_image_id or cfg.image, env)
        r["control_start_s"] = round(time.monotonic() - t_start, 3)
        wall0 = time.time()
        with _ControlPids(name) as pids:
            p, r["wall_s"] = _exec_control(name, code, env, timeout_s + 60)
        r["exit_code"] = p.returncode
        _earlyoom_of_control(r, pids.seen, sbx, wall0)
        result = _parse_result(p.stdout)
        if result is None or p.returncode != 0:
            r["errors"].append(f"script failed: exit {p.returncode}; stderr tail: {p.stderr[-1500:]}")
        st = _stats(p.stdout) or {}
        rx = st.get("rx")
        r["containers"] = metrics.container_stats({"agent": _cg_parse(st.get("cg0") or {})}, {"agent": _cg_parse(st.get("cg1") or {})})
        if mount:
            c1 = metrics.iface_by_mac(metrics.iface_counters(side), side_mac)
            r["bytes"] = {"sidecar_bridge": metrics.delta(c1, c0), "between_sites_rx": c1["rx"] - c0["rx"], "control_eth0_rx": rx}
            r["containers"].update(metrics.container_stats({"sidecar": side_cg0}, {"sidecar": metrics.cgroup(side)}))
        else:
            r["bytes"] = {"control_eth0_rx": rx, "between_sites_rx": rx}
        r["oom_kills"] = {role: c["oom_kills"] for role, c in r["containers"].items()}
        hit = {k: v for k, v in r["oom_kills"].items() if v}
        if hit:
            r["errors"].append(f"OOM kill: {hit}")
        r["trace_bytes"] = st.get("trace_bytes")
        if r["extra"]["traced"]:      # as in the enforced arm: a traced run must prove it was traced, and no statistics prove nothing
            why = _traced_problem(st)
            if why:
                r["errors"].append(why)
                r.setdefault("infrastructure", "instrument")
        if result is not None:
            r["script"] = result
            report, mask = work / "output" / "report.json", work / "output" / "mhw_mask.nc"
            if report.exists() and mask.exists():
                r["mask_sha256"] = sha256_file(mask)
                r["compare"] = compare_run(truth, plan.instance_id, mask, json.loads(report.read_text()), result, expected_sst)
                if not r["compare"]["equal"]:
                    r["errors"].append("result differs from the ground truth")
            else:
                r["errors"].append("outputs missing")
        r["ok"] = not r["errors"]
    except H.SandboxError as e:          # Docker failed, or the mount never appeared: host infrastructure, not this run's result
        r["errors"].append(f"sandbox: {e}"[:1500])
        r.setdefault("infrastructure", "sandbox")
    except Exception as e:  # noqa: BLE001 - a failed run is a result
        r["errors"].append(f"{type(e).__name__}: {e}"[:1500])
    finally:
        if sbx is not None:
            sbx.stop()                 # the ordered teardown: this container, the unmount, the sidecar, the agent
        if fwd is not None:
            fwd.stop()
        _remove_control(name, plan.key(), r)
        H.sudo("rm", "-rf", "--one-file-system", str(work), check=False)
        r["total_s"] = round(time.monotonic() - t0, 3)
        r["host_after"] = metrics.host_state(cfg.work_root, OWN_CONTAINERS)
        (out / "run.json").write_text(json.dumps(r, indent=1, default=str))
    return r


def _median_diff_interval(a: list[float], b: list[float], *, seed: int, n_boot: int = 10000, level: float = 0.95) -> tuple[float, float]:
    """Seeded percentile bootstrap of median(a) - median(b), resampling each arm independently."""
    import numpy as np
    rng = np.random.default_rng(seed)
    x, y = np.asarray(a, float), np.asarray(b, float)
    d = (np.median(x[rng.integers(0, x.size, size=(n_boot, x.size))], axis=1)
         - np.median(y[rng.integers(0, y.size, size=(n_boot, y.size))], axis=1))
    lo, hi = np.quantile(d, [(1 - level) / 2, (1 + level) / 2])
    return float(lo), float(hi)


def _arms(runs: list[dict], key) -> dict[tuple[str, str], dict[str, list[float]]]:
    cells: dict[tuple[str, str], dict[str, list[float]]] = {}
    for r in runs:
        if r["ok"]:
            cells.setdefault((r["option"], r["layout"]), {}).setdefault(key(r), []).append(r["wall_s"])
    return cells


def overhead_table(runs: list[dict]) -> list[dict]:
    """Per option x layout: median wall time enforced and without enforcement, their difference and ratio."""
    import statistics
    out = []
    for (o, la), d in sorted(_arms(runs, lambda r: r["extra"].get("variant", "enforced")).items()):
        enf, ctl = d.get("enforced", []), d.get("no-enforcement", [])
        row = {"option": o, "layout": la, "k_enforced": len(enf), "k_control": len(ctl),
               "enforced_median_s": round(statistics.median(enf), 2) if enf else None,
               "control_median_s": round(statistics.median(ctl), 2) if ctl else None}
        if enf and ctl:
            row["overhead_s"] = round(row["enforced_median_s"] - row["control_median_s"], 2)
            row["ratio"] = round(row["enforced_median_s"] / row["control_median_s"], 3)
        out.append(row)
    return out


MIN_K = 5     # the analysis refuses fewer (`[overhead].min_k`); a cell below it is listed apart, never written as a row


def _single_runs_only(runs: list[dict]) -> None:
    not_single = sorted(r.get("run_key", "?") for r in runs if (r["extra"].get("pool_workers") or 1) > 1 or "level" in r["extra"])
    if not_single:
        raise ValueError(f"the arms must run at the same concurrency, one at a time; these do not: {not_single[:5]}")


def analysis_overhead(runs: list[dict], *, traced: bool = True, seed: int = 20271203) -> dict:
    """The file the analysis reads (`icsa-enforcement-overhead-v1`, icsa/analysis/overhead.py): overhead = median wall time
    with the enforcement minus without it, never subtracted from anything there. Both arms in one tracing state (default
    traced, as the agent runs are), or the tracer's cost would be mixed in.

    T-unpaginated's control arm is T's: its only difference is the gate's listing merge, so without the gate it is T.
    M's baseline is "unsandboxed mount": the same sidecar mount read by a plain container, without the sandbox around
    the reader (science, #12: M's control keeps the sidecar; `arm_note` says so)."""
    import statistics
    _single_runs_only(runs)
    cells = _arms([r for r in runs if bool(r["extra"].get("traced")) is traced], lambda r: r["extra"].get("variant", "enforced"))
    rows, below = [], []
    for (o, la), d in sorted(cells.items()):
        enf = d.get("enforced", [])
        if not enf:
            continue
        arm = "T" if o == Option.T_UNPAGINATED.value else o
        ctl = cells.get((arm, la), {}).get("no-enforcement", [])
        k = min(len(enf), len(ctl))
        if k < MIN_K:
            below.append({"option": o, "layout": la, "k_enforced": len(enf), "k_control": len(ctl)})
            continue
        lo, hi = _median_diff_interval(enf, ctl, seed=seed)
        rows.append({"option": o, "layout": la, "overhead_s": round(statistics.median(enf) - statistics.median(ctl), 3),
                     "k": k, "baseline": "unsandboxed mount" if o in (Option.M.value, Option.M_PLUS.value) else "no gate",
                     "lo": round(lo, 3), "hi": round(hi, 3), "enforced_median_s": round(statistics.median(enf), 3),
                     "control_median_s": round(statistics.median(ctl), 3), "k_enforced": len(enf), "k_control": len(ctl),
                     "control_arm": arm, "traced": traced,
                     "arm_note": ("the same oneclient sidecar mount read by a plain container: no sandbox around the reader"
                                  if o in (Option.M.value, Option.M_PLUS.value)
                                  else "same image, script and limits, plain container on docker's bridge, direct to the provider")})
    return {"format": "icsa-enforcement-overhead-v1", "rows": rows, "below_min_k": below,
            "label": "scripted, interleaved per instance and cell, one at a time; wall time of the pipeline in the container"}


def traced_overhead(runs: list[dict], *, seed: int = 20271204, min_k: int = 3) -> dict:
    """Traced vs untraced per option x layout, with the enforcement on (science, #9): the curve runs traced, so its cost is
    stated beside the gate and sidecar overhead. No analysis rule fixes its k; `k` is on every row, and a cell below `min_k`
    is listed apart."""
    import statistics
    _single_runs_only(runs)
    rows, below = [], []
    arms = [r for r in runs if r["extra"].get("variant", "enforced") == "enforced"]     # with the same enforcement
    for (o, la), d in sorted(_arms(arms, lambda r: "traced" if r["extra"].get("traced") else "untraced").items()):
        tr, un = d.get("traced", []), d.get("untraced", [])
        k = min(len(tr), len(un))
        if k < min_k:
            below.append({"option": o, "layout": la, "k_traced": len(tr), "k_untraced": len(un)})
            continue
        lo, hi = _median_diff_interval(tr, un, seed=seed)
        rows.append({"option": o, "layout": la, "overhead_s": round(statistics.median(tr) - statistics.median(un), 3), "k": k,
                     "lo": round(lo, 3), "hi": round(hi, 3), "traced_median_s": round(statistics.median(tr), 3),
                     "untraced_median_s": round(statistics.median(un), 3)})
    return {"format": "icsa-trace-overhead-v1", "rows": rows, "below_min_k": below}
