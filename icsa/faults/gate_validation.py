"""Amendment 17(c), check (ii): on the direct path, a validation set of scripted runs, fixed before it runs, on which the gate log must stand for Traefik's.

T and D x S1 and S2, cold and untraced: 5 runs per fault type observable on the gate record (what is observable on the Traefik record, which it stands in for), and 5
fault-free runs per cell. Every run also makes, besides its fault's reads, one short read (T: a range past a file's end), one cancelled transfer and one request the
gate refuses (T: a write; D: a `Range`). It passes if, on every run:

  * each request's `body_bytes` in the gate log equals the bytes the client itself received (urllib3's own count, inside the sandbox), exactly. A cancelled
    transfer is the one exception, since no server can see what its client read of a cut transfer, only what it handed to the socket: there the client's bytes
    are at most the gate's confirmed and unconfirmed bytes together, and the excess is reported (the rule the lead put to science on 2 Nov);
  * the frozen detector, run on the gate log read as the Traefik record (`records/gate.py`), flags exactly the injected days that no byte record can show as read:
    the masking model's omitted days less those the client's own read-ahead serves anyway (T's S2, amendment 12(c); elsewhere none is). The detector on the
    client's own record of what it received is reported beside it, so a difference is the gate's only if the client's record agrees with the model;
  * each run's cancelled transfer was a content read (HTTP 200 or 206, on the client's side and the gate's) cut at the length planned: an error response is no cancel.

The fault's reads are `calibrate.read_ops`, run by `calibrate.execute_run` on the campaign's own route (`via=None`: the direct port), as a calibration run is. The
extra requests come after them. The short read and the refused request go on days the fault leaves read, so they move no flag. A faulted run's cancelled transfer
goes on an omitted day the client's own read-ahead does not serve, and ends a seeded distance before its chunk does (amendment 22; `--cancel-on omitted`, the
default), where a gate that handed the rest of the chunk to the socket would credit the chunk and the detector would miss the flag. Scoring and `run` refuse a plan
in which a faulted run's cancel is anywhere else (`cancel_on read` stays for tests: a fault-free run has no omitted day, so it cancels on a read day in either).

    python -m icsa.faults.gate_validation plan  <out>          seals the set: validation_plan.json and its sha
    python -m icsa.faults.gate_validation run   <out> --image <image> [--concurrency 4]
    python -m icsa.faults.gate_validation score <out>          writes verdict.json; exit 0 only if the set passes
    python -m icsa.faults.gate_validation score <out> --rule cut   the cut rule below: writes verdict-cut.json, never verdict.json; exit 0 only if it passes

The cut rule (`--rule cut`; science, #34, 15:39Z and 19:02Z) is for a gate that logs how each client connection ended (`records/gate.py`, `gate_cuts`; `cuts.py`). A response
the client cut credits nothing and flags nothing, and a day whose only covering response was cut is undecided, out of recall and precision. The set passes under it if, on every
run: the run's cancel is marked cut; no other response is; the cancel's day is undecided; the flags on the decided days are exactly the expected ones less the undecided days;
and the byte checks above hold, unchanged. A cancel that leaves at most BAND_BYTES of its body unread is reported apart (`band`): what the kernel's counters can show of it is
not the gate's to answer for, so the marker's outcome and the cancel's own day do not count for such a run; every other check of it does. `registered` is the rule the sealed
set was scored with, and stays the default.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import hashlib
import json
import sys
import threading
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from ..records import Layout, Option
from .detector import DetectorSpec, detect
from .masking import masking
from .observability import Obs, applicable_faults, classify
from .records.base import Record
from .cuts import undecided_days
from .records.gate import CLOSE_KINDS, CUT_REASONS, gate_close_summary, gate_endings, parse_gate
from .scenarios import Condition, Fault, Scenario, make_scenario
from .units import Manifest, Required

CELLS = ((Option.T, Layout.S1), (Option.T, Layout.S2), (Option.D, Layout.S1), (Option.D, Layout.S2))
RUNS_PER_FAULT = 5
FAULT_FREE = 5
SEED = 20261102                 # fixed with the set, before any run
MAX_REPLICATES = 400            # T's S2 cases are drawn until 5 are fully observable; a fault that cannot reach 5 says so
MAX_ATTEMPTS = 3                # a run the host stopped is replaced, as a calibration run is
KEY_PREFIX = "s11val-"
CANCEL_BYTES = 65536
CANCEL_ON = ("omitted", "read")  # an omitted-day cancel is the validation set's; `read` is what a fault-free run does anyway, and no plan of faulted runs scores with it
NEAR_END = 524288               # "within about 0.5 MB of the chunk's end": where the gate's measured over-credit (up to ~0.3 MB in flight) could cross it
FAR_END = 8 * 1024 * 1024       # the furthest a spread cancel ends before its chunk's end (a chunk smaller than this bounds it)
MIN_DISTANCE = 4096             # the nearest: a cancel always ends before its chunk does
VAL_TAG = "ICSA_VAL "
RULES = ("registered", "cut")
BAND_BYTES = 8192               # a cancel that leaves at most this much of its body unread is "the band": the kernel's counters cannot tell it from a read to the end


def observable_faults(option: Option, layout: Layout) -> list[tuple[Fault, Obs]]:
    out = []
    for f in applicable_faults(layout, option):
        c = classify(f, layout, option, Record.TRAEFIK, Condition.COLD)
        if c.obs in (Obs.OBSERVABLE, Obs.PER_INSTANCE):
            out.append((f, c.obs))
    return out


def _extras(s: Scenario, omitted: frozenset[int], unserved: frozenset[int], required: Required, manifest: Manifest, cancel_on: str) -> dict:
    """The extra requests of a run: on days the fault leaves read (not in `omitted`), except an `omitted` plan's cancel, which goes on a day of `unserved`: an omitted day
    the client's read-ahead does not serve anyway (one it does serve credits nothing a missed flag could show). A run with none has its cancel on a read day."""
    read_days = [d for d in sorted(required.days) if d not in omitted]
    om = sorted(unserved)
    unit = lambda d: manifest.units[d]                       # noqa: E731
    size = lambda key: manifest.file(key).size               # noqa: E731
    x: dict = {}
    if read_days:
        key, a, b = unit(read_days[0])
        if s.option is Option.T:
            x["short"] = [key, size(key)]                      # 100 bytes before the end, asked 4,000 past it
        x["reject"] = [key, size(key)]
    on = om if cancel_on == "omitted" and om else read_days
    if on:
        key, a, b = unit(on[0])
        if s.option is Option.D:
            x["cancel"] = [key, None, None]                    # a whole-file download, cut by the client
        else:
            lo, hi = (0, size(key)) if s.layout is Layout.S1 else (a, b)
            x["cancel"] = [key, lo, hi]
        if cancel_on == "omitted" and om:                       # where it ends is set by `_spread_cancels`, which sees every cancel of the plan
            x["cancel_chunk"] = [a, b]
            x["cancel_lo"] = 0 if x["cancel"][1] is None or s.layout is Layout.S1 else a        # the file offset the transfer starts at
    return x


