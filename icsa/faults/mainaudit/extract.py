"""From the pulled lines to one record per finished M attempt: `<store>/runs/<run_key>/<attempt>/m_audit.json` and the run's own lines, `lines.log.gz`.

The store sits outside the campaign's mirror: a file added to a mirrored run dir would break `snapshot.fetch`'s per-dir byte check. The attempts come from
the mirror's run records (`run_record.json`, `extras.onedata_slot`); every attempt of an M slot user found there takes part in the attribution, so a
neighbour's lease is known even when its own record is final. A record is final once the pull has reached past its lease (`record.FLUSH_MARGIN_S`); until
then it says `capture_incomplete` and is rebuilt on the next pass. An attempt whose record names no lease still gets a record (`no_lease`), so its absence
from the measure is on file, not silent.

The capture is large (19.85 M lines, 4.9 GB on 4 Nov, 0.7 GB more each hour), so it is never held: `extract` streams it once, parses and attributes the lines
of the users with a record to write in blocks of `BLOCK_LINES`, and spills each pending lease's own lines to a file under the store, from which that lease's
record is built, one lease at a time. What stays in memory is a block, the leases, and the damaged lines; the output is what holding it all gave."""
from __future__ import annotations

import dataclasses
import gzip
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Iterable

from icsa.faults.records.audit import _LINE, parse_audit, salvage
from icsa.faults.units import FileEntry, Manifest, Required
from icsa.records import Layout

from . import attribute as A
from . import record as R
from . import switched as SW
from . import windows as W

FINAL_CLASSES = ("observed", "read_nothing")
NOT_FINAL_REASONS = ("capture_incomplete", "window_end_unknown", "window_end_unverified", "restart_unverified")   # evidence that can still come (Astra, #2)
NEAR_S = 2.0                     # a lease seen for the first time reopens the records of its user's leases within this of it (Astra, #2)


def attempts(mirror: Path, options: Iterable[str] = ("M",)) -> list[tuple[Path, dict]]:
    """Each finished attempt of these options in the mirror: (its dir, its run record), in path order. Science, #34 07:01Z (5): T and D get the same reader."""
    out = []
    for o in options:
        for p in sorted(mirror.glob(f"**/runs/*__{o}__*/attempt*/run_record.json")):
            if not p.parent.with_name(p.parent.name + ".pulled.json").is_file():      # snapshot.fetch's marker: the dir is whole (Astra, #4)
                continue
            out.append((p.parent, json.loads(p.read_text())))
    return sorted(out, key=lambda x: str(x[0]))


def m_attempts(mirror: Path) -> list[tuple[Path, dict]]:
    return attempts(mirror, ("M",))


def manifest_to_json(m: Manifest) -> dict:
    return {"layout": m.layout.value, "files": [vars(f) | {} for f in m.files], "units": {str(d): list(u) for d, u in m.units.items()}}


def manifest_from_json(d: dict) -> Manifest:
    return Manifest(Layout(d["layout"]), tuple(FileEntry(**f) for f in d["files"]), {int(k): tuple(v) for k, v in d["units"].items()})


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _same_key(p: Path, key: str) -> bool:
    try:
        return json.loads(p.read_text()).get("cache_key") == key
    except (OSError, ValueError):
        return False


def _final(p: Path) -> bool:
    try:
        v = json.loads(p.read_text())["verdict"]
    except (OSError, ValueError, KeyError):
        return False
    return v["class"] in FINAL_CLASSES or v["reason"] not in NOT_FINAL_REASONS


QUAR_MARGIN_S = 60.0             # a quarantine is logged right after a lease's end: a copy taken less than this after the end may not hold it yet


def _quar(v) -> tuple[list[dict], float]:
    """A host's quarantine evidence: a list of entries (a test's shorthand: complete for all time) or {"entries": [...], "as_of": epoch} (a copy, or a file
    known absent, as of that time)."""
    if isinstance(v, dict):
        return list(v.get("entries") or []), float(v["as_of"])
    return list(v), float("inf")


BLOCK_LINES = 20_000             # kept lines parsed and attributed at a time: what a pass holds of the capture, besides the ledger's one chunk


def _marker(users: Iterable[str]) -> re.Pattern | None:
    """Where a line names one of `users`: `user: <id>;` anywhere in it. One scan, the same truth as `any(f"user: {u};" in ln for u in users)` and independent of
    how many users there are. None for no users: nothing is kept."""
    ids = sorted(set(users), key=len, reverse=True)
    return re.compile("user: (?:" + "|".join(re.escape(u) for u in ids) + ");") if ids else None


