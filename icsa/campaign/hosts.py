"""Two run hosts, split by whole models (science, #2, 2 Nov 05:36Z item 4 and 14:14Z item 4).

ONE dispatcher (the campaign process on the main host) keeps every cross-run rule as it is: the caps counted over all runs in
flight on both hosts (site_g's load is shared), the S2 runs' spare-capacity rule, the barriers, the Sonnet gate, the stops, one
store. Only execution moves: a run of a model assigned to a remote host is executed there by `icsa.campaign.remote`, started
over a transport (ssh with a forced command), and its run directory is pulled back. Remote docker is not an option: the
sandbox does loop mounts and cgroup reads on its own docker host.

The rules this module holds:
- every model of the manifest runs on exactly ONE host (`model_host`), so no model's runs mix hosts and its options stay
  balanced on its host as the manifest orders them; the map and the slot-user partition are pinned in the campaign state at
  the first start (`assignment_digest`), and a resume with another map is refused;
- the Onedata slot users are partitioned by host (`slot_keys`): a key on two hosts is refused at start, so no slot user can be
  held on both (a lease is an flock, which does not cross hosts);
- per host: its own sandbox cap, its memory and disk holds (host-wide, never per option: a per-option hold would let one
  option fall behind the others of a model), its image and code identity, and a down state. A host that fails pauses only
  the dispatch of its own models and raises an alarm; the other host goes on;
- a run whose host was lost mid-run is an infra failure, and it stays COUNTED as in flight (an orphan) until the host shows
  it is gone, because its sandbox may still be reading site_g.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import io
import json
import logging
import re
import shlex
import subprocess
import tarfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from .errors import InfraError

log = logging.getLogger(__name__)
LOCAL = "local"
HOST_KIND = "host"                # the infra kind of a host failure
NOT_STARTED = "not started on "   # detail prefix: no sandbox was started (no attempt used, the host is paused)
UNCERTAIN = "start uncertain on "  # detail prefix: the start may have reached the host, but no answer came: no attempt used, and kept as an orphan
LOST = "lost on "                 # detail prefix: the run's host could not be reached to the end of the run
WORKER_DIED = "worker died on "   # detail prefix: the host answered, its worker is gone with no result: one run's failure, not the host's

# A host whose own setup is broken (science #34, 12:11Z): the second VM lacked the admin password file and 13 pilot runs went infra_exhausted within minutes, each on
# `knowledge: factory failed: FileNotFoundError: ...onedata.pass`. HOST_SETUP_FAILS failures of one kind before the agent starts, on one host, within
# HOST_SETUP_WINDOW_S (by failure time), hold that host as a failed probe does (`HostBook.mark_down`); after that no attempt is charged for such a failure there.
HOST_SETUP_FAILS = 3
HOST_SETUP_WINDOW_S = 600
HOST_SETUP_PREFIX = 60                 # characters of the message, after its digits are collapsed, that tell two kinds apart
# The two stages of icsa/harness/runner.py that fail before the agent loop starts and say nothing of the run: the sandbox could not be started, and the knowledge plane's factory
# could not be built. The harness labels each in the detail (`<stage>: <Type>: <message>`); a failure of any later stage (a kill, the plane's start or teardown, a collection, the
# model's endpoint) is not here. A start refused for want of a slot user is the unstarted rule's (scheduler `_is_unstarted`), not this.
HOST_SETUP_STAGES = {"sandbox": ("start failed: ",), "knowledge": ("factory failed: ",)}


def setup_failure_kind(infra_kind: str, detail: str) -> str | None:
    """`<Type>: <prefix>` of a failure at one of the stages above, else None: the exception's type and the first HOST_SETUP_PREFIX characters of its message with every run of
    digits collapsed to `#` (`[Errno 2]` is `[Errno #]`; a port, a pid or a count never tells two failures apart). `harness_error_kind`'s convention (the type before the first
    colon), after the stage's label; an infra failure comes through a remote host as the same (kind, detail), not wrapped."""
    stages = HOST_SETUP_STAGES.get(infra_kind)
    if not stages or not detail.startswith(stages):
        return None
    body = detail[len(next(x for x in stages if detail.startswith(x))):]
    head, sep, rest = body.partition(":")
    ident = r"[A-Za-z_][A-Za-z0-9_.]*"
    if sep and re.fullmatch(ident, head.strip()):
        typ, msg = head.strip(), rest.strip()
    elif not sep and re.fullmatch(ident, body.strip()):
        typ, msg = body.strip(), ""
    else:
        typ, msg = "unknown", body.strip()
    return f"{typ}: {re.sub(r'[0-9]+', '#', msg)[:HOST_SETUP_PREFIX]}"


class HostConfigError(ValueError):
    pass


