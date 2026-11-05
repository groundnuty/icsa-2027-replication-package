"""The provider watch: what B's providers' op_worker pods are, and have been, read from this host and pushed to the providers' own B hosts.

Each cycle, per provider (`site_u`, `site_x`, `site_o`, `site_p`):

1. reads the pod: `kubectl get pod oneprovider-0` (uid, start time, restart count, the container's `startedAt`, image id) and one `exec` that prints the pod's clock,
   op_worker's process start (from /proc: its start time since boot, so it is the same number every time), the config files of `config.d` by digest and their
   `audit` lines;
2. makes a SAMPLE and appends it to `<store>/mon.jsonl` in the format of site_g's monitor log (`{ts, opw: {id}}`), where `windows.restart_windows` already turns a
   change of `id` between two samples into a restart window and `windows.mon_span` into the coverage. A change is also written to `<store>/restarts.jsonl`
   with both identities and UTC times. `<store>/restart_log.jsonl` is the (empty) hash-chained log `extract --restart-log` wants: providers have no planned
   restarts of ours;
3. pulls the audit log (`provider.pull_cycle`), when the provider has a filter;
4. pushes `settings.json` to the provider's B host, where its `site_g_settings_cmd` can `cat` it: the settings fields (image, command, config digests, keyed
   fingerprints of env values and the command line), `op_worker_pod` (restarts, started, op_worker_process_started: what `opwrestart.identity` reads, and what
   `frsettings.canonical_hash` leaves out, so a restart is no settings change) and `monitor_status` (`ts`: how old the file is; also left out of the hash).

A secret never leaves this host: env values and the command line only as HMAC-SHA256 under a key kept here (a plain digest of a short value could be tried
out), the kubeconfig only as the child's KUBECONFIG, never on a command line. A provider that fails is reported and the others go on; a sample that cannot be
logged (a damaged `mon.jsonl`) stops that provider's push, since a settings file saying "all quiet" over a broken restart history would be a lie.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from . import provider as P

CONTEXT = "icsa-audit-reader"
CONFIG_DIR = "/etc/op_worker/config.d"
STORAGE_PATH = "/volumes/posix"                                       # the provider's posix storage: its own 30 GB volume
PROC_PATTERN = "[/]usr/lib/op_worker/erts[^ ]*/bin/beam.smp"        # the bracket keeps the probe's own shell, which carries this text, from matching it
_RC = re.compile(r"^ICSA_PULL_RC=(\d+)$")
_SAFE = re.compile(r"[A-Za-z0-9._/-]+")


def iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fingerprint(key: bytes, value: str) -> str:
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()[:16]


# ---------------------------------------------------------------- the pod
class PodProbe:
    """`get pod` and one `exec` into oneprovider-0 of `namespace`, by argv (no local shell: nothing to quote). `run(argv, capture_output=, timeout=, env=)`
    defaults to subprocess.run."""

    def __init__(self, namespace: str, *, kubeconfig, context: str = CONTEXT, run: Callable | None = None, timeout_s: int = 90, exec_prefix: str | None = None,
                 config_dir: str = CONFIG_DIR, proc_pattern: str = PROC_PATTERN, storage_path: str = STORAGE_PATH, env_pid: int = 1):
        if not re.fullmatch(r"[a-z0-9-]+", namespace) or not re.fullmatch(r"[A-Za-z0-9._@:-]+", context):
            raise ValueError("a namespace or context name that is not a plain name")
        for v in (config_dir, storage_path):
            if not _SAFE.fullmatch(v):
                raise ValueError(f"{v!r}: not a plain path")
        if "'" in proc_pattern or "\n" in proc_pattern:
            raise ValueError("a process pattern with a quote or a newline")
        self.namespace, self.kubeconfig, self._run, self.timeout_s = namespace, str(kubeconfig), run, timeout_s
        self.kubectl = ["kubectl", "--context", context, "-n", namespace]
        self.exec = shlex.split(exec_prefix) if exec_prefix is not None else [*self.kubectl, "exec", "oneprovider-0", "--"]
        self.config_dir, self.proc_pattern, self.storage_path, self.env_pid = config_dir, proc_pattern, storage_path, int(env_pid)

    def _call(self, argv: list[str], what: str) -> bytes:
        run = self._run or subprocess.run
        p = run(argv, capture_output=True, timeout=self.timeout_s, env={**os.environ, "KUBECONFIG": self.kubeconfig, "SSH_AUTH_SOCK": ""})
        if p.returncode != 0:
            raise RuntimeError(f"{what}: exit {p.returncode}: {(p.stderr or b'')[-300:].decode('utf-8', 'replace').strip()}")
        return p.stdout or b""

    def get_pod(self) -> dict:
        out = self._call([*self.kubectl, "get", "pod", "oneprovider-0", "-o", "json"], "get pod")
        try:
            d = json.loads(out)
        except ValueError:
            raise RuntimeError("get pod: the reply is not JSON") from None
        if not isinstance(d, dict) or "status" not in d:
            raise RuntimeError("get pod: the reply is not a pod")
        return d

    def script(self) -> str:
        # the process start is the kernel's start time since boot plus the boot time, so it is one number, however often it is read (the age of the process, or
        # the mtime of its /proc entry, moves from one read to the next)
        return (f"date +%s.%N; "
                f"for p in $(pgrep -f '{self.proc_pattern}'); do [ \"$p\" = \"$$\" ] && continue; "
                "st=$(sed 's/^.*) //' /proc/$p/stat | awk '{print $20}'); bt=$(awk '/^btime/{print $2}' /proc/stat); hz=$(getconf CLK_TCK 2>/dev/null || echo 100); "
                "echo \"PROC $p $((bt + st / hz)) $(tr '\\0' ' ' < /proc/$p/cmdline)\"; done; "
                f"for f in {self.config_dir}/*; do [ -f \"$f\" ] && echo \"CONF $(basename \"$f\") $(sha256sum < \"$f\" | cut -d' ' -f1)\"; done; "
                f"grep -h -i audit {self.config_dir}/* 2>/dev/null | sed 's/^/AUDIT /'; "
                f"df -P -k {self.storage_path} | awk 'NR==2 {{print \"DF \" $4}}'; "
                f"echo \"ENVB64 $(base64 -w0 < /proc/{self.env_pid}/environ)\"; echo ICSA_PULL_RC=0")

    def exec_probe(self) -> dict:
        lines = self._call([*self.exec, "sh", "-c", self.script()], "exec probe").decode("utf-8", "replace").splitlines()
        m = _RC.match(lines[-1]) if lines else None
        if m is None or m.group(1) != "0":
            raise RuntimeError("exec probe: no exit status came back from the pod (a dead transport?)")
        out: dict = {"ts": None, "procs": [], "config_d": {}, "audit_lines": [], "df_kib": None, "env_pid1": None}
        for ln in lines[:-1]:
            if out["ts"] is None:
                try:
                    out["ts"] = float(ln)
                except ValueError:
                    raise RuntimeError("exec probe: the pod's date gave no time") from None
            elif ln.startswith("PROC "):
                parts = ln.split(" ", 3)
                out["procs"].append({"pid": int(parts[1]), "started": int(parts[2]), "cmdline": parts[3] if len(parts) > 3 else ""})
            elif ln.startswith("CONF "):
                _, name, sha = ln.split(" ", 2)
                out["config_d"][name] = sha
            elif ln.startswith("AUDIT "):
                out["audit_lines"].append(ln[len("AUDIT "):].strip())
            elif ln.startswith("DF ") and ln[3:].strip().isdigit():
                out["df_kib"] = int(ln[3:].strip())
            elif ln.startswith("ENVB64 ") and ln[7:].strip():
                try:                                              # the container's effective environment (what `valueFrom` and `envFrom` resolved to): never leaves this host
                    out["env_pid1"] = {k: v for k, _, v in (r.partition("=") for r in base64.b64decode(ln[7:].strip()).decode("utf-8", "replace").split("\0") if "=" in r)}
                except ValueError:
                    raise RuntimeError("exec probe: the environment could not be decoded") from None
        if out["ts"] is None:
            raise RuntimeError("exec probe: no time came back")
        return out


# ---------------------------------------------------------------- the sample
_AUDIT_ON = re.compile(r"file_access_audit_log_enabled\s*,\s*(true|false)")


def make_sample(provider: str, pod: dict, probe: dict, key: bytes) -> dict:
    """The pod's identity and its settings from one `get pod` and one probe. ValueError unless a container is there and running, exactly one op_worker process
    is, and the free space and the effective environment were read: an identity needs a start, and a sample that cannot say what it saw is no evidence. Nothing a
    secret could be in is kept as it is: command, args, config files and environment values go through a keyed fingerprint."""
    cs = (pod.get("status") or {}).get("containerStatuses") or []
    if not cs:
        raise ValueError("the pod reports no container status")
    st = cs[0]
    run = (st.get("state") or {}).get("running")
    if not run or not run.get("startedAt"):
        raise ValueError(f"the container {st.get('name')} is not running (state {list(st.get('state') or {})})")
    if not isinstance(probe.get("df_kib"), int) or probe["df_kib"] < 0:
        raise ValueError(f"the free space of the storage volume could not be read (df gave {probe.get('df_kib')!r})")
    if not isinstance(probe.get("env_pid1"), dict) or not probe["env_pid1"]:
        raise ValueError("the container's effective environment could not be read (/proc/1/environ)")
    procs = probe["procs"]
    if len(procs) != 1:                      # an unreadable start would read as "no restart" between two such samples, and as a restart on the way in and out of it
        raise ValueError(f"{len(procs)} op_worker processes found (one expected): the process start, and so the identity, is unknown")
    spec = next((c for c in pod["spec"]["containers"] if c.get("name") == st.get("name")), pod["spec"]["containers"][0])
    pstart = procs[0]["started"]
    uid, start = pod["metadata"]["uid"], pod["status"].get("startTime")
    ident = f"{uid}|{start}|{st['restartCount']}|{run['startedAt']}|{pstart}"
    pod_info = {"uid": uid, "start_time": start, "restart_count": st["restartCount"], "started_at": run["startedAt"], "node": pod["spec"].get("nodeName"),
                "image_id": st.get("imageID"), "ready": st.get("ready"), "process_started": pstart}
    env = probe["env_pid1"]
    declared = [e["name"] for e in spec.get("env") or []]
    audit_text = "\n".join(probe["audit_lines"])
    on = _AUDIT_ON.search(audit_text)
    settings = {"image": spec.get("image"), "image_id": st.get("imageID"), "resources": spec.get("resources"),
                "command_fingerprint": fingerprint(key, json.dumps(spec.get("command"), sort_keys=True)), "args_fingerprint": fingerprint(key, json.dumps(spec.get("args"), sort_keys=True)),
                "volume_mounts": sorted((v["name"], v["mountPath"]) for v in spec.get("volumeMounts") or []),
                "env_spec_fingerprints": {e["name"]: fingerprint(key, json.dumps({k: v for k, v in e.items() if k != "name"}, sort_keys=True)) for e in spec.get("env") or []},
                "env_effective_fingerprints": {n: fingerprint(key, env[n]) if n in env else "absent" for n in sorted(declared)},
                "env_from": [list(x.values())[0].get("name") if isinstance(list(x.values())[0], dict) else None for x in spec.get("envFrom") or []],
                "config_d_fingerprints": {n: fingerprint(key, sha) for n, sha in sorted(probe["config_d"].items())},
                "audit_config_fingerprint": fingerprint(key, audit_text), "audit_log_enabled": (on.group(1) == "true") if on else None,
                "op_worker_cmdline_fingerprint": fingerprint(key, "\n".join(sorted(p["cmdline"] for p in procs)))}
    return {"provider": provider, "ts": probe["ts"], "utc": iso(probe["ts"]), "opw": {"id": ident}, "pod": pod_info, "settings": settings,
            "data_free_gib": round(probe["df_kib"] / 1048576, 2)}


def settings_object(s: dict, *, now: float) -> dict:
    """What the B host's `site_g_settings_cmd` and `site_g_disk_cmd` print (one file): the settings fields; under `op_worker_pod` the three fields `opwrestart.identity`
    reads; `monitor_status` with `ts`, THIS host's clock at the push (a dead watch is a stale file: the loop's own time, not the pod's); and `data_free_gib`, the
    free space of the provider's posix volume. `op_worker_pod`, `monitor_status` and `data_free_gib` are left out of `frsettings.canonical_hash`."""
    p = s["pod"]
    return {**s["settings"], "op_worker_pod": {"restarts": p["restart_count"], "started": p["started_at"],
                                               "op_worker_process_started": iso(p["process_started"]) if p["process_started"] is not None else None},
            "data_free_gib": s["data_free_gib"], "monitor_status": {"running": True, "last_sample_age_s": 0, "ts": now}}