class _Spool:
    """Each pending lease's own lines (the raw lines attribution gave it, in the capture's order), one file per lease under a temporary directory beside the
    store, so that a lease's record is built from its file alone. Bytes, never text mode: a line may hold a character `splitlines` breaks at. Removed by `close`."""

    def __init__(self, parent: Path, idents: Iterable[tuple[str, str]]):
        self.parent, self.dir = parent, None
        self.index = {i: n for n, i in enumerate(idents)}
        self.wrote: dict[tuple[str, str], int] = {}

    def _path(self, ident) -> Path:
        return self.dir / f"{self.index[ident]:07d}.log"

    def add(self, ident, raws: list[str]) -> None:
        if self.dir is None:
            self.parent.mkdir(parents=True, exist_ok=True)
            self.dir = Path(tempfile.mkdtemp(prefix=".extract-spill-", dir=self.parent))
        with open(self._path(ident), "ab") as f:
            f.write("".join(r + "\n" for r in raws).encode())
        self.wrote[ident] = self.wrote.get(ident, 0) + len(raws)

    def events(self, ident) -> list:
        n = self.wrote.get(ident, 0)
        if not n:
            return []
        evs = parse_audit(self._path(ident).read_bytes().decode(), max_bad=10 ** 9).events
        if len(evs) != n:                          # a line written and not read back would be a run's missing read (silent-fallback A)
            raise RuntimeError(f"{ident}: {n} lines spilled, {len(evs)} read back")
        return evs

    def close(self) -> None:
        if self.dir is not None:
            shutil.rmtree(self.dir, ignore_errors=True)