@dataclasses.dataclass
class HostSpec:
    name: str
    remote: bool = False
    ssh: list[str] | None = None              # the argv prefix that reaches the host's forced command (remote only)
    max_sandboxes: int | None = None          # this host's own limit; the campaign's caps still count both hosts
    mem_pause_below_gib: float | None = None
    mem_resume_at_gib: float | None = None
    disk_min_free_gib: float | None = None    # host-wide hold on the free disk (run root and docker root, the smaller)
    slot_keys: list[str] = dataclasses.field(default_factory=list)
    option_caps: dict[str, int] = dataclasses.field(default_factory=dict)   # e.g. {"D": 11}: held IN STEP (scheduler: a model waits)


def host_specs(cfg: Any) -> dict[str, HostSpec]:
    out = {}
    for name, d in (getattr(cfg, "hosts", None) or {}).items():
        d = dict(d)
        d.pop("name", None)
        unknown = set(d) - {f.name for f in dataclasses.fields(HostSpec)}
        if unknown:
            raise HostConfigError(f"host {name!r}: unknown keys {sorted(unknown)}")
        out[name] = HostSpec(name=name, **d)
    return out


def multi_host(cfg: Any) -> bool:
    return bool(getattr(cfg, "hosts", None))


def host_of(cfg: Any, model: str) -> str:
    """The host a model runs on. One host (no `hosts` in the config): the local one, as before."""
    if not multi_host(cfg):
        return LOCAL
    try:
        return cfg.model_host[model]
    except KeyError:
        raise HostConfigError(f"model {model!r} has no host in model_host") from None


def local_host(cfg: Any) -> str:
    specs = host_specs(cfg)
    return next((n for n, s in specs.items() if not s.remote), LOCAL)


def validate(cfg: Any, models: Iterable[str], options_by_model: dict[str, set[str]], slot_map: dict[str, str]) -> None:
    """Refuse a host plan that breaks a rule, naming every problem at once. `slot_map`: slot key -> option."""
    if not multi_host(cfg):
        return
    specs = host_specs(cfg)
    probs: list[str] = []
    locals_ = [n for n, s in specs.items() if not s.remote]
    if len(locals_) != 1:
        probs.append(f"exactly one host must be local (the dispatcher's own), found {locals_}")
    for n, s in specs.items():
        if s.remote and not s.ssh:
            probs.append(f"remote host {n!r} has no ssh command")
    models = sorted(set(models))
    for m in models:
        h = cfg.model_host.get(m)
        if h is None:
            probs.append(f"model {m!r} has no host")
        elif h not in specs:
            probs.append(f"model {m!r} is assigned to unknown host {h!r}")
    owner: dict[str, str] = {}
    for n, s in specs.items():
        for k in s.slot_keys:
            if k not in slot_map:
                probs.append(f"host {n!r}: slot key {k!r} is not in the slot map")
            if k in owner and owner[k] != n:
                probs.append(f"slot key {k!r} is on two hosts ({owner[k]!r}, {n!r}): a slot user must never be held on both")
            owner[k] = n
    for shape, k in sorted((getattr(cfg, "live_check_slot_keys", None) or {}).items()):     # the live check's probe users (amendment 25(e)) are its own: in no host's partition
        if k not in slot_map:
            probs.append(f"live-check slot key {k!r} ({shape} probe) is not in the slot map")
        elif slot_map[k] != shape:
            probs.append(f"live-check slot key {k!r} is a {slot_map[k]} slot user, but the {shape} probe needs a {shape} one")
        if k in owner:
            probs.append(f"live-check slot key {k!r} ({shape} probe) is also in host {owner[k]!r}'s slot_keys: a run could lease the probe's user, or the probe a run's")
    for n, s in specs.items():
        need = set().union(*[options_by_model.get(m, set()) for m in models if cfg.model_host.get(m) == n]) if models else set()
        have = {slot_map[k] for k in s.slot_keys if k in slot_map}
        for opt in sorted(need - have):
            probs.append(f"host {n!r} runs option {opt} but holds none of its slot users")
    if getattr(cfg, "process_reservations", None):        # fault calibration and the validation set: their keys are held back from the LOCAL pool, so they must be in it
        from icsa.harness import reservation
        local = next((s for s in specs.values() if not s.remote), None)
        probs += reservation.problems(cfg.process_reservations, slot_map, local.slot_keys if local is not None else [])
    if probs:
        raise HostConfigError("the host plan is refused: " + "; ".join(probs))


REPO = Path(__file__).resolve().parents[2]


