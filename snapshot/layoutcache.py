"""A per-run cache of layout_read's evidence, so that an interim reads only the runs it has not seen (#34; lane-snap5's request of 5 Nov).

    python -m snapshot.layoutread read <seal> --cache DIR ...        # read-through: a run found in the cache is not read again; a run not found is read and stored
    python -m snapshot.layoutcache fill --merged-root M --cache DIR --audit-root R --bmerge-config F [--jobs N]
                                                                     # fills DIR for every finished attempt of a merged store, outside any snapshot

What is cached, per finished attempt directory, is the run's EVIDENCE: what each source shows of it (`layoutread.Ev` of the gate, the perf log and the audit lines: counts by layout, the
files, the read gaps and durations), never a row. A row is made from the evidence at read time with what belongs to the snapshot and not to the run: the environment (the provider table),
the kernel journals (hung tasks), the backend, the slot. So a cached run costs a few stats and one small file, and a run's entry stays good across snapshots.

The KEY of an entry is a sha256 over everything its evidence is a function of, so that an entry is used only when it would be recomputed to the same value:
- the code of the evidence (the source of the functions that read the sources and of `Ev`, and the manifests' file table): another code is another key, so a fix never serves a stale entry;
- the run's identity (provider, store run key, option, layout, attempt directory) and the provider's file-id table (the gate's ids mean files only through it);
- the sources themselves, by `(size, mtime_ns)`: the gate log and the run record (T, T-unpaginated, D), the performance logs (M, M+), the audit lines file of the run's lease;
- what the audit lines are judged by: the sealed audit record's attempt, verdict class and reason, `lines.n`, slot and the exclusion's `was`, and the exclusion windows of the run's provider and slot.
An entry that does not match is recomputed and replaced; nothing is ever served on a partial match. The directory is mode 700 and holds per-run evidence: it is sealed like the snapshot's own files."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse         # noqa: E402
import dataclasses      # noqa: E402
import hashlib          # noqa: E402
import inspect          # noqa: E402
import json             # noqa: E402
import os               # noqa: E402
import shutil           # noqa: E402
import sqlite3          # noqa: E402
import tempfile         # noqa: E402
from pathlib import Path    # noqa: E402

from . import layoutread as L   # noqa: E402

FORMAT = "layout-evidence/1"


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=list).encode()).hexdigest()


def evidence_code_sha() -> str:
    """The sha256 of the code the evidence is a function of: the readers of the three sources, the line reader, the layout map's lookups, `Ev`, and the constants they use."""
    parts = [inspect.getsource(x) for x in (L.gate_evidence, L.perf_evidence, L.scan_audit, L.audit_evidence, L._iter_lines, L._tod_gap, L._side, L._bump, L.Ev,
                                            L.LayoutMap.rel_of_path, L.LayoutMap.of_rel, L.LayoutMap.of_path)]
    parts += [L._REAL_CONTENT.pattern, repr(L.REST_OPTIONS), repr(L.MOUNT_OPTIONS), FORMAT]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def _stat(p: Path):
    try:
        st = os.stat(p)
    except OSError:
        return None
    return [st.st_size, st.st_mtime_ns]


class EvidenceCache:
    """The cache directory. Picklable (paths and hashes only), so worker processes share it; each run has its own file, so they never write the same one."""

    def __init__(self, root: Path, lm: "L.LayoutMap", ids_by_provider: dict[str, dict[str, str]], audit_root: Path):
        self.root, self.audit_root = Path(root), Path(audit_root)
        self.lm_sha = _sha(sorted(lm.files.items()))
        self.ids_sha = {p: _sha(sorted(ids.items())) for p, ids in ids_by_provider.items()}
        self.code_sha = evidence_code_sha()

    def key(self, *, option: str, layout: str, provider: str, run_key: str, run_dir: Path, arec: dict | None, windows) -> str:
        rd = Path(run_dir)
        if option in L.REST_OPTIONS:
            src = {n: _stat(rd / n) for n in ("gate_requests.jsonl", "run_record.json")}
        else:
            src = {p.name: _stat(p) for p in sorted((rd / "oneclient_perf").glob("read_write_perf-*.csv"))}
        a = arec if isinstance(arec, dict) else {}
        used = {"attempt_dir": a.get("attempt_dir"), "class": (a.get("verdict") or {}).get("class"), "reason": (a.get("verdict") or {}).get("reason"),
                "lines_n": (a.get("lines") or {}).get("n"), "slot": (a.get("window") or {}).get("slot"), "was": (a.get("exclusion") or {}).get("was"),
                "present": isinstance(arec, dict)}
        lines = self.audit_root / provider / "runs" / run_key / rd.name / "lines.log.gz"
        return _sha({"code": self.code_sha, "lm": self.lm_sha, "ids": self.ids_sha.get(provider), "id": [provider, run_key, option, layout, rd.name], "src": src,
                     "lines": _stat(lines), "audit": used, "windows": windows or []})

    def path(self, provider: str, run_key: str, attempt: str) -> Path:
        return self.root / provider / run_key / f"{attempt}.json"

    def get(self, key: str, provider: str, run_key: str, attempt: str) -> dict | None:
        try:
            d = json.loads(self.path(provider, run_key, attempt).read_text())
        except (OSError, ValueError):
            return None
        if d.get("format") != FORMAT or d.get("key") != key:
            return None
        return {n: (None if d[n] is None else L.Ev(**d[n])) for n in ("gate", "perf", "audit")}

    def put(self, key: str, provider: str, run_key: str, attempt: str, ev: dict) -> None:
        p = self.path(provider, run_key, attempt)
        for d in (self.root, p.parent.parent, p.parent):
            d.mkdir(mode=0o700, exist_ok=True)
        data = {"format": FORMAT, "key": key, **{n: (None if ev[n] is None else dataclasses.asdict(ev[n])) for n in ("gate", "perf", "audit")}}
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".tmp-")
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)


