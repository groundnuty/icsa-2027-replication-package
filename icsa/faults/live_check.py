"""The live check of the platform records before calibration (#11 part 2; science on #2, item 3).

A T, a D and an M read of the SAME S1 file, each through the real sandbox (the campaign's image, gate and oneclient
sidecar), each as its own leased slot user, each sandbox with its own run key (the gate adds it as X-ICSA-Run to every
T and D request; M's oneclient does not pass the gate). Plus, for M, the read patterns of the two cache conditions:

- warm_buffer ("the days to be read are read once before the run"): a file read in one exec, then read again in a
  second exec after a pause, with the sidecar's bridge rx counted around the second exec, so that a cache-served read is
  shown to BE cache-served (about 0 bytes from the provider), not assumed;
- prefetch_on: a separate M sandbox with the oneclient arguments given on the command line.

And a header-only read (bytes below the first data byte, from the HDF5 chunk index) for T and M, the calibration's
`header_only` fault.

Writes `<out>/<run_key>/live.json` per sandbox (UTC stamps in ms around every read, in the sandbox and on the host; the
slot, its user id and the lease interval; the sidecar's rx per exec) plus the gate log and, for M, the perf CSV. The
token is never printed or recorded. Unsandboxed (docker and the federation):

    python -m icsa.faults.live_check --out DIR --image TAG [--only T,D,M,Mpre,T2h,M2h,T2skip,M2skip,M2skippre]

(T2h, M2h: a header-only read of the one S2 file, bytes below its first chunk, as T and as M.)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import time
from pathlib import Path

from icsa.records import Layout, Option

S1_LOCAL = Path("/mnt/volume2/icsa-2027/s1z")
S2_LOCAL = Path("/mnt/volume2/icsa-2027/s2z/sst_s2.nc")
VAR = "analysed_sst"
PREFIX = "s11live-"
SAME_FILE = "sst_19820105.nc"        # read by T, D and M (cold)
HEADER_FILE = "sst_19820106.nc"      # header-only read, T and M
WARM_FILE = "sst_19820107.nc"        # M: read, pause, read again
INPROC_FILE = "sst_19820108.nc"      # M: read twice in one process
PREFETCH_FILE = "sst_19820111.nc"    # M with the prefetch arguments (the superseded 10 s run read 0109 and 0110)
PREFETCH_HEADER_FILE = "sst_19820112.nc"
# prefetch_on as science froze it (#11, 21:40Z, amendment 12); calibration uses exactly these
PREFETCH_ON_ARGS = ["--read-buffer-prefetch-duration", "30", "--read-buffer-max-size", "1073741824"]
SKIP_DAYS = (200, 201, 202)          # S2: read chunk 200, skip 201, read 202 (1982: never required)
LIVE_TAG = "ICSA_LIVE "
QUARANTINED_UNTIL: list[float] = []   # token expiries of quarantined slots in this process: any entry stops new sandboxes, and none of them ends a quarantine
QUARANTINED_LEASES: list = []         # their leases: `held` until the teardown is proven (slot_lease.Lease.quarantine)
WARM_PAUSE_S = 10


def utc_ms() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def data_start(name: str | None) -> int:
    """First data byte, from the HDF5 chunk index of the local verified copy (name None: the S2 file)."""
    from .units import _dataset_spans
    if name is None:
        return min(a for _, a, _ in _dataset_spans(S2_LOCAL, VAR))
    spans = _dataset_spans(S1_LOCAL / name, VAR)
    if len(spans) != 1:
        raise ValueError(f"{name}: expected one chunk, found {len(spans)}")
    return spans[0][1]


_SNIPPET = r'''
import json as _j, datetime as _dt
def _u():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds")
_OPS = _j.loads(OPS_JSON)
_loc = os.environ["ICSA_DATASET_LOCATION"]
os.makedirs("/work/data", exist_ok=True)
_p = Paths(ACCESS[_OPS["option"]], _OPS["layout"], _loc, "/work/data")
_out = []
for _op in _OPS["ops"]:
    _t0 = _u()
    _n = 0
    if _op["kind"] == "full":          # the campaign's mechanism: open_path, then load the data variable
        _ds, _f = _p.open_path(_op["name"])
        _n = int(_ds[_op["var"]].values.size)
        _ds.close()
        if _f is not None:
            _f.close()
    elif _op["kind"] == "bytes":       # the calibration's mechanism: bytes [0, n) of the named file
        _path = _p.remote(_op["name"])
        _fh = _p.fs.open(_path, "rb") if _p.fs is not None else open(_path, "rb")
        try:
            _n = len(_fh.read(_op["n"]))
        finally:
            _fh.close()
    elif _op["kind"] == "ranges":      # ONE open file object, as an agent keeps it: seek + read per range
        _path = _p.remote(_op["name"])
        _fh = _p.fs.open(_path, "rb") if _p.fs is not None else open(_path, "rb")
        try:
            for _a, _b in _op["ranges"]:
                _fh.seek(_a)
                _n += len(_fh.read(_b - _a))
                time.sleep(_op.get("gap_s", 0))
        finally:
            _fh.close()
    elif _op["kind"] == "sleep":
        time.sleep(_op["s"])
    else:
        raise ValueError(_op)
    _out.append({**_op, "start_utc": _t0, "end_utc": _u(), "got": _n,
                 "access_type": _p.access_type_xattr(_op.get("name")) if _op["kind"] != "sleep" else None})
print("ICSA_LIVE " + _j.dumps(_out), flush=True)
'''


def exec_code(option: str, ops: list[dict], layout: str = "S1") -> str:
    from icsa.scripted import bundle
    payload = json.dumps({"option": option, "layout": layout, "ops": ops})
    return f"{bundle.script_source()}\nOPS_JSON = {payload!r}\n{_SNIPPET}"


def plans(only: set[str], prefetch_args: list[str]) -> list[dict]:
    hdr = {HEADER_FILE: data_start(HEADER_FILE), PREFETCH_HEADER_FILE: data_start(PREFETCH_HEADER_FILE)}
    full = lambda n: {"kind": "full", "name": n, "var": VAR}            # noqa: E731
    head = lambda n: {"kind": "bytes", "name": n, "n": hdr[n], "what": "header_only"}   # noqa: E731
    whole = lambda n: {"kind": "bytes", "name": n, "n": (S1_LOCAL / n).stat().st_size, "what": "whole_bytes"}  # noqa: E731
    p = [
        {"id": "T", "option": "T", "execs": [[full(SAME_FILE), {"kind": "sleep", "s": 3}, head(HEADER_FILE)]]},
        {"id": "D", "option": "D", "execs": [[full(SAME_FILE)]]},
        {"id": "M", "option": "M", "execs": [
            [full(SAME_FILE), {"kind": "sleep", "s": 3}, head(HEADER_FILE), {"kind": "sleep", "s": 3}, full(WARM_FILE)],
            # after WARM_PAUSE_S on the host: the same files again, in a new process (warm_buffer as the calibration runs it)
            [full(WARM_FILE), {"kind": "sleep", "s": 3}, full(SAME_FILE)],
            # one process, the same file twice, as raw bytes
            [whole(INPROC_FILE), {"kind": "sleep", "s": 3}, whole(INPROC_FILE)]]},
        {"id": "Mpre", "option": "M", "extra_args": prefetch_args, "execs": [
            [full(PREFETCH_FILE), {"kind": "sleep", "s": 3}, head(PREFETCH_HEADER_FILE)]]},
    ]
    if only & {"T2skip", "M2skip", "M2skippre"}:   # S2: chunk 200 read, 201 skipped, 202 read, through one open file
        from .units import _dataset_spans
        sp = {t: (a, b) for t, a, b in _dataset_spans(S2_LOCAL, VAR) if t in SKIP_DAYS}
        rng = {"kind": "ranges", "name": None, "ranges": [list(sp[SKIP_DAYS[0]]), list(sp[SKIP_DAYS[2]])], "gap_s": 1,
               "skipped": list(sp[SKIP_DAYS[1]]), "what": "middle_chunk_skipped"}
        p += [{"id": "T2skip", "option": "T", "layout": "S2", "execs": [[rng]]},
              {"id": "M2skip", "option": "M", "layout": "S2", "execs": [[rng]]},
              {"id": "M2skippre", "option": "M", "layout": "S2", "extra_args": PREFETCH_ON_ARGS, "execs": [[rng]]}]
    if only & {"T2h", "M2h"}:                 # S2: the header only (bytes below the first chunk), T and M
        s2h = {"kind": "bytes", "name": None, "n": data_start(None), "what": "header_only"}
        p += [{"id": "T2h", "option": "T", "layout": "S2", "execs": [[s2h]]},
              {"id": "M2h", "option": "M", "layout": "S2", "execs": [[s2h]]}]
    return [x for x in p if x["id"] in only]


def _sidecar_rx(side: str, mac: str) -> int | None:
    from icsa.scripted import metrics
    try:
        return metrics.iface_by_mac(metrics.iface_counters(side), mac)["rx"]
    except Exception:  # noqa: BLE001 - unknown is recorded as unknown
        return None


def run_plan(plan: dict, out_root: Path, image: str, stamp: str) -> dict:
    """One sandbox under one slot lease. `live.json` is written on every path, with the token redacted from the whole
    record (exception text and stderr included)."""
    option = plan["option"]
    run_key = f"{PREFIX}{stamp}-{plan['id']}"
    out = out_root / run_key
    out.mkdir(parents=True, exist_ok=False)
    r: dict = {"run_key": run_key, "plan": plan["id"], "option": option, "layout": plan.get("layout", "S1"), "image": image,
               "oneclient_extra_args": plan.get("extra_args") or [], "execs": [], "errors": []}
    secret: list[str] = []          # the run's token, kept only to redact it from what is written
    lease = None
    try:
        from icsa.harness.config import load_config
        from icsa.harness.real_sandbox import sandbox_config
        from icsa.sandbox import Sandbox
        from icsa.sandbox.config import pin_image
        from icsa.scripted import federation as F
        from icsa.scripted import metrics, tokens
        from icsa.scripted.slot_tokens import SlotTokens
        # the campaign's own builder and limits (config/harness.toml [sandbox_limits]); untraced: the tracer runs in the
        # agent container and does not change what the provider or Traefik log
        cfg = sandbox_config(image, pin_image(image), sandbox_limits=load_config().sandbox_limits)
        r["host_aliases"] = dict(sorted((getattr(cfg, "host_aliases", None) or {}).items()))
        from icsa.sandbox import hostops
        r["host"] = hostops.host_facts()
        with SlotTokens().lease(run_key, option) as lease:
            secret.append(lease._lt.token)
            _hold(lease, r, plan, option, run_key, cfg, out, Sandbox, F, metrics, tokens)
    except Exception as e:  # noqa: BLE001 - setup or lease failure: recorded, the record is still written
        r["errors"].append(f"{type(e).__name__}: {e}")
    finally:
        if lease is not None:
            try:
                r["onedata_slot"] = lease.final_record()
            except Exception as e:  # noqa: BLE001
                r["errors"].append(f"slot record: {type(e).__name__}: {e}")
        r["errors"] = [_redact(x, *secret)[:800] for x in r["errors"]]
        (out / "live.json").write_text(_redact(json.dumps(r, indent=1, default=str), *secret))
    return r


def _redact(s: str, token: str | None = None) -> str:
    """Redact BEFORE any truncation, so no token prefix survives a cut."""
    return s.replace(token, "<token>") if token else s


def _hold(lease, r, plan, option, run_key, cfg, out, Sandbox, F, metrics, tokens) -> None:
    """The body under the slot lease. A sandbox that may outlive its teardown (a failed stop, or a failed start that
    left one behind: `exc.sandbox`, also on an interrupt) may still use the token, so the slot is QUARANTINED until its
    teardown is proven, never released to another run (the harness's `release_or_quarantine` rule); the leased_token
    context's release is then a no-op and attaches the retried teardown, and `main` keeps the process (and so the slot's lock) alive until then."""
    from icsa.harness.real_sandbox import _epoch
    from icsa.sandbox import route                   # imported in run_plan too, but this is its own scope: without it every live check ended in a NameError
    lt = lease._lt                                   # the LeasedToken behind the scripted lease: its harness Lease and record
    slot_lease, valid_until = lt.lease, _epoch(lt.record.valid_until_utc)
    sbx = None

    def quarantine(why: str) -> None:
        r["errors"].append(why)
        r["quarantined"], r["quarantine_until_epoch"] = True, valid_until
        QUARANTINED_UNTIL.append(valid_until)
        QUARANTINED_LEASES.append(slot_lease)        # main holds the process (the slot's lock) until its teardown is proven, on every exit
        slot_lease.quarantine(valid_until)

    r.update(slot=lease.slot, user_id=lease.subject, lease_start_utc=utc_ms())
    with tokens.held(lease):
        try:
            try:
                from icsa.sandbox import route
                via = route.fault_calibration_via(option)
                r["provider_route"] = route.route_name(via)
                dc = F.data_config(F.MAIN, option, via=via, perf_log=(option == "M"),
                                   oneclient_extra_args=plan.get("extra_args") or None)
                sbx = Sandbox.start(run_key, Option(option), Layout(r["layout"]), dc, cfg)
                del dc                                      # holds the token: never printed, never kept
                r["sandbox_up_utc"] = utc_ms()
                meta = sbx.metadata()
                mount = meta.get("mount_kind") == "oneclient"
                side = f"{sbx.name}-oneclient"
                mac = metrics.bridge_mac(side) if mount else None
                for i, ops in enumerate(plan["execs"]):
                    if i and option == "M":
                        time.sleep(WARM_PAUSE_S)
                    rx0 = _sidecar_rx(side, mac) if mount else None
                    h0 = utc_ms()
                    ex = sbx.exec(exec_code(option, ops, r["layout"]), 600)
                    h1 = utc_ms()
                    rx1 = _sidecar_rx(side, mac) if mount else None
                    res = None
                    for line in ex.stdout.splitlines():
                        if line.startswith(LIVE_TAG):
                            res = json.loads(line[len(LIVE_TAG):])
                    e = {"host_start_utc": h0, "host_end_utc": h1, "exit_code": ex.exit_code, "ops": res,
                         "sidecar_rx_bytes": None if rx0 is None or rx1 is None else rx1 - rx0}
                    if ex.exit_code != 0 or res is None:
                        e["stderr_tail"] = _redact(ex.stderr or "", lt.token)[-1500:]
                        r["errors"].append(f"exec {i} failed: exit {ex.exit_code}")
                    r["execs"].append(e)
                r["sandbox"] = {k: v for k, v in sbx.metadata().items() if "token" not in k.lower()}
                r["collected"] = sbx.collect(out)
            except BaseException as e:  # recorded; an interrupt is re-raised after the record and the quarantine
                r["errors"].append(_redact(f"{type(e).__name__}: {e}", lt.token))
                if sbx is None and getattr(e, "sandbox", None) is not None:
                    quarantine("a failed start left a sandbox behind: slot quarantined until its teardown is proven")
                if not isinstance(e, Exception):
                    raise
        finally:
            if sbx is not None:
                try:
                    sbx.stop()
                except BaseException as e:
                    r["errors"].append(_redact(f"teardown failed: {type(e).__name__}: {e}", lt.token))
                    quarantine("teardown failed: slot quarantined until its teardown is proven")
                    if not isinstance(e, Exception):
                        raise
            r["lease_end_utc"] = utc_ms()


def main() -> None:
    from icsa.sandbox.termination import exit_on_sigterm
    exit_on_sigterm()     # a SIGTERM is an orderly exit: `finally` -> `stop()`, the summary, the quarantine hold
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--image", required=True)
    ap.add_argument("--only", default="T,D,M")
    ap.add_argument("--prefetch-args", default="")
    a = ap.parse_args()
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).parent).stdout.strip()
    stamp = time.strftime("%H%M%S", time.gmtime())
    a.out.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(","))
    pre = shlex.split(a.prefetch_args)
    if "Mpre" in only and not pre:
        pre = list(PREFETCH_ON_ARGS)          # the frozen prefetch_on flags
    summary = {"code_sha": sha, "image": a.image, "started_utc": utc_ms(), "runs": []}
    try:
        for plan in plans(only, pre):
            r = run_plan(plan, a.out, a.image, stamp)
            summary["runs"].append({k: r.get(k) for k in ("run_key", "option", "slot", "user_id", "lease_start_utc",
                                                           "lease_end_utc", "errors")})
            print(json.dumps(summary["runs"][-1]), flush=True)
            if r.get("quarantined"):        # a sandbox may still be up: stop here, it needs a look before anything else runs
                summary["stopped"] = f"{r['run_key']}: a sandbox survived its teardown"
                break
    finally:
        try:
            summary["ended_utc"] = utc_ms()
            (a.out / f"SUMMARY-{stamp}.json").write_text(json.dumps(summary, indent=1))
        finally:
            hold_quarantines()
    if summary.get("stopped"):
        raise SystemExit(summary["stopped"])


_sleep, _now = time.sleep, time.time      # tests replace these


def _say(msg: str) -> None:
    """Best effort: a closed stdout must never end a quarantine hold."""
    try:
        print(msg, flush=True)
    except Exception:  # noqa: BLE001
        pass


def hold_quarantines() -> None:
    """A quarantined slot's lock lives as long as this process: on every exit path (an interrupt included) hold it until
    its teardown is proven, so no other run gets that slot user while a surviving sandbox may still use the token (the lead's ruling, 2 Nov: a mounted oneclient may read past
    the token's expiry, so that is no end). A teardown that never finishes keeps this process here, saying so every 10 minutes: only an operator's kill -9 ends that."""
    if not any(getattr(lease, "held", False) for lease in QUARANTINED_LEASES):
        return
    from icsa.sandbox.termination import raise_if_requested, sigterm_deferred
    pending: BaseException | None = None
    with sigterm_deferred():               # a SIGTERM raises nothing in here: it is honoured after the hold, as an interrupt is
        waited = 0
        while any(getattr(lease, "held", False) for lease in QUARANTINED_LEASES):
            if waited % 10 == 0:
                _say(f"holding {sum(bool(getattr(lease, 'held', False)) for lease in QUARANTINED_LEASES)} quarantined slot(s) until their teardown is proven")
            waited += 1
            try:
                _sleep(60.0)
            except KeyboardInterrupt as e:     # deferred: the lock must outlive the sandbox; it is raised after the proof
                pending = e
                _say("interrupt deferred until the quarantined sandbox is shown gone (kill -9 drops the slot's lock)")
    if pending is not None:
        raise pending
    raise_if_requested()


if __name__ == "__main__":
    main()