# ---------------------------------------------------------------- the logs the audit reader reads
def _append(path: Path, obj: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        os.write(fd, (json.dumps(obj, sort_keys=True) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for n, ln in enumerate(path.read_text().splitlines(), 1):
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except ValueError:
            raise ValueError(f"{path.name} line {n} is not JSON (a torn write?): the restart history is not trustworthy until a person looks") from None
    return out


def read_restarts(store) -> list[dict]:
    return _read_jsonl(Path(store) / "restarts.jsonl")


def record(store, s: dict) -> bool:
    """Append the sample to mon.jsonl and, when its identity differs from the last sample's, the change to restarts.jsonl. True when it was a restart. The files
    are checked first: a damaged one raises before anything is written."""
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    mon = _read_jsonl(store / "mon.jsonl")
    _read_jsonl(store / "restarts.jsonl")
    (store / "restart_log.jsonl").touch()
    line = {"ts": s["ts"], "utc": s["utc"], "provider": s["provider"], "opw": s["opw"], "pod": s["pod"]}
    changed = bool(mon) and mon[-1]["opw"]["id"] != s["opw"]["id"]
    _append(store / "mon.jsonl", line)
    if changed:
        _append(store / "restarts.jsonl", {"ts": s["ts"], "utc": s["utc"], "provider": s["provider"], "from": mon[-1]["opw"]["id"], "to": s["opw"]["id"],
                                           "last_sample_before": mon[-1]["ts"], "pod_before": mon[-1]["pod"], "pod_after": s["pod"]})
    return changed


# ---------------------------------------------------------------- the push
@dataclasses.dataclass(frozen=True)
class Target:
    host: str
    user: str
    directory: str
    key: str
    known_hosts: str

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9.-]+", self.host) or not re.fullmatch(r"[a-z_][a-z0-9_-]*", self.user):
            raise ValueError("a host or user that is not a plain name")
        for v in (self.directory, self.key, self.known_hosts):
            if not _SAFE.fullmatch(v) or ".." in v.split("/"):
                raise ValueError(f"{v!r}: not a plain path")


def _ssh_opts(t: Target) -> list[str]:
    return ["-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "-o", "ProxyCommand=none", "-o", "IdentitiesOnly=yes", "-i", t.key, "-o", f"UserKnownHostsFile={t.known_hosts}"]


def push(t: Target, files: dict[str, bytes], *, run: Callable = subprocess.run, timeout_s: int = 60) -> None:
    """Each file to `<directory>/.<name>.tmp` by scp, then renamed over `<name>` by ssh, so a reader never sees half a file and a failed copy leaves the old one
    whole. Host keys are checked against `known_hosts` (BatchMode: an unknown host fails; nothing is ever added or switched off)."""
    for name in files:                                   # every name is checked before any command exists
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise ValueError(f"{name!r}: not a plain file name")
    env = {**os.environ, "SSH_AUTH_SOCK": ""}
    p = run(["ssh", *_ssh_opts(t), f"{t.user}@{t.host}", f"mkdir -p {t.directory}"], capture_output=True, timeout=timeout_s, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"ssh mkdir on {t.host}: exit {p.returncode}: {(p.stderr or b'')[-200:].decode('utf-8', 'replace').strip()}")
    for name, data in files.items():
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / name
            local.write_bytes(data)
            tmp = f"{t.directory}/.{name}.tmp"
            p = run(["scp", *_ssh_opts(t), str(local), f"{t.user}@{t.host}:{tmp}"], capture_output=True, timeout=timeout_s, env=env)
            if p.returncode != 0:
                raise RuntimeError(f"scp to {t.host}: exit {p.returncode}: {(p.stderr or b'')[-200:].decode('utf-8', 'replace').strip()}")
        p = run(["ssh", *_ssh_opts(t), f"{t.user}@{t.host}", f"mv {tmp} {t.directory}/{name}"], capture_output=True, timeout=timeout_s, env=env)
        if p.returncode != 0:
            raise RuntimeError(f"ssh mv on {t.host}: exit {p.returncode}: {(p.stderr or b'')[-200:].decode('utf-8', 'replace').strip()}")


# ---------------------------------------------------------------- the cycle
@dataclasses.dataclass
class ProviderCfg:
    name: str
    store: Path
    filter: P.UserFilter | None = None
    target: Target | None = None


def _pod_identity(pod: dict) -> tuple:
    cs = ((pod.get("status") or {}).get("containerStatuses") or [{}])[0]
    return pod["metadata"]["uid"], cs.get("restartCount"), ((cs.get("state") or {}).get("running") or {}).get("startedAt")


def run_cycle(cfgs: list[ProviderCfg], *, probe_of: Callable, key: bytes, push_fn: Callable | None = None, remote_of: Callable | None = None,
              now: Callable[[], float] = time.time) -> dict:
    """One cycle over the providers; {name: {ok, error, restarted, pull, pushed}}. A step that fails is recorded and the providers after it still run."""
    res: dict = {}
    for c in cfgs:
        r = res[c.name] = {"ok": False, "error": None, "restarted": None, "pull": None, "pushed": False}
        try:
            pr = probe_of(c)
            pod, ex = pr.get_pod(), pr.exec_probe()
            again = pr.get_pod()
            if _pod_identity(pod) != _pod_identity(again):          # a restart while we read: the two halves are of different pods, and the next sample would see another change
                raise RuntimeError("the pod changed during the probe (uid, restart count or container start differ between the two reads); no sample is made")
            s = make_sample(c.name, pod, ex, key)
            r["restarted"] = record(c.store, s)
        except Exception as e:                                          # noqa: BLE001 - one provider's failure is its own
            r["error"] = f"{type(e).__name__}: {e}"
            continue
        errs = []
        if c.filter is not None and remote_of is not None:
            try:
                r["pull"] = P.pull_cycle(remote_of(c), c.store, c.filter, provider=c.name)
            except Exception as e:                                      # noqa: BLE001
                errs.append(f"pull: {type(e).__name__}: {e}")
        if c.target is not None and push_fn is not None:
            try:
                push_fn(c.target, {"settings.json": (json.dumps(settings_object(s, now=now()), indent=1, sort_keys=True) + "\n").encode()})
                r["pushed"] = True
            except Exception as e:                                      # noqa: BLE001
                errs.append(f"push: {type(e).__name__}: {e}")
        r["error"], r["ok"] = ("; ".join(errs) or None), not errs
    return res


def load_key(path) -> bytes:
    """The HMAC key of this host's fingerprints: 32 random bytes in a mode-600 file, made once. Losing it only re-keys the fingerprints (one settings change)."""
    p = Path(path)
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(os.urandom(32))
    if (p.stat().st_mode & 0o077) or p.stat().st_size < 32:
        raise ValueError(f"{p}: the key file must be mode 600 and at least 32 bytes")
    return p.read_bytes()


def slot_map_users(path) -> list[str]:
    """The user ids of a provider's slot map (`{slot key: {user: <id>, option}}`): the audit filter's allowlist."""
    try:
        m = json.loads(Path(path).read_text())
        return sorted({v["user"] for v in m.values() if isinstance(v, dict) and v.get("user")})
    except (OSError, ValueError, AttributeError) as e:
        raise ValueError(f"the slot map {path} cannot be read ({type(e).__name__})") from None


def configs(d: dict) -> tuple[list[ProviderCfg], dict]:
    ssh = d.get("ssh") or {}
    out = []
    for p in d["providers"]:
        f = p.get("filter") if p.get("pull") is True else None        # the audit log is pulled, and the marker written, only where `"pull": true` says so
        t = p.get("push")
        out.append(ProviderCfg(name=p["name"], store=Path(p["store"]),
                               filter=P.UserFilter(users=(*f.get("users", ()), *(slot_map_users(f["slot_map"]) if f.get("slot_map") else ())), prefixes=tuple(f.get("prefixes", ())), exclude=tuple(f.get("exclude", ()))) if f else None,
                               target=Target(host=t["host"], user=t.get("user", "ubuntu"), directory=t["directory"], key=ssh["key"], known_hosts=ssh["known_hosts"]) if t else None))
    return out, d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m icsa.faults.mainaudit.watch", description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True, help="read afresh every cycle: a provider added, or a filter switched on (`\"pull\": true`), takes effect at the next one")
    ap.add_argument("--once", action="store_true", help="one cycle, then exit (exit 3 if any provider failed)")
    ap.add_argument("--period", type=float, default=None, help="seconds between cycles (default: the config's period_s, else 3600)")
    ap.add_argument("--no-push", action="store_true", help="do not push to the B hosts")
    ap.add_argument("--no-pull", action="store_true", help="do not pull the audit logs even where the config says to (no marker is ever written)")
    ap.add_argument("--only", action="append", default=[], help="a provider name; repeatable (default: all)")
    ap.add_argument("--pidfile", default=None, help="write this process's pid here while it runs (refuses to start over a live one), so it is stopped by pid, never by pattern")
    a = ap.parse_args(argv)
    if a.pidfile:
        pf = Path(a.pidfile)
        try:
            other = int(pf.read_text().strip())
            os.kill(other, 0)
        except (OSError, ValueError):
            pass
        else:
            print(json.dumps({"error": f"pidfile {pf}: process {other} is alive"}), flush=True)
            return 4
        pf.write_text(f"{os.getpid()}\n")
    try:
        return _loop(a)
    finally:
        if a.pidfile:
            with contextlib.suppress(OSError):
                if Path(a.pidfile).read_text().strip() == str(os.getpid()):
                    Path(a.pidfile).unlink()


def _loop(a) -> int:
    while True:
        t0 = time.time()
        try:
            cfg = json.loads(Path(a.config).read_text())
            cfgs, _ = configs(cfg)
            if a.only:
                cfgs = [c for c in cfgs if c.name in a.only]
            key = load_key(cfg["key_file"])
            kube, ctx = cfg["kubeconfig"], cfg.get("context", CONTEXT)
            period = a.period if a.period is not None else float(cfg.get("period_s", 3600))
        except (OSError, ValueError, KeyError) as e:               # a half-written or wrong config costs this cycle, not the loop: the files on the B hosts go stale on their own
            print(json.dumps({"utc": iso(t0), "error": f"config {a.config}: {type(e).__name__}: {e}"}, sort_keys=True), flush=True)
            if a.once:
                return 2
            time.sleep(60.0)
            continue
        res = run_cycle(cfgs, probe_of=lambda c: PodProbe(c.name, kubeconfig=kube, context=ctx), key=key, push_fn=None if a.no_push else push,
                        remote_of=None if a.no_pull else (lambda c: P.PodDirRemote(c.name, kubeconfig=kube, context=ctx)))
        print(json.dumps({"utc": iso(t0), "results": {n: {k: v for k, v in r.items() if k != "pull"} | ({"pull": {"files": [(f["n"], f["finished"]) for f in r["pull"]["files"]],
                                                                                                                   "gaps": r["pull"]["gaps"], "marker": r["pull"]["marker"]}}
                                                                                                 if r["pull"] else {}) for n, r in res.items()}}, sort_keys=True), flush=True)
        bad = [n for n, r in res.items() if not r["ok"]]
        if a.once:
            return 3 if bad else 0
        time.sleep(max(1.0, period - (time.time() - t0)))


if __name__ == "__main__":
    sys.exit(main())