# ---- fill ---------------------------------------------------------------------------------------------------------------------------------
def attempts_of(merged_root: Path) -> list[dict]:
    """Every finished attempt of the merged store with its run: {run_key, block, option, layout, run_dir}. The store is copied before it is opened (it may be a sealed, read-only tree)."""
    with tempfile.TemporaryDirectory() as td:
        shutil.copyfile(Path(merged_root) / "state.sqlite", Path(td) / "state.sqlite")
        c = sqlite3.connect(Path(td) / "state.sqlite")
        try:
            rows = c.execute("select r.run_key, r.block, r.option, r.layout, a.run_dir from attempts a join runs r on r.run_key = a.run_key "
                             "where a.state = 'done' and a.run_dir is not null order by r.run_key, a.attempt").fetchall()
        finally:
            c.close()
    return [{"run_key": k, "block": b, "option": o, "layout": lay, "run_dir": d} for k, b, o, lay, d in rows]


def fill(merged_root: Path, cache_dir: Path, *, audit_root: Path, data_root: Path = L.DEFAULT_DATA_ROOT, bmerge_config: Path | None = None, exclusions_path: Path | None = None,
         jobs: int = 1, lm: "L.LayoutMap | None" = None) -> dict:
    """Fills the cache for every finished attempt of `merged_root` (a merged store: state.sqlite and providers.json, as bmerge writes them) that is not in it yet or changed. Returns counts."""
    merged_root = Path(merged_root)
    lm = lm or L.LayoutMap.default()
    cfg_p = Path(bmerge_config) if bmerge_config else merged_root.parent / "bmerge.json"
    ids = L.provider_ids_from(cfg_p, Path(data_root), None, lm)
    owner = json.loads((merged_root / "providers.json").read_text())["providers"]
    excl = L.load_exclusions(exclusions_path)
    cache = EvidenceCache(cache_dir, lm, ids, audit_root)
    items, skipped = [], 0
    for a in attempts_of(merged_root):
        prov = owner.get(a["run_key"])
        rd = Path(a["run_dir"])
        if prov is None or not rd.is_dir() or a["option"] not in (*L.REST_OPTIONS, *L.MOUNT_OPTIONS):
            skipped += 1
            continue
        rec_p = Path(audit_root) / prov / "runs" / a["run_key"] / rd.name / "m_audit.json"
        try:
            rec = json.loads(rec_p.read_text())
        except (OSError, ValueError):
            rec = None
        items.append(dict(run_key=a["run_key"], option=a["option"], layout=a["layout"], provider=prov, run_dir=rd, platform_record={"audit": rec} if rec else None))
    L._init_work(ids, lm, Path(audit_root), excl, None, cache)
    if jobs > 1 and len(items) > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(jobs, initializer=L._init_work, initargs=(ids, lm, Path(audit_root), excl, None, cache)) as ex:
            status = list(ex.map(L._fill_one, items, chunksize=4))
    else:
        status = [L._fill_one(kw) for kw in items]
    return {"attempts": len(items), "computed": status.count("miss"), "cached": status.count("hit"), "skipped": skipped}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.layoutcache", description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["fill"])
    ap.add_argument("--merged-root", required=True, type=Path, help="a merged store (state.sqlite + providers.json), as bmerge writes it; <seal>/M")
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--audit-root", type=Path, default=L.DEFAULT_AUDIT_ROOT)
    ap.add_argument("--data-root", type=Path, default=L.DEFAULT_DATA_ROOT)
    ap.add_argument("--bmerge-config", type=Path, help="the providers' index roots (default: <merged root>/../bmerge.json)")
    ap.add_argument("--exclusions", type=Path, help="the exclusion list in force (default: none: an entry made without it is not used where it applies)")
    ap.add_argument("--jobs", type=int, default=1)
    ns = ap.parse_args(argv)
    try:
        os.umask(0o077)
        r = fill(ns.merged_root, ns.cache, audit_root=ns.audit_root, data_root=ns.data_root, bmerge_config=ns.bmerge_config, exclusions_path=ns.exclusions, jobs=ns.jobs)
    except L.LayoutReadError as e:
        print(f"layoutcache refused: {e}", file=sys.stderr)
        return 2
    except Exception as e:      # noqa: BLE001
        print(f"layoutcache FAILED {type(e).__name__}", file=sys.stderr)
        return 1
    print("layoutcache fill " + " ".join(f"{k}={v}" for k, v in r.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