def extract(store: Path, attempts: list[tuple[Path, dict]], lines, *, covered_until: float | None, gaps: list[tuple[float, float | None]],
            restarts: list[dict], quarantines: dict | None, manifests: dict[Layout, Manifest], required_of: Callable[[str], Required],
            host_of: Callable[[Path, dict], str | None] = lambda d, rec: None, provenance: dict | None = None, orphans: list[dict] | None = None,
            mon_span: tuple[float, float] | None = None, covered_from: float | None = None, switched_key: str = "",
            block_lines: int = BLOCK_LINES, spool_dir: Path | None = None) -> dict:
    """Write the record of every attempt not yet final. Returns counts by class and reason.

    `lines`: the ledger's lines, or a callable giving them afresh (they may be read twice). `quarantines`: host -> its quarantine evidence (`_quar`); a host
    missing from it, or a lease ending within QUAR_MARGIN_S of its copy's as-of time, has its end unverified, never read as unquarantined. `mon_span`: the
    monitor's coverage. `covered_from`: where the pull began (the backfill's `since`, store/capture.json), never the first request it happened to hold.
    `switched_key`: the switched-on record's version (its schema and the manifests' ids); a record of another version is rebuilt.

    Reopened, whatever their state: the records of a lease seen for the first time or whose bounds or end changed, and of its user's leases within NEAR_S
    of it (old or new bounds); and every lease of a user with a damaged line anywhere in the ledger (Codex Astra, delta #1-#3).

    The lines are streamed, never held (see the module doc): a pass over `lines` keeps, in blocks of `block_lines`, those of the users with a record to write;
    a second pass, only if a damaged line reopened another user's records, keeps that user's. Every refusal of the ledger (a chunk that does not match its
    row) comes in those passes, before anything is written. `spool_dir`: where the spill goes (default: the store)."""
    get_lines = lines if callable(lines) else (lambda: lines)
    leases: list[W.Lease] = []
    no_lease: list[tuple[Path, dict, str]] = []
    for d, rec in attempts:
        host = host_of(d, rec)
        qv = (quarantines or {}).get(host)
        entries, as_of = _quar(qv) if qv is not None else ([], float("-inf"))
        try:
            ls = W.lease_from_record(rec, d.name, host=host, quarantines=entries)
        except W.NoLease as e:
            no_lease.append((d, rec, str(e)))
            continue
        if ls.end_source == "lease" and (qv is None or ls.end + QUAR_MARGIN_S > as_of):
            ls = dataclasses.replace(ls, end_source="unverified")
        leases.append(ls)
    reg_p = store / "leases.json"
    reg = json.loads(reg_p.read_text()) if reg_p.is_file() else {}
    lkey = lambda x: f"{x.run_key}/{x.attempt_dir}"
    sig = lambda x: [x.start, x.end, x.end_source]
    moved = []                                    # a lease new, or with other bounds or end than last time: its old and new spans both reopen neighbours
    for x in leases:
        old = reg.get(lkey(x))
        if old != sig(x):
            moved.append((x.user, x.start, x.end))
            if old:
                moved.append((x.user, old[0], old[1]))
    near = {lkey(x) for (u, a, b) in moved for x in leases if x.user == u and x.start - NEAR_S <= b and a - NEAR_S <= x.end}
    pending = {lkey(x) for x in leases if lkey(x) in near or not _final(store / "runs" / x.run_key / x.attempt_dir / "m_audit.json")}
    users = {x.user for x in leases if lkey(x) in pending}
    damaged: list[tuple[float | None, str | None]] = []
    bad_extra: list[tuple[float | None, str | None]] = []       # the damaged lines parsing finds in the kept ones, and the untimed events
    ambiguous: dict[tuple[str, str], int] = {}
    n_unattributed = 0
    held: list = []                                              # events of a client no user of the first pass owns: a line that names two users
    spool = _Spool(spool_dir or store, [x.ident for x in leases])
    want = {x.ident for x in leases if lkey(x) in pending}       # the leases that get a record: only their lines are spilled
    attr_leases = [x for x in leases if x.user in users]

    def absorb(events) -> None:                                  # attribution is per event, so block by block gives what one call over all of them gave
        nonlocal n_unattributed
        at = A.attribute(events, attr_leases)
        n_unattributed += sum(at.unattributed.values())
        for k, v in at.ambiguous.items():
            ambiguous[k] = ambiguous.get(k, 0) + v
        for ident, evs in at.per_run.items():
            if ident in want:
                spool.add(ident, [e.raw for e in evs])

    def read_block(block: list[str], hold: bool) -> None:
        parsed = parse_audit("\n".join(block), max_bad=10 ** 9)
        bad_extra.extend(salvage(b) for b in parsed.bad_lines)
        bad_extra.extend((None, ev.client) for ev in parsed.events if ev.ts is None)         # untimed: any lease of its user
        mine = [ev for ev in parsed.events if (ev.client or "") in users] if hold else parsed.events
        if hold:
            held.extend(ev for ev in parsed.events if (ev.client or "") not in users)
        absorb(mine)

    def keep_pass(mark: re.Pattern | None, hold: bool, find_damaged: bool) -> None:
        block: list[str] = []
        for ln in get_lines():
            if mark is not None and mark.search(ln):
                block.append(ln)
                if len(block) >= block_lines:
                    read_block(block, hold)
                    block = []
            elif find_damaged and ln.strip() and (not _LINE.match(ln) or salvage(ln)[0] is None):
                damaged.append(salvage(ln))                      # a damaged line of anyone (delta #3)
        if block:
            read_block(block, hold)

    try:
        keep_pass(_marker(users), hold=True, find_damaged=True)  # one pass: the lines of users with a record to write, and any damaged line of anyone
        spoiled = {u for _, u in damaged if u} - users
        if spoiled:                                              # a damaged line of a user whose records were final: reopen them, and read that user's lines too
            pending |= {lkey(x) for x in leases if x.user in spoiled}
            users |= spoiled
            want = {x.ident for x in leases if lkey(x) in pending}
            attr_leases = [x for x in leases if x.user in users]
        absorb(held)                                             # now every client is known; these came first in the capture, before the second pass's
        held = []
        if spoiled:
            keep_pass(_marker(spoiled), hold=False, find_damaged=False)
        bad = damaged + bad_extra
        cap = R.Capture(covered_until=covered_until, gaps=tuple(gaps), provenance=provenance, covered_from=covered_from, mon_span=mon_span)
        pending = [x for x in leases if lkey(x) in pending]
        counts: dict[str, int] = {}
        for x in pending:                                        # one lease at a time: its own lines from its file, never another's
            flags = ["orphan_risk"] if W.orphan_risk(x, orphans or []) else []
            evs = spool.events(x.ident)
            at = A.Attribution({x.ident: evs} if evs else {}, ambiguous, {}, A.EPS_S)       # `unattributed` is not read by build: counted in n_unattributed
            r = R.build(x, at, capture=cap, restarts=W.overlapping(restarts, x), bad_lines=bad, required=required_of(x.instance), manifest=manifests[x.layout],
                        flags=flags)
            base = store / "runs" / x.run_key / x.attempt_dir
            own = sorted(evs, key=lambda e: e.ts or 0.0)
            _write(base / "lines.log.gz", gzip.compress("".join(e.raw + "\n" for e in own).encode()))
            _write(base / "m_audit.json", json.dumps(r, indent=1, sort_keys=True).encode())
            k = f"{r['verdict']['class']}:{r['verdict']['reason']}"
            counts[k] = counts.get(k, 0) + 1
    finally:
        spool.close()
    for d, rec, why in no_lease:
        key = W.run_key_of(rec)
        base = store / "runs" / key / d.name
        if not (base / "m_audit.json").exists():
            _write(base / "m_audit.json", json.dumps({"schema": R.SCHEMA, "record_type": "audit", "run_key": key, "attempt_dir": d.name,
                                                      "verdict": {"class": "not_observed", "reason": "no_lease", "testable": False, "flags": [], "detail": why}},
                                                     indent=1, sort_keys=True).encode())
            counts["not_observed:no_lease"] = counts.get("not_observed:no_lease", 0) + 1
    for d, rec in attempts:              # the switched-on record (science, 07:01Z (6)): from the run dir alone, so written once
        key, opt = W.run_key_of(rec), rec["run"]["option"]
        p = store / "runs" / key / d.name / "switched_on.json"
        if opt in ("M", *SW.GATED) and not _same_key(p, switched_key):          # another version (schema, manifests' ids) is rebuilt (delta #7)
            r = SW.build(d, rec, required=required_of(rec["run"].get("instance_id")), manifest=manifests[Layout(rec["run"]["layout"])]) | {"cache_key": switched_key}
            _write(p, json.dumps(r, indent=1, sort_keys=True).encode())
            k = f"switched_on:{r['record_type']}:{r['verdict']['class']}:{r['verdict']['reason']}"
            counts[k] = counts.get(k, 0) + 1
    counts["unattributed_lines"] = n_unattributed
    _write(reg_p, json.dumps({**reg, **{lkey(x): sig(x) for x in leases}}, sort_keys=True).encode())
    counts["summary"] = _summary_and_join(store, attempts, host_of)
    return counts