def load_plan(cfg: Any) -> dict:
    """The fixed map's source (tools/host_split.py's output, science's ruling of #34, 15:39Z): the config's `model_host` must be exactly its
    `map`, and its own hash and its inputs' hash are pinned with the assignment, so the map can be traced to the planning figures it came from."""
    f = getattr(cfg, "host_plan_file", "") or ""
    if not f:
        raise HostConfigError("no host_plan_file: name the fixed map's source (tools/host_split.py's output), so it is pinned with its inputs' hashes")
    path = Path(f) if Path(f).is_absolute() else REPO / f
    try:
        raw = path.read_bytes()
        d = json.loads(raw)
    except (OSError, ValueError) as e:
        raise HostConfigError(f"host_plan_file {f}: unreadable ({type(e).__name__}: {e})") from e
    m = d.get("map")
    if m != dict(cfg.model_host):
        diff = sorted(k for k in set(m or {}) | set(cfg.model_host) if (m or {}).get(k) != cfg.model_host.get(k))
        raise HostConfigError(f"model_host differs from the fixed map in {f} for {diff}: the map is science's, set it from the file")
    return {"file": str(f), "sha256": hashlib.sha256(raw).hexdigest(), "inputs_sha256": (d.get("inputs") or {}).get("sha256")}


def assignment_digest(cfg: Any, plan: dict | None = None) -> str:
    """What is pinned in the campaign state: the model->host map, each host's slot users, and the map's source and its inputs' hashes.
    Caps and holds are not in it (an operator may change them on a resume); the assignment may not change once the campaign has started."""
    specs = host_specs(cfg)
    d = {"model_host": dict(sorted(cfg.model_host.items())),
         "hosts": {n: {"remote": s.remote, "slot_keys": sorted(s.slot_keys)} for n, s in sorted(specs.items())},
         "plan": None if plan is None else {"sha256": plan["sha256"], "inputs_sha256": plan["inputs_sha256"]}}
    return "sha256:" + hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---- the transport -------------------------------------------------------------------------------------------------
class TransportError(RuntimeError):
    """The host could not be reached (ssh failed, timed out); says nothing about the run."""


class Transport:
    def call(self, args: list[str], stdin: bytes | None = None, timeout: float = 60.0) -> tuple[int, bytes, bytes]:
        raise NotImplementedError


class SshTransport(Transport):
    """`ssh ... <target>` with a forced command on the far side (it reads SSH_ORIGINAL_COMMAND, so the arguments go as one
    shell-quoted string). ssh's own exit 255 is a transport failure; any other code is the remote command's."""

    def __init__(self, prefix: list[str], run: Callable = subprocess.run):
        self.prefix, self._run = list(prefix), run

    def call(self, args: list[str], stdin: bytes | None = None, timeout: float = 60.0) -> tuple[int, bytes, bytes]:
        import os
        env = {k: v for k, v in os.environ.items() if k != "SSH_AUTH_SOCK"}     # an ssh agent can hang a login (lane-common, 2 Nov 04:01Z)
        try:
            p = self._run([*self.prefix, shlex.join(args)], input=stdin if stdin is not None else b"", capture_output=True,
                          timeout=timeout, env=env)
        except subprocess.TimeoutExpired as e:
            raise TransportError(f"timed out after {timeout:g} s") from e
        except OSError as e:
            raise TransportError(f"{type(e).__name__}: {e}") from e
        if p.returncode == 255:
            raise TransportError((p.stderr or b"").decode(errors="replace").strip()[-300:] or "ssh exit 255")
        return p.returncode, p.stdout, p.stderr


# ---- per-host state ------------------------------------------------------------------------------------------------
@dataclasses.dataclass
class Probe:
    at: float                                  # monotonic
    ok: bool
    why: str | None = None
    mem_available: int | None = None           # bytes
    disk_free_gib: float | None = None
    live: list[str] = dataclasses.field(default_factory=list)   # run dirs with a live worker
    tree: str | None = None
    image_ok: bool | None = None
    endpoints: list[dict] | None = None        # the host's own endpoints.json (its site_a supervisor's); None: unreadable there
    pool: dict | None = None                   # the host's slot-user pool (slot_lease.pool_status); None: not reported
    d_use: dict = dataclasses.field(default_factory=dict)   # campaign run key -> {"bytes", "spool_bytes"} of its live sandbox (diskuse)
    unreaped: list[str] = dataclasses.field(default_factory=list)   # in `live`: run dirs whose worker died and whose sandbox is not shown gone yet