def _spread_cancels(runs: list[dict], seed: int) -> None:
    """Give every cancel of an `omitted` plan the end point that falls `cancel_distance` bytes before its chunk's end, the distances stratified log-uniformly
    from MIN_DISTANCE to FAR_END (cut to what the chunk allows) and dealt to the runs in an order drawn from the seed: so some end well before the chunk's end and
    some within NEAR_END of it, with nothing but the seed to choose."""
    import math
    import numpy as np
    idx = [i for i, r in enumerate(runs) if "cancel_chunk" in r["extras"]]
    rng = np.random.default_rng([seed, 17, len(idx)])
    order = rng.permutation(len(idx))
    jitter = rng.random(len(idx))
    for rank, k in enumerate(order):
        x = runs[idx[k]]["extras"]
        a, b = x["cancel_chunk"]
        lo = x["cancel_lo"]
        far = max(1, min(FAR_END, b - a - 1, b - lo - 1))          # inside the chunk, and at least one byte read
        near = max(1, min(MIN_DISTANCE, far // 8))
        u = (rank + jitter[k]) / len(idx)
        d = int(round(math.exp(math.log(near) + u * (math.log(far) - math.log(near)))))
        d = max(near, min(far, d))
        x["cancel_distance"] = d
        x["cancel_end"] = b - d
        x["cancel_read"] = b - d - lo


def plan(required: Required, manifests: dict, *, seed: int = SEED, cancel_on: str = "omitted") -> dict:
    if cancel_on not in CANCEL_ON:
        raise ValueError(f"cancel_on is one of {CANCEL_ON}, not {cancel_on!r}")
    runs, short = [], []
    for option, layout in CELLS:
        man = manifests[layout]
        for f, obs in observable_faults(option, layout) + [(Fault.NONE, Obs.OBSERVABLE)]:
            want = FAULT_FREE if f is Fault.NONE else RUNS_PER_FAULT
            kept = 0
            for r in range(MAX_REPLICATES):
                s = make_scenario(f, layout, option, Condition.COLD, r, seed)
                m = masking(s, required, man)
                expected = m.omitted - m.served_omitted
                if f is not Fault.NONE and not expected:        # nothing a byte record could show: a fault-free run under another name, or masked
                    continue
                runs.append({"order": len(runs), "fault": f.value, "option": option.value, "layout": layout.value, "replicate": r, "sid": s.sid,
                             "expected_flags": sorted(expected), "served_anyway": sorted(m.served_omitted),
                             "extras": _extras(s, m.omitted, expected, required, man, cancel_on)})
                kept += 1
                if kept == want:
                    break
            if kept < want:
                short.append({"fault": f.value, "option": option.value, "layout": layout.value, "kept": kept})
    if cancel_on == "omitted":
        _spread_cancels(runs, seed)
    body = {"amendment": "17(c) (ii)", "seed": seed, "cancel_on": cancel_on, "runs": runs, "short_of_runs": short,
            "rule": "per-request body_bytes equal the client's received bytes, a cancelled transfer bounded; the detector on the gate log flags exactly expected_flags"}
    if cancel_on == "omitted" and (bad := plan_problems(body, manifests)):
        raise ValueError(f"the plan built is not one amendment 22 allows: {bad[:3]}")
    sha = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return {**body, "sha256": sha}


def plan_problems(sealed: dict, manifests: dict) -> list[str]:
    """Why a sealed plan cannot be the validation set (amendment 22): every faulted run's cancel falls on one of its expected-flag days, an omitted day the client does not
    serve anyway, and ends inside that day's chunk, before its end. Read from the runs' own extras, not from the plan's `cancel_on`, which is a label. A fault-free run
    has no omitted day and is not asked for one."""
    out = []
    if sealed.get("cancel_on") != "omitted":
        out.append(f"the plan is sealed with cancel_on={sealed.get('cancel_on')!r}, not 'omitted': its cancels cannot show an over-count that credits an omitted chunk")
    for r in sealed["runs"]:
        if r["fault"] == "none":
            continue
        x, man = r["extras"], manifests[Layout(r["layout"])]
        try:
            key, (a, b) = x["cancel"][0], x["cancel_chunk"]
            end, lo, read, dist = x["cancel_end"], x["cancel_lo"], x["cancel_read"], x["cancel_distance"]
        except (KeyError, IndexError, TypeError, ValueError):
            out.append(f"{r['sid']}: no omitted-day cancel (its cancel is on a read day, where an over-count shows no flag)")
            continue
        if not [d for d in r["expected_flags"] if tuple(man.units.get(d, ())) == (key, a, b)]:
            out.append(f"{r['sid']}: its cancel's chunk {key} [{a}, {b}) is no omitted, unserved day: the expected flags are {r['expected_flags']}")
        elif not (a < end < b and 0 < read == end - lo and dist == b - end):
            out.append(f"{r['sid']}: its cancel does not end inside its chunk [{a}, {b}) before the chunk's end (ends at {end}, reads {read} B from {lo})")
    return out


def scenario_of(p: dict, seed: int) -> Scenario:
    return make_scenario(Fault(p["fault"]), Layout(p["layout"]), Option(p["option"]), Condition.COLD, p["replicate"], seed)


def run_key(sealed: dict, p: dict, attempt: int) -> str:
    return f"{KEY_PREFIX}{sealed['sha256'][:8]}-{p['order']:04d}-{p['sid']}" + (f"-a{attempt}" if attempt > 1 else "")


# ---------------------------------------------------------------------------------------------------------------- inside the sandbox
_BEFORE = r'''
import json as _vj, urllib.parse as _vu
import requests as _vrq
_VREC, _VKIND = [], ["plan"]
_vsend = _vrq.Session.send
def _vrecord(self, request, **kw):
    r = _vsend(self, request, **kw)
    _VREC.append([request.method, _vu.urlsplit(request.url).path, request.headers.get("Range"), r.status_code, r, _VKIND[0]])
    return r
_vrq.Session.send = _vrecord
'''

_AFTER = r'''
import os as _vo
_VX = _vj.loads(VAL_JSON)
_vtok = {"X-Auth-Token": _vo.environ["ONEDATA_TOKEN"]}
_vs = _vrq.Session()
_vloc = _vo.environ["ICSA_DATASET_LOCATION"].strip("/")
_vbase = "https://" + _VX["provider"] + "/api/v3/oneprovider"
def _vrel(key):
    rest = _vloc.split("/", 1)[1]
    return rest if _VX["layout"] == "S2" else rest + "/" + key
def _vfid(key):
    _VKIND[0] = "lookup"
    r = _vs.post(_vbase + "/lookup-file-id/" + _vloc.split("/", 1)[0] + "/" + _vrel(key), headers=_vtok, timeout=120)
    r.raise_for_status()
    return r.json()["fileId"]
_vout = {}
if _VX.get("short"):
    key, size = _VX["short"]
    fid = _vfid(key)
    _VKIND[0] = "short"
    r = _vs.get(f"{_vbase}/data/{fid}/content", headers={**_vtok, "Range": f"bytes={size - 100}-{size + 4000}"}, timeout=120)
    _vout["short"] = [r.status_code, len(r.content)]
if _VX.get("cancel"):
    key, lo, hi = _VX["cancel"]
    fid = _vfid(key)
    _VKIND[0] = "cancel"
    h = dict(_vtok)
    if lo is not None:
        h["Range"] = f"bytes={lo}-{hi - 1}"
    r = _vs.get(f"{_vbase}/data/{fid}/content", headers=h, stream=True, timeout=600)
    got = r.raw.read(_VX.get("cancel_read") or _VX["cancel_bytes"])
    r.close()
    _vout["cancel"] = [r.status_code, len(got)]
if _VX.get("reject"):
    key, size = _VX["reject"]
    fid = _vfid(key)
    _VKIND[0] = "reject"
    if _VX["option"] == "D":
        r = _vs.get(f"{_vbase}/data/{fid}/content", headers={**_vtok, "Range": "bytes=0-9"}, timeout=120)
    else:
        r = _vs.put(f"{_vbase}/data/{fid}/content", headers=_vtok, data=b"", timeout=120)
    _vout["reject"] = [r.status_code, len(r.content)]
def _vgot(r):
    t = getattr(r.raw, "tell", None)
    return t() if t is not None else len(r.content)
_vout["requests"] = [[m, p, rg, st, _vgot(r), k] for m, p, rg, st, r, k in _VREC]
print("ICSA_VAL " + _vj.dumps(_vout), flush=True)
'''


def exec_code(s: Scenario, ops: list, expect: list, extras: dict, provider: str) -> str:
    from .calibrate import exec_code as cal_code
    val = {**extras, "option": s.option.value, "layout": s.layout.value, "provider": provider, "cancel_bytes": CANCEL_BYTES}
    return _BEFORE + cal_code(s, ops, expect=expect) + f"\nVAL_JSON = {json.dumps(val)!r}\n" + _AFTER


# ---------------------------------------------------------------------------------------------------------------- the checks
def check_requests(gate_text: str, client: list[list]) -> dict:
    """Each request of the run, the gate's line against the client's own count, matched in order within (method, path, Range)."""
    gate = defaultdict(list)
    for line in gate_text.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if "event" in d:
            continue
        gate[(d.get("method"), str(d.get("path", "")).split("?", 1)[0], d.get("range"))].append(d)
    cli = defaultdict(list)
    for m, p, rg, st, got, kind in client:
        cli[(m, p, rg)].append({"status": st, "received": got, "kind": kind})
    rows, problems = [], []
    for k in sorted(set(gate) | set(cli), key=str):
        g, c = gate.get(k, []), cli.get(k, [])
        if len(g) != len(c):
            problems.append(f"{k[0]} {k[1]} {k[2]}: {len(g)} gate line(s), {len(c)} client response(s)")
        for gl, cl in zip(g, c):
            b, u = gl.get("body_bytes"), gl.get("body_bytes_unconfirmed", 0)
            row = {"method": k[0], "path": k[1], "range": k[2], "kind": cl["kind"], "client_status": cl["status"], "gate_status": gl.get("status"),
                   "client_bytes": cl["received"], "gate_body_bytes": b, "gate_unconfirmed": u}
            if not isinstance(b, int):
                problems.append(f"{k[1]}: the gate's line has no body_bytes")
            elif cl["kind"] == "cancel":
                row["excess"] = b - cl["received"]
                if cl["received"] > b:      # amendment 22: at least the client's. body_bytes counts a failed write's partial progress; the unconfirmed rest never covers a shortfall
                    problems.append(f"{k[1]}: a cancelled transfer the client read {cl['received']} B of, beyond the gate's body_bytes {b} (+{u} unconfirmed)")
            elif b != cl["received"] or u:
                problems.append(f"{k[1]} ({cl['kind']}): the gate says {b} B (+{u} unconfirmed), the client received {cl['received']}")
            rows.append(row)
    kinds = {r["kind"] for r in rows}
    return {"requests": rows, "problems": problems, "kinds": sorted(kinds)}


def client_events(client: list[list]) -> list:
    """The client's own record of what it received, as the Traefik record's events: for telling the gate's error from the masking model's."""
    from .records.base import AccessEvent, Kind
    from .records.gate import _CONTENT
    out = []
    for m, p, rg, st, got, kind in client:
        c = _CONTENT.search(p or "")
        out.append(AccessEvent(ts=None, kind=Kind.READ if c and m == "GET" else Kind.OTHER, target=c.group(1) if c else None, status=st, range_header=rg,
                               content_size=got, client="client", record=Record.TRAEFIK))
    return out


def check_flags(gate_text: str, expected: list[int], required: Required, manifest: Manifest, client: list[list] | None = None) -> dict:
    spec = DetectorSpec(Record.TRAEFIK)
    o = detect(parse_gate(gate_text).events, required, manifest, spec)
    exp = frozenset(expected)
    out = {"flags": sorted(o.missing), "expected": sorted(exp), "equal": o.missing == exp, "missed": sorted(exp - o.missing),
           "extra": sorted(o.missing - exp), "unresolved": o.n_unresolved, "fingerprint": o.fingerprint}
    if client is not None:
        c = detect(client_events(client), required, manifest, spec)
        out["client_flags_equal_gate"] = c.missing == o.missing
        out["client_flags_equal_expected"] = c.missing == exp
    return out


def score_run(rec: dict, p: dict, required: Required, manifest: Manifest, run_dir: Path) -> dict:
    out = {"order": p["order"], "sid": p["sid"], "fault": p["fault"], "option": p["option"], "layout": p["layout"], "run_key": rec.get("run_key")}
    if not rec.get("ok"):
        return {**out, "passes": None, "why": f"the run did not finish: {(rec.get('errors') or ['?'])[0]}"[:300]}
    gl = run_dir / "gate_requests.jsonl"
    if not gl.exists():
        return {**out, "passes": False, "why": "no gate log"}
    text = gl.read_text()
    req = check_requests(text, rec.get("val", {}).get("requests", []))
    flags = check_flags(text, p["expected_flags"], required, manifest, rec.get("val", {}).get("requests", []))
    missing = [k for k in ("short", "cancel", "reject") if p["extras"].get(k) and k not in req["kinds"]]
    problems = req["problems"] + [f"no {m} request on record" for m in missing] + check_cancel(p["extras"], req["requests"])
    cancel = cancel_report(p["extras"], req["requests"], flags)
    if cancel and not flags["equal"]:                      # a finding, not something to repair: the cancel's distance rides beside the flag
        problems.append(f"flags missed {flags['missed']}, extra {flags['extra']}: the cancel ended {cancel['distance_planned']} B before its chunk's end "
                        f"(the client read to {cancel['distance_client']} B before it, the gate credited to {cancel['distance_gate']} B before it)")
    out = {**out, "passes": not problems and flags["equal"], "problems": problems[:20], "flags": flags,
           "cancel_excess": [r.get("excess") for r in req["requests"] if r["kind"] == "cancel"], "n_requests": len(req["requests"])}
    return {**out, "cancel": cancel} if cancel else out


def check_cancel(extras: dict, rows: list[dict]) -> list[str]:
    """What makes the run's cancel one: a content read (the detector's own `ok_statuses`, on the client's side and the gate's) that the client cut at the length planned. An
    error response is neither: its short body is not a transfer cut, and the detector credits it nothing, so a run of it would pass with no cancel exercised. An omitted-day
    cancel reads exactly its planned length, which ends inside its chunk; a read-day cancel, at most CANCEL_BYTES and at least a byte."""
    row = next((r for r in rows if r["kind"] == "cancel"), None)
    if row is None or not extras.get("cancel"):
        return []                                           # a missing cancel is named by the caller
    ok, got, out = DetectorSpec(Record.TRAEFIK).ok_statuses, row["client_bytes"], []
    for side, st in (("client", row["client_status"]), ("gate", row["gate_status"])):
        if st not in ok:
            out.append(f"the cancel GET got HTTP {st} on the {side}'s side, not a content read ({'/'.join(map(str, ok))}): its {got} B are no cancelled transfer")
    if "cancel_chunk" in extras:
        a, b = extras["cancel_chunk"]
        lo, want = extras["cancel_lo"], extras["cancel_read"]
        if not isinstance(got, int) or got != want or not a < lo + got < b:
            out.append(f"the cancel read {got} B from {lo}, planned {want} B, which ends inside its chunk [{a}, {b})")
    elif not isinstance(got, int) or not 0 < got <= CANCEL_BYTES:
        out.append(f"the cancel read {got} B, planned at most {CANCEL_BYTES} B and at least one")
    return out


def cancel_report(extras: dict, rows: list[dict], flags: dict) -> dict | None:
    """The one cancel of an `omitted` run: its planned distance to the chunk's end, what the gate and the client counted, and whether the flags stayed exact."""
    if "cancel_distance" not in extras:
        return None
    row = next((r for r in rows if r["kind"] == "cancel"), None)
    if row is None:
        return None
    lo, end, b, u, c = extras["cancel_lo"], extras["cancel_chunk"][1], row["gate_body_bytes"], row["gate_unconfirmed"], row["client_bytes"]
    return {"planned_end": extras["cancel_end"], "chunk_end": end, "distance_planned": extras["cancel_distance"],
            "client_bytes": c, "gate_confirmed": b, "gate_unconfirmed": u, "distance_client": end - (lo + c), "distance_gate": end - (lo + b),
            "gate_reached_chunk_end": lo + b >= end, "flags_exact": flags["equal"], "flags_moved": len(flags["missed"]) + len(flags["extra"])}


def verdict(rows: list[dict], sealed: dict) -> dict:
    by_cell: dict = defaultdict(lambda: {"runs": 0, "passed": 0, "failed": 0, "not_finished": 0})
    for r in rows:
        c = by_cell[f"{r['option']} {r['layout']} {r['fault']}"]
        c["runs"] += 1
        c["passed" if r["passes"] else "not_finished" if r["passes"] is None else "failed"] += 1
    cancels = [{"sid": r["sid"], **r["cancel"]} for r in rows if r.get("cancel")]
    complete = len(rows) == len(sealed["runs"]) and all(r["passes"] is not None for r in rows)
    return {"sha256": sealed["sha256"], "runs": len(rows), "planned": len(sealed["runs"]), "complete": complete,
            "passes": complete and all(r["passes"] for r in rows) and not sealed["short_of_runs"],
            "failed": [r["sid"] for r in rows if r["passes"] is False], "not_finished": [r["sid"] for r in rows if r["passes"] is None],
            "short_of_runs": sealed["short_of_runs"], "by_cell": dict(sorted(by_cell.items())),
            **({"cancels": cancels, "cancel_summary": {
                "cancels": len(cancels), "within_0.5MB_of_chunk_end": sum(1 for c in cancels if c["distance_planned"] <= NEAR_END),
                "gate_credit_reached_chunk_end": sum(1 for c in cancels if c["gate_reached_chunk_end"]),
                "flags_moved": sum(c["flags_moved"] for c in cancels), "runs_with_moved_flags": sum(1 for c in cancels if not c["flags_exact"])}}
               if cancels else {})}


# ---------------------------------------------------------------------------------------------------------------- the cut rule
def _gate_by_key(gate_text: str) -> dict:
    """The gate's request lines in log order, grouped as `check_requests` groups them: (method, path without its query, Range)."""
    gate = defaultdict(list)
    for line in gate_text.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if "event" in d:
            continue
        gate[(d.get("method"), str(d.get("path", "")).split("?", 1)[0], d.get("range"))].append(d)
    return gate


def cancel_gate_lines(gate_text: str, client: list[list]) -> list:
    """The gate's line for each cancel of the client's record, in the client's order (None where the gate has no such line). Matched as `check_requests` matches a response to
    its line: the n-th client response with a (method, path, Range) to the n-th gate line with it. A D whole-file cancel shares its key with the plan's read of the same file,
    so taking the first line with that path would give the plan's."""
    gate, seen, out = _gate_by_key(gate_text), defaultdict(int), []
    for m, p, rg, st, got, kind in client:
        k = (m, p, rg)
        n, seen[k] = seen[k], seen[k] + 1
        if kind == "cancel":
            lines = gate.get(k, [])
            out.append(lines[n] if n < len(lines) else None)
    return out


def unanswered_at_teardown(gate_text: str) -> int:
    """The connections the gate was stopped on with a request read and not yet answered: its `conn_close` lines with `ended` "teardown" and `in_request` true."""
    n = 0
    for line in gate_text.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("event") == "conn_close" and d.get("ended") == "teardown" and d.get("in_request") is True:
            n += 1
    return n


def cancel_unread(extras: dict, manifest: Manifest, status: int | None = None, received: int | None = None) -> int | None:
    """What the run's cancel leaves of its body unread: the body's length less what the client received. The body is the one the response carried: the file's size for a
    whole-file cancel (D's) and for a ranged one answered 200 (a server that ignored the Range sends the whole file), the range's length for one answered 206 or not yet
    known. What the client received is its own count when there is one (`received`), else the plan's `cancel_read`, or CANCEL_BYTES for a read-day cancel, as the
    sandbox's script reads. None for a run with no cancel."""
    c = extras.get("cancel")
    if not c:
        return None
    key, lo, hi = c
    body = manifest.file(key).size if lo is None or status == 200 else hi - lo
    got = received if isinstance(received, int) else (extras.get("cancel_read") or CANCEL_BYTES)
    return body - got


def _flagged_without(text: str, drop: set, drop_lines: list[dict], required: Required, manifest: Manifest) -> frozenset:
    """The days the frozen detector flags on the gate log with some responses left out: which days nothing else covers. A response is left out by its key
    (conn, conn_request) in `drop`, which only a line carrying `conn` has, or, for a line with none (an old gate's), by being one of `drop_lines` itself: lines
    with no `conn` share no identity, so a key of (None, None) never stands for one."""
    drop = {k for k in drop if k is not None and k[0] is not None}
    remaining = list(drop_lines)          # each line to leave out is left out once: an identical line elsewhere is a response of its own
    keep = []
    for ev in parse_gate(text).events:
        try:
            d = json.loads(ev.raw)
        except ValueError:
            d = {}
        if d.get("conn") is not None and (d.get("conn"), d.get("conn_request")) in drop:
            continue
        if d.get("conn") is None and d in remaining:
            remaining.remove(d)
            continue
        keep.append(ev)
    return detect(keep, required, manifest, DetectorSpec(Record.TRAEFIK)).missing


def _unmarked_why(line: dict | None, endings: dict) -> str:
    if line is None:
        return "the gate has no line for it"
    if line.get("conn") is None:
        return "its line has no conn (a gate that does not log how connections end)"
    e = endings.get((line["conn"], line.get("conn_request")))
    if e is None:
        return "another request followed it on its connection"
    return f"its connection ended {e['ended']!r}, which is not read as a cut"


def score_run_cut(rec: dict, p: dict, required: Required, manifest: Manifest, run_dir: Path) -> dict:
    """One run under the cut rule. `problems` fail it. `band_excused` are the problems of the cancel's own marking and day that a run in the band is not held to: a cancel that
    leaves at most BAND_BYTES unread; every other problem of such a run is in `problems` as for any other."""
    out = {"order": p["order"], "sid": p["sid"], "fault": p["fault"], "option": p["option"], "layout": p["layout"], "run_key": rec.get("run_key")}
    if not rec.get("ok"):
        return {**out, "passes": None, "why": f"the run did not finish: {(rec.get('errors') or ['?'])[0]}"[:300]}
    gl = run_dir / "gate_requests.jsonl"
    if not gl.exists():
        return {**out, "passes": False, "why": "no gate log"}
    text, client, extras = gl.read_text(), rec.get("val", {}).get("requests", []), p["extras"]
    try:
        u = undecided_days(text, required, manifest)
        close = gate_close_summary(text)
        endings = {(e["conn"], e["conn_request"]): e for e in gate_endings(text)}
    except ValueError as e:                                  # a gate this reader does not know is never read as complete
        return {**out, "passes": False, "why": f"the gate log cannot be read: {e}"[:300]}
    req = check_requests(text, client)
    problems = req["problems"] + [f"no {m} request on record" for m in ("short", "cancel", "reject") if extras.get(m) and m not in req["kinds"]] + check_cancel(extras, req["requests"])
    excused: list[str] = []
    crow = next((r for r in req["requests"] if r["kind"] == "cancel"), None)
    unread = cancel_unread(extras, manifest, (crow or {}).get("client_status"), (crow or {}).get("client_bytes"))
    band = unread is not None and unread <= BAND_BYTES
    cuts = {(c["conn"], c["conn_request"]): c for c in u["cuts"]}
    lines = cancel_gate_lines(text, client)
    keys = [None if d is None else (d.get("conn"), d.get("conn_request")) for d in lines]
    cancel_day = p["expected_flags"][0] if p["fault"] != "none" and extras.get("cancel") and p["expected_flags"] else None      # where `_extras` puts a faulted run's cancel
    # in the band the cancel's own marking and day are excused only when the cancel is what decides that day: with every cut and the cancel left out, nothing else covers it
    alone = cancel_day is not None and cancel_day in _flagged_without(text, set(cuts) | {k for k in keys if k is not None},
                                                                      [d for d in lines if d is not None and d.get("conn") is None], required, manifest)
    marker_problems = excused if band else problems
    day_problems = excused if band and alone else problems
    for d, k in zip(lines, keys):
        if k not in cuts:
            marker_problems.append("cancel not marked cut: " + _unmarked_why(d, endings))
    for k, c in cuts.items():
        if k not in keys:
            problems.append(f"a complete response marked cut: {c['method']} {c['path']} {c['range']} ({c['reason']})")
    exp, undecided, decided = frozenset(p["expected_flags"]), frozenset(u["undecided"]), frozenset(u["decided_missing"])
    want = exp - undecided
    missed, extra = sorted(want - decided), sorted(decided - want)
    if cancel_day is not None and cancel_day not in undecided:
        day_problems.append(f"the cancel's day {cancel_day} {'missed' if cancel_day in decided else 'read'}, not undecided")
    own = {cancel_day} if band and alone else set()       # in the band, a flag on the cancel's own day is the marker's outcome only when the cancel alone covers that day
    if [d for d in missed + extra if d in own]:
        excused.append(f"flags missed {[d for d in missed if d in own]}, extra {[d for d in extra if d in own]} on the cancel's own day")
    m2, e2 = [d for d in missed if d not in own], [d for d in extra if d not in own]
    if m2 or e2:
        problems.append(f"flags missed {m2}, extra {e2} on decided days (undecided: {sorted(undecided)})")
    k0 = keys[0] if keys else None
    cut0, end0 = cuts.get(k0), endings.get(k0)
    marker = {"cancel_marked": (k0 in cuts) if keys else None, "reason": cut0["reason"] if cut0 else None, "ended": (end0 or {}).get("ended"), "unread": unread, "band": band}
    cancel = cancel_report(extras, req["requests"], {"equal": not missed and not extra, "missed": missed, "extra": extra})
    return {**out, "passes": not problems, "problems": problems[:20], "band": band, "band_excused": excused[:20], "unobservable": bool(exp) and exp <= undecided, "marker": marker,
            "expected": sorted(exp), "missing_complete": u["missing_complete"], "undecided": sorted(undecided), "decided_missing": sorted(decided), "missed": missed, "extra": extra,
            "cancel_day": cancel_day, "cuts": u["cuts"], "n_days": len(required.days), "touched_days": sorted({d for c in u["cuts"] for d in c["days"]}), "close": close,
            "unanswered_at_teardown": unanswered_at_teardown(text), "cancel_excess": [r.get("excess") for r in req["requests"] if r["kind"] == "cancel"],
            "n_requests": len(req["requests"]), **({"cancel": cancel} if cancel else {})}


CUT_SHARE_DEFINITION = ("per option x layout over the runs that finished: runs_with_cut / runs (share_runs); days_undecided / days, days being the required days summed over the "
                        "runs (share_days); expected_undecided / expected_flags, the injected flags a cut leaves undecided (share_expected)")


def verdict_cut(rows: list[dict], sealed: dict) -> dict:
    """The cut rule's verdict. It passes if the set is complete, no run is short of its fault types, and every run passes under `score_run_cut`: a run in the band passes
    without its cancel's marker outcome, which is reported apart; an unobservable run (every expected flag undecided) is counted, and is no failure."""
    cells: dict = defaultdict(lambda: {"runs": 0, "passed": 0, "failed": 0, "band": 0, "unobservable": 0, "not_finished": 0})
    share: dict = defaultdict(lambda: {"runs": 0, "runs_with_cut": 0, "days": 0, "days_touched": 0, "days_undecided": 0, "expected_flags": 0, "expected_undecided": 0})
    ended = dict.fromkeys(CLOSE_KINDS, 0)
    closes = {"old_format_runs": 0, "connections": 0, "no_close_line": 0, "cuts": dict.fromkeys(CUT_REASONS, 0)}
    teardown = {}
    for r in rows:
        c = cells[f"{r['option']} {r['layout']} {r['fault']}"]
        c["runs"] += 1
        c["passed" if r["passes"] else "not_finished" if r["passes"] is None else "failed"] += 1
        c["band"] += bool(r.get("band"))
        c["unobservable"] += bool(r.get("unobservable"))
        if "close" not in r:
            continue
        s = share[f"{r['option']} {r['layout']}"]
        s["runs"] += 1
        s["runs_with_cut"] += bool(r["cuts"])
        s["days"] += r["n_days"]
        s["days_touched"] += len(r["touched_days"])
        s["days_undecided"] += len(r["undecided"])
        s["expected_flags"] += len(r["expected"])
        s["expected_undecided"] += len(set(r["expected"]) & set(r["undecided"]))
        for k, n in r["close"]["ended"].items():
            ended[k] = ended.get(k, 0) + n
        closes["old_format_runs"] += bool(r["close"]["old_format"])
        closes["connections"] += r["close"]["connections"]
        closes["no_close_line"] += r["close"]["no_close_line"]
        for k, n in r["close"]["cuts"].items():
            closes["cuts"][k] = closes["cuts"].get(k, 0) + n
        if r["unanswered_at_teardown"]:
            teardown[r["sid"]] = r["unanswered_at_teardown"]
    for s in share.values():
        s["share_runs"] = s["runs_with_cut"] / s["runs"] if s["runs"] else None
        s["share_days"] = s["days_undecided"] / s["days"] if s["days"] else None
        s["share_expected"] = s["expected_undecided"] / s["expected_flags"] if s["expected_flags"] else None
    done = [r for r in rows if r["passes"] is not None and "close" in r]
    marks = [r["marker"]["cancel_marked"] for r in done]
    complete = len(rows) == len(sealed["runs"]) and all(r["passes"] is not None for r in rows)
    band = [{"sid": r["sid"], "option": r["option"], "layout": r["layout"], "fault": r["fault"], "marker": r["marker"], "passes": r["passes"], "excused": r["band_excused"],
             "problems": r["problems"]} for r in rows if r.get("band")]
    return {"rule": "cut", "sha256": sealed["sha256"], "runs": len(rows), "planned": len(sealed["runs"]), "complete": complete,
            "passes": complete and all(r["passes"] for r in rows) and not sealed["short_of_runs"],
            "failed": [r["sid"] for r in rows if r["passes"] is False], "not_finished": [r["sid"] for r in rows if r["passes"] is None], "band": band,
            "unobservable": [r["sid"] for r in rows if r.get("unobservable")], "short_of_runs": sealed["short_of_runs"], "by_cell": dict(sorted(cells.items())),
            "counts": {"runs": len(rows), "passed": sum(1 for r in rows if r["passes"]), "failed": sum(1 for r in rows if r["passes"] is False), "band": len(band),
                       "unobservable": sum(1 for r in rows if r.get("unobservable")), "not_finished": sum(1 for r in rows if r["passes"] is None),
                       "cancels_marked": sum(1 for m in marks if m), "cancels_unmarked": sum(1 for m in marks if m is False), "runs_with_cuts": sum(1 for r in done if r["cuts"])},
            "cut_share": dict(sorted(share.items())), "cut_share_definition": CUT_SHARE_DEFINITION, "close": {"ended": ended, **closes},
            "unanswered_at_teardown": {"total": sum(teardown.values()), "runs_with": len(teardown), "by_run": teardown}}


# ---------------------------------------------------------------------------------------------------------------- driving it
def _load(out: Path, manifests: dict) -> dict:
    sealed = json.loads((out / "validation_plan.json").read_text())
    body = {k: v for k, v in sealed.items() if k != "sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != sealed["sha256"]:
        raise SystemExit("validation_plan.json does not match its own sha256: the set was changed after it was sealed")
    if bad := plan_problems(sealed, manifests):          # a set that cannot show the over-count amendment 22 asks for is not run and not scored
        raise SystemExit(f"validation_plan.json is refused (amendment 22: each faulted run's cancel falls on an omitted day and ends before its chunk does), "
                         f"{len(bad)} problem(s): {'; '.join(bad[:5])}")
    return sealed


def _attempts(out: Path, sealed: dict, p: dict) -> list[dict]:
    recs = []
    for a in range(1, MAX_ATTEMPTS + 1):
        f = out / "runs" / run_key(sealed, p, a) / "run.json"
        if f.exists():
            recs.append(json.loads(f.read_text()))
    return recs


def run(out: Path, image: str, required: Required, manifests: dict, *, concurrency: int = 4, log=print) -> None:
    from icsa.harness.real_sandbox import sandbox_config
    from icsa.harness.config import load_config
    from icsa.sandbox.config import pin_image
    from icsa.scripted import federation as F
    from . import calibrate as C
    from .live_check import hold_quarantines
    sealed = _load(out, manifests)
    cfg = sandbox_config(image, pin_image(image), sandbox_limits=load_config().sandbox_limits)      # untraced, the campaign's limits
    todo = []
    for p in sealed["runs"]:
        recs = _attempts(out, sealed, p)
        if any(r.get("ok") for r in recs) or len(recs) >= MAX_ATTEMPTS:
            continue
        todo.append((p, len(recs) + 1))
    stop = threading.Event()

    def one(item):
        p, attempt = item
        if stop.is_set():
            return None
        s, man = scenario_of(p, sealed["seed"]), manifests[Layout(p["layout"])]
        ops = C.read_ops(s, required, man)
        code = exec_code(s, ops, C.expected_bytes(ops, man), p["extras"], F.MAIN.provider_host)
        try:
            r = C.execute_run(SimpleNamespace(scenario=s, order=p["order"]), SimpleNamespace(sha=sealed["sha256"]), required, man, cfg, out / "runs",
                              key=run_key(sealed, p, attempt), via=None, code=code)
        except C.RunRefused as e:
            stop.set()
            log(f"stopped: {e}")
            return None
        log(f"{r['run_key']}: {'ok' if r.get('ok') else 'FAILED ' + str((r.get('errors') or ['?'])[0])[:200]}")
        return r
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        list(ex.map(one, todo))
    hold_quarantines()


def score(out: Path, required: Required, manifests: dict, rule: str = "registered") -> dict:
    """`registered`: the rule the sealed set was scored with, writes verdict.json. `cut`: the cut rule, writes verdict-cut.json and never verdict.json."""
    if rule not in RULES:
        raise ValueError(f"rule is one of {RULES}, not {rule!r}")
    sealed = _load(out, manifests)
    rows = []
    for p in sealed["runs"]:
        recs = _attempts(out, sealed, p)
        rec = next((r for r in reversed(recs) if r.get("ok")), recs[-1] if recs else {})
        rows.append((score_run_cut if rule == "cut" else score_run)(rec, p, required, manifests[Layout(p["layout"])], out / "runs" / rec.get("run_key", "none")))
    if rule == "cut":
        v = verdict_cut(rows, sealed)
        (out / "verdict-cut.json").write_text(json.dumps({"verdict": v, "runs": rows}, indent=1))
        return v
    v = verdict(rows, sealed)
    (out / "verdict.json").write_text(json.dumps({"verdict": v, "runs": rows}, indent=1))
    return v


def main(argv=None) -> int:
    from .calibrate import IDS, REPO, _calibration_instance, _manifests
    ap = argparse.ArgumentParser(prog="python -m icsa.faults.gate_validation")
    ap.add_argument("command", choices=["plan", "run", "score"])
    ap.add_argument("out", type=Path)
    ap.add_argument("--image")
    ap.add_argument("--concurrency", type=int, default=None, help="run: sandboxes at once; default: what the launch JSON reserves for this process (never more)")
    ap.add_argument("--launch-config", type=Path, help="run: the campaign's launch JSON; its process_reservations['validation_set'] says the slot keys this process leases from "
                    "and the sandboxes it holds, and its reservation_dir (or ICSA_RESERVATION_DIR) where it takes its lock for as long as it runs")
    ap.add_argument("--rule", choices=list(RULES), default=None, help="score: `registered` (the default) writes verdict.json; `cut` scores a gate that logs how connections end, "
                    "and writes verdict-cut.json")
    ap.add_argument("--cancel-on", choices=list(CANCEL_ON), default="omitted", help="where a faulted run's cancel goes; `run` and `score` refuse a plan that is not `omitted`")
    a = ap.parse_args(argv)
    if a.rule is not None and a.command != "score":
        ap.error("--rule is for score")
    _, required = _calibration_instance()
    manifests, _ = _manifests(IDS)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.command == "plan":
        f = a.out / "validation_plan.json"
        sealed = plan(required, manifests, cancel_on=a.cancel_on)
        if f.exists() and json.loads(f.read_text())["sha256"] != sealed["sha256"]:
            raise SystemExit("a different validation set is already sealed here")
        f.write_text(json.dumps(sealed, indent=1))
        print(json.dumps({"runs": len(sealed["runs"]), "sha256": sealed["sha256"], "short_of_runs": sealed["short_of_runs"]}))
        return 0
    if a.command == "run":
        if not a.image:
            raise SystemExit("run needs --image")
        from icsa.harness import reservation as R
        from .matcher import load_slot_map
        try:         # its own slot keys and its reservation, or no run: without them it would lease from the pool the agent runs share (the campaign counts it by this lock)
            spec = ((json.loads(a.launch_config.read_text()) if a.launch_config else {}).get("process_reservations") or {}).get("validation_set") or {}
            n = a.concurrency if a.concurrency is not None else int(spec.get("sandboxes") or 1)
            R.claim("validation_set", a.launch_config, {k: s.option for k, s in load_slot_map(REPO / "config" / "slot_map.json").items()},
                    options={p["option"] for p in _load(a.out, manifests)["runs"]}, concurrency=n)
        except (R.ReservationError, OSError, ValueError) as e:
            raise SystemExit(f"run refused: {e}") from None
        from icsa.sandbox.termination import exit_on_sigterm
        exit_on_sigterm()
        run(a.out, a.image, required, manifests, concurrency=n)
        return 0
    if a.rule == "cut":
        v = score(a.out, required, manifests, rule="cut")
        shown = {k: v[k] for k in ("passes", "complete", "runs", "planned", "failed", "not_finished", "short_of_runs")}
        print(json.dumps({**shown, "band": [b["sid"] for b in v["band"]], "unobservable": len(v["unobservable"])}))
        return 0 if v["passes"] else 1
    v = score(a.out, required, manifests)
    print(json.dumps({k: v[k] for k in ("passes", "complete", "runs", "planned", "failed", "not_finished", "short_of_runs")}))
    return 0 if v["passes"] else 1


if __name__ == "__main__":
    sys.exit(main())