def _attempt_order(name: str) -> tuple[int, int]:
    """attempt<N>.try<M> as numbers: a run's last attempt is its analysed one (the mirror holds the finished attempts of done runs)."""
    import re
    m = re.fullmatch(r"attempt(\d+)\.try(\d+)", name)
    if m is None:
        raise ValueError(f"{name!r} is not an attempt dir (attempt<N>.try<M>)")
    return int(m.group(1)), int(m.group(2))


def _load(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _summary_and_join(store: Path, attempts: list[tuple[Path, dict]], host_of) -> dict:
    """From every attempt's records, fresh or kept: summary.json, the counts by class and reason per option x layout x model and per run host, orphan_risk
    beside them (science, #34 09:14Z); and platform_rows.jsonl, one row per run in `adapter.load_fidelity_rows`'s format ({run: instance__option__layout__
    model__s<seed>, block, platform_record: {schema, audit, switched_on}}), which the analysis joins by run key beside the scored rows (option (c): no file
    the pipeline or the analysis imports changes). A run with several attempts here gives the row of its last."""
    by_cell: dict[str, dict] = {}
    by_host: dict[str, dict] = {}
    rows: dict[tuple, dict] = {}
    for d, rec in attempts:
        r = rec["run"]
        base = store / "runs" / W.run_key_of(rec) / d.name
        recs = {"audit": _load(base / "m_audit.json"), "switched_on": _load(base / "switched_on.json")}
        for tgt in (by_cell.setdefault(f"{r['option']}|{r['layout']}|{r['model']}", {"audit": {}, "switched_on": {}}),
                    by_host.setdefault(str(host_of(d, rec)), {"audit": {}, "switched_on": {}})):
            for name, x in recs.items():
                if x is None:
                    continue
                v = x["verdict"]
                k = f"{v['class']}:{v['reason']}" if v.get("reason") else v["class"]
                tgt[name][k] = tgt[name].get(k, 0) + 1
                if "orphan_risk" in (v.get("flags") or []):
                    tgt[name]["orphan_risk"] = tgt[name].get("orphan_risk", 0) + 1
        run = f"{r['instance_id']}__{r['option']}__{r['layout']}__{r['model']}__s{r['seed']}"
        order = _attempt_order(d.name)
        if (rec["block"], run) not in rows or order > rows[(rec["block"], run)][0]:      # the numerically latest attempt, never path order (Astra)
            rows[(rec["block"], run)] = (order, {"run": run, "block": rec["block"], "platform_record": {"schema": "platform/1", **recs}})
    summary = {"by_cell": by_cell, "by_host": by_host}
    _write(store / "summary.json", json.dumps(summary, indent=1, sort_keys=True).encode())
    _write(store / "platform_rows.jsonl", "".join(json.dumps(v[1], sort_keys=True) + "\n" for _, v in sorted(rows.items())).encode())
    return summary