class HostBook:
    """Dispatchability of each host, its orphans, and the alarms. Thread-safe; the scheduler holds its own lock around
    dispatch, and workers and the prober call in from their threads."""

    def __init__(self, cfg: Any, event: Callable[[str, str, str | None, str], None], now_iso: Callable[[], str],
                 transports: dict[str, Transport] | None = None, mono: Callable[[], float] = time.monotonic,
                 local_tree: str | None = None, image_id: str | None = None, persist: Callable[[dict], None] | None = None,
                 on_orphan_end: Callable[[str, dict], None] | None = None):
        self.cfg, self.specs = cfg, host_specs(cfg)
        self._persist = persist or (lambda d: None)
        self._on_orphan_end = on_orphan_end or (lambda k, o: None)
        self._deaths: dict[str, list[float]] = {}
        self._setup_fails: dict[str, list[tuple[float, str, str]]] = {}      # host -> (failure epoch, kind, run key) of the pre-agent failures still inside the window
        self._setup_tripped: dict[str, set[str]] = {}                        # host -> the kinds that tripped it: until a run there gets past setup, each failure of one is the host's
        self.local = local_host(cfg)
        self._event, self._now = event, now_iso
        self._mono = mono
        self.transports = transports or {n: SshTransport(s.ssh or []) for n, s in self.specs.items() if s.remote}
        self.local_tree, self.image_id = local_tree, image_id
        self._lock = threading.RLock()
        self.down: dict[str, str] = {}             # host -> why (cleared by a good probe after the pause)
        self.pause_until: dict[str, float] = {}
        self.probes: dict[str, Probe] = {}
        self.orphans: dict[str, dict] = {}         # "<run_key>#<attempt id>" -> {run_key, model, group, host, run_dir, slot}
        self._held: dict[str, str | None] = {}     # host -> last hold reason logged (an event per change only)

    # -- the dispatcher's question
    def unreachable(self, host: str) -> str | None:
        """Why `host` cannot take a run at all now (down, never or no longer probed, probe failed, other code, pinned image missing), or None. The ordinary holds
        (its own cap, memory, disk) are not here: they pass in minutes and say nothing about the host being gone."""
        with self._lock:
            s = self.specs.get(host)
            if s is None:
                return f"unknown host {host!r}"
            if host in self.down:
                return f"down: {self.down[host]}"
            if not s.remote:
                return None
            p = self.probes.get(host)
            stale = getattr(self.cfg, "host_probe_stale_s", 60.0)
            if p is None:
                return "not probed yet"
            if self._mono() - p.at > stale:
                return f"probe older than {stale:g} s"
            if not p.ok:
                return f"probe failed: {p.why}"
            if p.tree is not None and self.local_tree is not None and p.tree != self.local_tree:
                return f"code differs from the dispatcher's ({p.tree[:12]} vs {self.local_tree[:12]})"
            if self.image_id and p.image_ok is not True:
                return f"the pinned image {self.image_id[:19]} is not on the host"
            return None

    def hold(self, host: str, n_on_host: int, disk_reserve_gib: float = 0.0) -> str | None:
        """Why no new run may start on `host` now, or None. `disk_reserve_gib`: what its D transfers in flight may still spool (the free space now
        does not show it yet), held back from the free space."""
        with self._lock:
            s = self.specs.get(host)
            if s is None:
                return f"unknown host {host!r}"
            why = None
            if host in self.down:
                why = f"down: {self.down[host]}"
            elif s.remote:
                p = self.probes.get(host)
                stale = getattr(self.cfg, "host_probe_stale_s", 60.0)
                if p is None:
                    why = "not probed yet"
                elif self._mono() - p.at > stale:
                    why = f"probe older than {stale:g} s"
                elif not p.ok:
                    why = f"probe failed: {p.why}"
                elif p.tree is not None and self.local_tree is not None and p.tree != self.local_tree:
                    why = f"code differs from the dispatcher's ({p.tree[:12]} vs {self.local_tree[:12]})"
                elif self.image_id and p.image_ok is not True:
                    why = f"the pinned image {self.image_id[:19]} is not on the host"
                elif s.mem_pause_below_gib is not None and (p.mem_available is None or p.mem_available < self._mem_floor(host, s) * 1024 ** 3):
                    why = "memory below its hold" if p.mem_available is not None else "memory unknown"
                elif s.disk_min_free_gib is not None and (p.disk_free_gib is None or p.disk_free_gib - disk_reserve_gib < s.disk_min_free_gib):
                    why = (f"disk below its hold ({p.disk_free_gib:.1f} GiB free, {disk_reserve_gib:.1f} reserved for D spools in flight)"
                           if p.disk_free_gib is not None else "disk unknown")
            if why is None and s.max_sandboxes is not None and n_on_host >= s.max_sandboxes:
                return f"at its own cap {s.max_sandboxes}"       # an ordinary wait: not logged as a hold
            self._log_hold(host, why)
            return why

    def _mem_floor(self, host: str, s: HostSpec) -> float:
        """Hysteresis, as the local watchdog: once held for memory, a host resumes only at `mem_resume_at_gib`."""
        held = (self._held.get(host) or "").startswith("memory")
        return (s.mem_resume_at_gib or s.mem_pause_below_gib) if held else s.mem_pause_below_gib   # type: ignore[return-value]

    def _log_hold(self, host: str, why: str | None) -> None:
        if self._held.get(host) != why and not (why is None and host not in self._held):
            self._event(self._now(), "host_hold" if why else "host_dispatch_resumed", None, f"{host}: {why or 'dispatchable again'}")
        if why is None:
            self._held.pop(host, None)
        else:
            self._held[host] = why

    def n_orphans(self, host: str | None = None) -> int:
        with self._lock:
            return sum(1 for o in self.orphans.values() if host is None or o["host"] == host)

    def orphan_run_keys(self) -> set[str]:
        with self._lock:
            return {o["run_key"] for o in self.orphans.values()}

    # -- what runs report
    def mark_down(self, host: str, why: str) -> None:
        with self._lock:
            new = host not in self.down
            self.down[host] = why
            self.pause_until[host] = self._mono() + getattr(self.cfg, "host_pause_s", 300.0)
        if new:
            self._event(self._now(), "host_down", None, f"{host}: {why}; dispatch to its models is PAUSED, the other host goes on")

    def note_worker_death(self, host: str, why: str) -> None:
        """One dead worker is that run's infrastructure failure (the host answered); several together are the host's: `host_worker_deaths_pause` within
        `host_worker_deaths_window_s` pauses it, as a failed probe does (the lead, 2 Nov)."""
        n = int(getattr(self.cfg, "host_worker_deaths_pause", 3))
        w = float(getattr(self.cfg, "host_worker_deaths_window_s", 300.0))
        t = self._mono()
        with self._lock:
            seen = [x for x in self._deaths.get(host, []) if t - x < w] + [t]
            self._deaths[host] = seen
        if len(seen) >= n:
            self.mark_down(host, f"{len(seen)} workers died within {w:g} s (last: {why})")

    def note_setup_failure(self, host: str, kind: str, run_key: str, at: float) -> str:
        """One failure before the agent started, of `kind` (`setup_failure_kind`), that ended at epoch `at`. Returns what the scheduler does with it:
        "held": the host is down, or this kind already tripped it and no run there has got past setup since (`note_past_setup`), so this is the host's and not the run's: charge
        nothing, the run stays pending; and in the second case the host is marked down again at once (a probe that released it did not check the cause);
        "tripped": this one made HOST_SETUP_FAILS of its kind within HOST_SETUP_WINDOW_S (by the failures' own times) on this host: the host is marked down (the event and alarm
        of any host failure) and the store event names the kind, the run keys and their times; this failure is charged as the ones before it were;
        "counted": charged as today (also every failure of the local host, which is not held by this rule). Another kind has its own count: three of it trip it separately."""
        with self._lock:
            sp = self.specs.get(host)
            if sp is None or not sp.remote:      # the local host is never probed, so nothing would release it (`probe` is the release): its failures are charged as today
                return "counted"
            if host in self.down:
                return "held"
            again = kind in self._setup_tripped.get(host, ())
            if not again:
                seen = sorted([*self._setup_fails.get(host, []), (at, kind, run_key)])
                seen = [f for f in seen if f[0] >= seen[-1][0] - HOST_SETUP_WINDOW_S]           # `seen` is in time order: older than the latest by more than the window can no longer be in one
                self._setup_fails[host] = seen
                same = [f for f in seen if f[1] == kind]
                hit = next((same[i - HOST_SETUP_FAILS + 1:i + 1] for i in range(HOST_SETUP_FAILS - 1, len(same))
                            if same[i][0] - same[i - HOST_SETUP_FAILS + 1][0] <= HOST_SETUP_WINDOW_S), None)
                if hit is None:
                    return "counted"
                self._setup_fails[host] = [f for f in seen if f[1] != kind]
                self._setup_tripped.setdefault(host, set()).add(kind)
        if again:
            self.mark_down(host, f"{kind} failed again before the agent started ({run_key}) after the host was released: it is not fixed")
            return "held"
        when = ", ".join(f"{k} at {dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()}" for t, _, k in hit)
        self.mark_down(host, f"{len(hit)} failures of one kind before the agent started within {HOST_SETUP_WINDOW_S:g} s ({kind})")
        self._event(self._now(), "host_setup_failures", None,
                    f"{host}: {len(hit)} failures of one kind before the agent started within {HOST_SETUP_WINDOW_S:g} s: {kind}: {when}. The host is held as a failed probe holds it "
                    f"(a good probe after {getattr(self.cfg, 'host_pause_s', 300.0):g} s releases it); no further attempt is charged for a failure of this kind there until a run on it gets "
                    f"past setup, and the host is held again at once if one comes")
        return "tripped"

    def note_past_setup(self, host: str) -> None:
        """A run on `host` returned a record (its sandbox, its knowledge plane and its agent loop all ran): the kinds that tripped it are not its problem now, so each needs its own
        three again. No failure clears them: an endpoint failure may come before any sandbox."""
        with self._lock:
            self._setup_tripped.pop(host, None)

    def add_orphan(self, key: str, o: dict) -> None:
        with self._lock:
            self.orphans[key] = {**o, "added_epoch": time.time()}
            self._persist(dict(self.orphans))
        self._event(self._now(), "host_orphan", o.get("model"), f"{o['run_key']} on {o['host']}: counted as in flight until the host shows it gone")

    # -- the prober
    def probe(self, host: str) -> Probe:
        t = self.transports[host]
        asked = time.time()                    # the live list is the host's as of now: an orphan added later is not judged by it
        try:
            rc, out, err = t.call(["probe"] + (["--image", self.image_id] if self.image_id else []), timeout=30)
            if rc != 0:
                raise TransportError(f"probe exit {rc}: {(err or b'').decode(errors='replace')[-200:]}")
            d = json.loads(out)
            eps = d.get("endpoints")
            p = Probe(self._mono(), True, None, d.get("mem_available"), d.get("disk_free_gib"), list(d.get("live", [])),
                      d.get("tree"), d.get("image_ok"), [e for e in eps if isinstance(e, dict)] if isinstance(eps, list) else None,
                      d.get("pool") if isinstance(d.get("pool"), dict) else None, dict(d.get("d_use") or {}), list(d.get("unreaped") or []))
        except (TransportError, ValueError) as e:
            p = Probe(self._mono(), False, f"{type(e).__name__}: {e}")
        with self._lock:
            self.probes[host] = p
            if p.ok and host in self.down and self._mono() >= self.pause_until.get(host, 0):
                why = self.down.pop(host)
                self._event(self._now(), "host_up", None, f"{host}: reachable again after: {why}")
            ended = []
            if p.ok:
                live = set(p.live)
                ended = [(k, o) for k, o in self.orphans.items()
                         if o["host"] == host and o["run_dir"] not in live and float(o.get("added_epoch", 0.0)) < asked]
        for k, o in ended:                     # outside the lock: it pulls the run's dir. Before the orphan goes, so its retry finds its usage in place
            try:
                self._on_orphan_end(k, o)
            except Exception:  # noqa: BLE001 - the attempt's usage stays marked incomplete
                log.exception("the end of orphan %s", k)
            with self._lock:
                self.orphans.pop(k, None)
                self._persist(dict(self.orphans))
            self._event(self._now(), "host_orphan_ended", o.get("model"), f"{o['run_key']} on {host}: no live worker and no sandbox left")
        return p

    def waiting(self, option: str) -> dict[str, int | None]:
        """Runs waiting for a slot user of `option` on each remote host, from its last good probe (None: unknown there)."""
        with self._lock:
            out: dict[str, int | None] = {}
            for h, s in self.specs.items():
                if s.remote:
                    p = self.probes.get(h)
                    pool = p.pool if p is not None and p.ok else None
                    out[h] = None if pool is None or "_error" in pool else int((pool.get(option) or {}).get("waiting", 0))
            return out

    def option_cap(self, host: str, option: str) -> int | None:
        s = self.specs.get(host)
        return None if s is None else s.option_caps.get(option)

    def endpoints_of(self, host: str) -> list[dict] | None:
        with self._lock:
            p = self.probes.get(host)
            return None if p is None or not p.ok else p.endpoints

    def slot_probe(self, host: str, entry: dict, no_fp_models: Iterable[str] = ()):
        """The slot-equality read of one slot, made FROM the host whose models use it (slot_equality.http_probe there)."""
        from .slot_equality import Obs
        e = {k: v for k, v in entry.items() if k != "_host"}
        try:
            rc, out, err = self.transports[host].call(["slotprobe", "--no-fp", ",".join(sorted(no_fp_models))],
                                                      stdin=json.dumps(e).encode(), timeout=60)
            if rc != 0:
                raise TransportError(f"slotprobe exit {rc}: {(err or b'').decode(errors='replace')[-200:]}")
            return Obs(**json.loads(out))
        except (TransportError, ValueError, TypeError) as ex:
            return Obs(str(e.get("slot")), str(e.get("model")), e.get("backend_job"), error=f"read from {host} failed: {ex}"[:200])

    def fail_probes(self, why: str) -> None:
        """Every remote host's state becomes a failed probe: held until its next good one."""
        with self._lock:
            for h, s in self.specs.items():
                if s.remote:
                    self.probes[h] = Probe(self._mono(), False, why)

    def probe_all(self) -> None:
        for h, s in self.specs.items():
            if s.remote:
                self.probe(h)

    def snapshot(self) -> dict:
        with self._lock:
            return {"down": dict(self.down), "orphans": sorted(o["run_key"] + "@" + o["host"] for o in self.orphans.values()),
                    "probes": {h: {"ok": p.ok, "why": p.why, "mem_available_gib": None if p.mem_available is None else round(p.mem_available / 1024 ** 3, 2),
                                   "disk_free_gib": p.disk_free_gib, "live": len(p.live), "endpoints_readable": p.endpoints is not None,
                                   "pool": p.pool, "unreaped": len(p.unreaped)}
                               for h, p in self.probes.items()},
                    "holds": dict(self._held)}


def merge_endpoints(cfg: Any, local: list[dict] | None, remote: dict[str, list[dict] | None]) -> list[dict] | None:
    """One slot list for the dispatcher: each model's slots from ITS host's own endpoints.json (each host has its own site_a supervisor on
    the same local ports, so a slot's state is the one its runs will see). A remote entry is tagged `_host`. None only if no host's file
    could be read."""
    keys_on: dict[str, set[str]] = {}
    for m, h in cfg.model_host.items():
        k = cfg.open_models.get(m)
        if k:
            keys_on.setdefault(h, set()).add(k)
    lh = local_host(cfg)
    out: list[dict] = []
    seen = False
    for h, entries in [(lh, local), *remote.items()]:
        if entries is None:
            continue
        seen = True
        for e in entries:
            if e.get("model") in keys_on.get(h, set()):
                out.append(e if h == lh else {**e, "_host": h})
    return out if seen else None


# ---- the executor that routes a run to its host ----------------------------------------------------------------------
class RemoteHarnessError(RuntimeError):
    """The remote harness raised something that is not infra: a harness error, as it would be locally."""


def _safe_extract(data: bytes, dest: Path) -> tuple[int, int]:
    """Unpacks a pulled run dir and checks what landed: (files, bytes), which the host must match before it removes its copy."""
    n = b = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        members = tf.getmembers()
        for m in members:
            p = Path(m.name)
            if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()):
                raise RemoteHarnessError(f"refused member {m.name!r} in the pulled run dir")
        tf.extractall(dest, filter="data")
        for m in members:
            if m.isfile():
                got = (Path(dest) / m.name).stat().st_size
                if got != m.size:
                    raise RemoteHarnessError(f"{m.name}: {got} bytes landed of {m.size}")
                n, b = n + 1, b + m.size
    return n, b


class HostRouter:
    """The campaign's executor when there are two hosts. A run of a local model goes to `local_exec` unchanged; one of a
    remote model is started on its host (idempotent per run dir), waited for (a dropped connection reattaches; it is LOST only
    after `remote_lost_s` without reaching the host), and its run dir pulled back into the same path here."""

    def __init__(self, local_exec: Callable, transports: dict[str, Transport] | None = None, *, sleep: Callable[[float], None] = time.sleep,
                 mono: Callable[[], float] = time.monotonic, load_record: Callable | None = None):
        self.local_exec, self._transports = local_exec, transports
        self._still_live: set[str] = set()     # run dirs whose result came with a lease in quarantine (remote.cmd_work)
        self._sleep, self._mono = sleep, mono
        self._load = load_record

    def still_live(self, run_dir: Path) -> bool:
        """The run ended, but its sandbox's teardown was not proven on its host: the scheduler keeps it counted (an orphan) until the host's
        worker, which holds the slot user meanwhile, is gone."""
        return str(run_dir) in self._still_live

    def transports(self, cfg: Any) -> dict[str, Transport]:
        if self._transports is None:
            self._transports = {n: SshTransport(s.ssh or []) for n, s in host_specs(cfg).items() if s.remote}
        return self._transports

    def __call__(self, run, attempt: int, run_dir: Path, slot: str, cfg: Any, provider_cap: int | None = None,
                 concurrency_at_start: int | None = None):
        host = host_of(cfg, run.model)
        spec = host_specs(cfg).get(host)
        if spec is None or not spec.remote:
            kw = {"provider_cap": provider_cap}
            if concurrency_at_start is not None and _accepts(self.local_exec, "concurrency_at_start"):
                kw["concurrency_at_start"] = concurrency_at_start
            return self.local_exec(run, attempt, run_dir, slot, cfg, **kw)
        t = self.transports(cfg)[host]
        payload = json.dumps({"run": {"instance_id": run.instance_id, "option": getattr(run.option, "value", run.option),
                                      "layout": getattr(run.layout, "value", run.layout), "model": run.model, "seed": run.seed},
                              "attempt": attempt, "slot": slot, "provider_cap": provider_cap, "concurrency_at_start": concurrency_at_start,
                              "slot_keys": sorted(spec.slot_keys), "cfg": _cfg_dict(cfg), "host": host}).encode()
        lost_answer = False
        for i in range(3):                     # start is idempotent per run dir, so a retry after a dropped connection never starts it twice
            try:
                rc, out, err = t.call(["start", str(run_dir)], stdin=payload, timeout=120)
                break
            except TransportError as e:
                lost_answer = True
                if i == 2:                     # the start may have reached the host and its answer been lost: not known to be unstarted
                    raise InfraError(HOST_KIND, f"{UNCERTAIN}{host}: {e}") from e
                self._sleep(2.0 * (i + 1))
        if rc != 0:                            # after a lost answer a refusal is no proof that nothing runs: uncertain, kept as an orphan
            prefix = UNCERTAIN if lost_answer else NOT_STARTED
            raise InfraError(HOST_KIND, f"{prefix}{host}: start exit {rc}: {(err or b'').decode(errors='replace')[-300:]}")
        res = self._wait(t, host, run_dir, cfg)
        if res.get("still_live"):
            self._still_live.add(str(run_dir))
        facts = self._pull(t, host, run_dir)
        if not res.get("still_live"):          # a run whose teardown was not proven keeps its dir there with its worker (delta pass, finding 4)
            self._clean(t, run_dir, facts)
        kind = res.get("kind")
        if kind == "infra":
            raise InfraError(res["infra_kind"], res.get("detail", ""))
        if kind == "harness_error":
            raise RemoteHarnessError(res.get("detail", "remote harness error"))
        if kind != "record":
            raise RemoteHarnessError(f"unknown remote result {res!r}")
        load = self._load
        if load is None:
            from icsa.pipeline.loadrec import read_record
            load = lambda d: read_record(d)[0]      # noqa: E731
        return load(Path(run_dir))

    def _wait(self, t: Transport, host: str, run_dir: Path, cfg: Any) -> dict:
        lost_s = getattr(cfg, "remote_lost_s", 600.0)
        unreachable_since: float | None = None
        last = ""
        while True:
            try:
                rc, out, err = t.call(["wait", str(run_dir), "--timeout", "60"], timeout=120)
            except TransportError as e:
                rc, last = None, str(e)
            if rc == 0:
                return json.loads(out)
            if rc == 3:                        # still running
                unreachable_since = None
                continue
            if rc == 4:                        # what it left is the only record of why: pulled before anything removes it (best effort)
                try:
                    self._pull(t, host, run_dir)
                except (InfraError, RemoteHarnessError, OSError) as e:
                    log.warning("the dead worker's run dir %s was not pulled: %s", run_dir, e)
                raise InfraError(HOST_KIND, f"{WORKER_DIED}{host}: the worker ended without a result")
            if rc is not None:
                last = f"wait exit {rc}: {(err or b'').decode(errors='replace')[-200:]}"
            now = self._mono()
            if unreachable_since is None:
                unreachable_since = now
            if now - unreachable_since >= lost_s:
                raise InfraError(HOST_KIND, f"{LOST}{host}: unreachable for {lost_s:g} s ({last})")
            self._sleep(min(10.0, max(0.5, lost_s / 20)))

    def _clean(self, t: Transport, run_dir: Path, facts: tuple[int, int]) -> None:
        """After a pull that unpacked: the host's copy goes, or run dirs fill its disk over a campaign (the pulled copy here is the record). The host removes it only
        if its own count matches `facts`, what landed here (no run output goes without its copy checked by file count and bytes: lane-common). Best effort: the
        host keeps a dir whose run still has a live worker, and a failed call only leaves it there."""
        try:
            rc, _, err = t.call(["clean", str(run_dir), "--files", str(facts[0]), "--bytes", str(facts[1])], timeout=120)
            if rc != 0:                        # not silent: a dir left there holds the host's disk, which its hold then shows
                log.warning("clean of %s refused (exit %s): %s", run_dir, rc, (err or b"").decode(errors="replace")[-200:])
        except TransportError as e:
            log.warning("clean of %s not sent: %s", run_dir, e)

    def _pull(self, t: Transport, host: str, run_dir: Path) -> tuple[int, int]:
        try:
            rc, out, err = t.call(["pack", str(run_dir)], timeout=600)
        except TransportError as e:
            raise InfraError(HOST_KIND, f"{LOST}{host}: the run ended but its run dir could not be pulled: {e}") from e
        if rc != 0:
            raise InfraError(HOST_KIND, f"{LOST}{host}: pack exit {rc}")
        Path(run_dir).mkdir(parents=True, exist_ok=True)
        return _safe_extract(out, Path(run_dir))


def _accepts(fn: Callable, name: str) -> bool:
    import inspect
    try:
        ps = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    return name in ps or any(p.kind is p.VAR_KEYWORD for p in ps.values())


def _cfg_dict(cfg: Any) -> dict:
    d = dataclasses.asdict(cfg) if dataclasses.is_dataclass(cfg) else dict(vars(cfg))
    return json.loads(json.dumps(d, default=str))
