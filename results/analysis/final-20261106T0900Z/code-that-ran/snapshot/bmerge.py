"""B's extra dispatchers (#34): merge main's store with the stores of runs made on other providers, label each run with ITS provider's index and
cache, and let the frozen `run_pipeline` write every output over the merged cut.

    python -m snapshot.bmerge stores   --main-root R --b NAME=ROOT [--b ...] --out M        # one merged "campaign root": M/state.sqlite
    python -m snapshot cut --campaign-root M ...                                              # unchanged: the cut of the merged store
    python -m snapshot.bmerge assemble --cut OUT/work/cut --config bmerge.json --out OUT/pipeline
    python -m snapshot analyse ... --providers bmerge.json                                    # the same, inside the snapshot's guard

The seam is the STORE, not the outputs. Everything a snapshot writes (scored rows, run records, labels, the cause tables, the infra export,
the second coder's sample, the manifest) comes from the frozen `postrun.run_pipeline`, run once over one store; nothing of it is merged or
rewritten here. What differs per provider is only how a run is labelled (`Resources.index`: the Onedata file ids that turn a gate log's
requests into files) and which pipeline cache holds its result, so those are the two things done per provider:

  stores    Per run key the FIRST STARTED ATTEMPT across the stores wins (science's ruling, #34: "first started wins at the merge, and the duplicates
            are counted"). The winner's run row and all of its attempts go into the merged store; the loser's are dropped, so the infra account
            (discarded usage, retries by kind, ...) holds only the winner's attempts and `export_infra` sees one done attempt per run. A store that
            never started a run does not contend for it. When no store started it, the earliest deferral decides, else main's row stands.
            Counted, never listed by run key on a terminal: duplicates, who won, ties (broken by store order: main first), the loser's attempts and
            usage, the runs whose loser finished while the winner did not, and the duplicates `counted_starts()` (the cut's own notion, which treats
            a deferral as a start) would have decided the other way.
  assemble  For each provider that won a finished run: the cut's store reduced to that provider's runs, then the UNMODIFIED `pcache.assemble` with that
            provider's `Resources` and cache (so main's existing cache keys hold: `pcache.py` and the walk are untouched), the per-run results
            captured as they leave the pipeline's pool; then the frozen `run_pipeline` over the whole merged cut with those results stood in for
            the per-run call, as `pcache` stands in a cache entry. A run that no pass returned, or two did, is an error, never a dropped row.

`snapshot/` is outside `codestamp.ROOTS` and outside the code check's walk, and `pcache.py` is not changed: a new file here moves no cache key.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse                     # noqa: E402
import contextlib                   # noqa: E402
import datetime as dt               # noqa: E402
import json                         # noqa: E402
import pickle                       # noqa: E402
import shutil                       # noqa: E402
import sqlite3                      # noqa: E402
import tempfile                     # noqa: E402
import time                         # noqa: E402
from pathlib import Path           # noqa: E402

from icsa.campaign.store import Store   # noqa: E402
from icsa.pipeline import postrun   # noqa: E402

from . import cut as cutmod         # noqa: E402
from . import pcache                # noqa: E402

PROVIDERS_FORMAT = "icsa-bmerge-providers-v1"
PROVIDERS_META = "bmerge_providers"      # the store's own record of who owns each run: the providers file must agree with it, or the cut is not of that merge
RUN_FIELDS = ("block", "instance_id", "option", "layout", "model", "seed", "exclude_from_analysis")     # what a B run must share with main's row of it
# `seq` is only the manifest's order, which `export_infra` lists by: a B run takes main's seq (counted in `seq_differs` when B's was another), so the lists keep main's order
USAGE_FIELDS = ("input_tokens", "output_tokens", "wall_s")


class MergeError(RuntimeError):
    """The stores cannot be merged, or a pass left a run without exactly one result. Messages carry counts and field names, never a run key."""


# ---- the stores ---------------------------------------------------------------------------------------------------------------------

def _utc(ts: str) -> dt.datetime:
    return cutmod.utc(ts)


def first_attempt_start(attempts: list[dict]) -> str | None:
    """The run's first started attempt in this store (state 'unstarted' is not one), or None. A retry never moves it."""
    starts = [a["started_utc"] for a in attempts if a["state"] != "unstarted" and a["started_utc"]]
    return min(starts, key=_utc) if starts else None


def counted_start(run: dict, attempts: list[dict]) -> str | None:
    """`Store.counted_starts` for one run: the earlier of its first started attempt and its deferral. Only used to count disagreements."""
    c = [t for t in (first_attempt_start(attempts), run.get("deferred_utc")) if t]
    return min(c, key=_utc) if c else None


class _Loaded:
    def __init__(self, name: str, root: Path, tmp: Path, idx: int):
        self.name, self.root = name, Path(root)
        dest = tmp / f"store{idx}.sqlite"
        cutmod.copy_store(self.root / "state.sqlite", dest)          # never opened where it is: a read-only open of a quiescent store makes -wal and -shm
        Store(dest).close()                                           # the copy brought to the current schema: every store has the same columns
        self.path = dest
        db = sqlite3.connect(dest)
        db.row_factory = sqlite3.Row
        try:
            self.runs = {r["run_key"]: dict(r) for r in db.execute("SELECT * FROM runs")}
            self.attempts: dict[str, list[dict]] = {}
            for a in db.execute("SELECT * FROM attempts ORDER BY id"):
                self.attempts.setdefault(a["run_key"], []).append(dict(a))
            self.meta = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM meta")}
        finally:
            db.close()

    def first_start(self, k: str) -> str | None:
        return first_attempt_start(self.attempts.get(k, [])) if k in self.runs else None


def _check_prefixes(stores: list[_Loaded]) -> None:
    """A store's run directories must be where ITS mirror put them, and no two stores may share a mirror: two stores that both record
    `/mnt/volume2/icsa-2027/runs/<key>/attempt1.try1` read one directory for two runs, and nothing shows it."""
    seen: dict[str, str] = {}
    for s in stores:
        p = s.meta.get("fetch_run_dir_prefix")
        if not p:
            raise MergeError(f"store {s.name!r} has no fetch_run_dir_prefix: it is not a `snapshot.fetch` mirror, so its run directories are not distinct from the others'")
        if p in seen:
            raise MergeError(f"stores {seen[p]!r} and {s.name!r} have the same fetch_run_dir_prefix: their run directories are not distinct")
        seen[p] = s.name
    for s in stores:
        base = s.meta["fetch_run_dir_prefix"].rstrip("/") + "/"
        off = sum(1 for atts in s.attempts.values() for a in atts if a["run_dir"] and not (a["run_dir"] + "/").startswith(base))
        if off:
            raise MergeError(f"store {s.name!r}: {off} attempt run directories are not under its fetch_run_dir_prefix")


def _check_same_manifest(main: _Loaded, other: _Loaded) -> None:
    absent = [k for k in other.runs if k not in main.runs]
    if absent:
        raise MergeError(f"store {other.name!r} has {len(absent)} run keys that are not in main: B's keys must equal main's (science, #34), so the cohort is not changed silently")
    differ: dict[str, int] = {}
    for k, r in other.runs.items():
        for f in RUN_FIELDS:
            if r.get(f) != main.runs[k].get(f):
                differ[f] = differ.get(f, 0) + 1
    if differ:
        raise MergeError(f"store {other.name!r} differs from main in {sum(differ.values())} run fields ({', '.join(f'{f}: {n}' for f, n in sorted(differ.items()))})")


def merge_stores(main_root, b_roots, out_root, *, main_name: str = "site_g", check_prefix: bool = False) -> dict:
    """Merge main's store and the B stores (`[(name, root), ...]`, roots holding `state.sqlite`) into `out_root/state.sqlite`, with `providers.json` (run key ->
    the store the run came from) and `merge.json` (the counts, which are also returned). Nothing is written if anything is refused; an existing
    `out_root/state.sqlite` is never overwritten. `check_prefix`: every store must be a fetch mirror with its own `fetch_run_dir_prefix`."""
    out_root = Path(out_root)
    names = [main_name] + [n for n, _ in b_roots]
    if len(set(names)) != len(names) or not all(names):
        raise MergeError(f"store names must be non-empty and distinct: {names}")
    if (out_root / "state.sqlite").exists():
        raise MergeError(f"{out_root / 'state.sqlite'} exists: a merge is never overwritten")
    tmp = Path(tempfile.mkdtemp(prefix="bmerge-"))
    try:
        stores = [_Loaded(n, r, tmp, i) for i, (n, r) in enumerate([(main_name, main_root), *b_roots])]
        main = stores[0]
        for s in stores[1:]:
            _check_same_manifest(main, s)
        if check_prefix:
            _check_prefixes(stores)
        winner: dict[str, int] = {}
        carry: dict[str, tuple[str, str]] = {}      # run key -> (the earliest counted start of ANY copy, its store), where that is earlier than the winner copy's own (science 6 Nov 03:44Z, amendment 24)
        info: dict = {"stores": names, "main": main_name, "duplicates": 0, "duplicates_by_option": {}, "duplicates_won": dict.fromkeys(names, 0), "ties": 0, "ties_won_by_main": 0,
                      "started": dict.fromkeys(names, 0), "loser_attempts": dict.fromkeys(names, 0),
                      "loser_usage": {n: dict(attempts=0, **dict.fromkeys(USAGE_FIELDS, 0)) for n in names},
                      "loser_done_winner_not_done": 0, "analysable_won_over_earlier_unfinished": 0, "several_finished_earliest_won": 0,
                      "winner_differs_by_counted_start": 0, "seq_differs": {n: sum(1 for k, r in s_.runs.items() if r["seq"] != main.runs[k]["seq"]) for n, s_ in zip(names, stores)}}
        for k in sorted(main.runs):
            have = [(i, s) for i, s in enumerate(stores) if k in s.runs]
            started = [(_utc(s.first_start(k)), i) for i, s in have if s.first_start(k)]
            for _, i in started:
                info["started"][names[i]] += 1
            # Science, #34 17:00Z (the registered retry rule, never outcomes): the earliest-started attempt with an ANALYSABLE outcome wins.
            # "done" is every registered ending (a time cap included); a copy that ended as infrastructure (exhausted, interrupted, a harness
            # error) or has not ended gives way to the next analysable one, as a retry would. Among finished copies the earliest start wins.
            done_started = [(t, i) for t, i in started if stores[i].runs[k]["status"] == "done"]
            if done_started:
                w = min(done_started)[1]
                if w != min(started)[1]:
                    info["analysable_won_over_earlier_unfinished"] += 1
                if len(done_started) >= 2:
                    info["several_finished_earliest_won"] += 1
            elif started:
                w = min(started)[1]
            else:           # nobody started it: the earliest deferral, else main's row
                deferred = [(_utc(s.runs[k]["deferred_utc"]), i) for i, s in have if s.runs[k].get("deferred_utc")]
                w = min(deferred)[1] if deferred else 0
            winner[k] = w
            cs = [(_utc(c), i, c) for i, s in have if (c := counted_start(s.runs[k], s.attempts.get(k, [])))]
            if len(cs) >= 2:
                first = min(cs)
                own = [x for x in cs if x[1] == w]
                if first[1] != w and (not own or first[0] < own[0][0]):
                    carry[k] = (first[2], names[first[1]])
            if len(started) >= 2:
                info["duplicates"] += 1
                opt_ = main.runs[k]["option"]            # science, #34 09:12Z: the duplicates per option are kept in merge.json (a duplicate is settled by the earliest start, never by an outcome)
                info["duplicates_by_option"][opt_] = info["duplicates_by_option"].get(opt_, 0) + 1
                info["duplicates_won"][names[w]] += 1
                top = sorted(started)
                if top[0][0] == top[1][0]:
                    info["ties"] += 1
                    info["ties_won_by_main"] += w == 0
                by_counted = min((_utc(c), i) for i, s in have if (c := counted_start(s.runs[k], s.attempts.get(k, []))))[1]      # a store that only deferred it counts here
                info["winner_differs_by_counted_start"] += by_counted != w
                if any(stores[i].runs[k]["status"] == "done" for _, i in started if i != w) and stores[w].runs[k]["status"] != "done":
                    info["loser_done_winner_not_done"] += 1
            for i, s in have:
                if i != w:
                    for a in s.attempts.get(k, []):
                        info["loser_attempts"][names[i]] += 1
                        u = info["loser_usage"][names[i]]
                        u["attempts"] += 1
                        for f in USAGE_FIELDS:
                            u[f] += a.get(f) or 0
        providers = {k: names[w] for k, w in sorted(winner.items())}
        merged = tmp / "merged.sqlite"
        shutil.copyfile(main.path, merged)
        db = sqlite3.connect(merged, isolation_level=None)
        try:
            db.execute("BEGIN IMMEDIATE")
            run_cols = [r[1] for r in db.execute("PRAGMA table_info(runs)")]
            att_cols = [r[1] for r in db.execute("PRAGMA table_info(attempts)") if r[1] != "id"]
            for k in sorted(main.runs):
                w = winner[k]
                if w == 0:
                    continue
                db.execute("DELETE FROM attempts WHERE run_key=?", (k,))
                db.execute("DELETE FROM runs WHERE run_key=?", (k,))
                r = {**stores[w].runs[k], "seq": main.runs[k]["seq"]}
                db.execute(f"INSERT INTO runs({','.join(run_cols)}) VALUES({','.join('?' * len(run_cols))})", [r.get(c) for c in run_cols])
                for a in stores[w].attempts.get(k, []):
                    db.execute(f"INSERT INTO attempts({','.join(att_cols)}) VALUES({','.join('?' * len(att_cols))})", [a.get(c) for c in att_cols])
            for k, (c0, src) in sorted(carry.items()):       # a retry is the same run restarting: it never moves the run's counted start (amendment 24); the winner copy keeps its attempts, the run counts as started when its EARLIEST copy did
                why = db.execute("SELECT deferred_why FROM runs WHERE run_key=?", (k,)).fetchone()[0]
                db.execute("UPDATE runs SET deferred_utc=?, deferred_why=? WHERE run_key=?", (c0, ((why + "; ") if why else "") + f"counted_start_source:{src}", k))
            info["counted_start_carried"] = len(carry)
            info["counted_start_carried_by_option"] = {o: sum(1 for k in carry if main.runs[k]["option"] == o) for o in sorted({main.runs[k]["option"] for k in carry})}
            info["counted_start_source"] = {k: src for k, (_, src) in sorted(carry.items())}
            info["runs"] = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            shared = db.execute("SELECT COUNT(*) FROM (SELECT run_dir FROM attempts WHERE run_dir IS NOT NULL GROUP BY run_dir HAVING COUNT(*) > 1)").fetchone()[0]
            if shared:
                raise MergeError(f"{shared} run directory paths are named by more than one attempt in the merged store: two runs would be read from one directory")
            now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for key, value in (("bmerge", info), (PROVIDERS_META, {"main": main_name, "providers": providers})):      # the provider of every run stays WITH the store, through the cut
                db.execute("INSERT INTO meta(key,value,set_utc) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, set_utc=excluded.set_utc",
                           (key, json.dumps(value, sort_keys=True, separators=(",", ":")), now))
            db.execute("COMMIT")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        out_root.mkdir(parents=True, exist_ok=True)
        (out_root / "providers.json").write_text(json.dumps({"format": PROVIDERS_FORMAT, "main": main_name, "providers": providers}, indent=1, sort_keys=True))
        (out_root / "merge.json").write_text(json.dumps(info, indent=1, sort_keys=True))
        shutil.copyfile(merged, out_root / "state.sqlite")      # last: a reader that finds the store finds the rest
        return info
    finally:
        pcache._remove_tree(tmp)


# ---- the labelling ------------------------------------------------------------------------------------------------------------------

def check_covered(expected: set, done: dict, failed: list[dict]) -> None:
    """Every analysed run of the merged cut has exactly one result: a `Processed` or a listed failure. Anything else is an error, because the replay would
    otherwise write a manifest whose counts hide a dropped run (its own assert only compares its own two counts)."""
    got = list(done) + [(f["block"], f["run_key"]) for f in failed]
    if len(got) != len(set(got)):
        raise MergeError(f"{len(got) - len(set(got))} runs have more than one result across the providers' passes")
    missing, extra = expected - set(got), set(got) - expected
    if missing:
        raise MergeError(f"{len(missing)} analysed runs of the merged cut have no result from any provider's pass")
    if extra:
        raise MergeError(f"{len(extra)} results are for runs that are not analysed in the merged cut")


@contextlib.contextmanager
def _capturing(spill: Path, sink: list[Path]):
    """The pipeline's per-instance results, kept as they leave `_process_all` in the parent (a forked pool's workers hand them back through it). Pickled
    BEFORE the pipeline sees them: it blanks each run's `record_json` once spooled, and the replay needs the text."""
    orig = postrun._process_all

    def wrapped(groups, flags_of, res, jobs, worker_gib):
        for g_done, g_failed in orig(groups, flags_of, res, jobs, worker_gib):
            path = spill / f"{len(sink):06d}.pkl"
            with open(path, "wb") as fh:
                pickle.dump((g_done, g_failed), fh, protocol=5)
            sink.append(path)
            yield g_done, g_failed
    postrun._process_all = wrapped
    try:
        yield
    finally:
        postrun._process_all = orig


@contextlib.contextmanager
def _replaying(paths: list[Path]):
    orig = postrun._process_all

    def replay(groups, flags_of, res, jobs, worker_gib):
        for p in paths:
            with open(p, "rb") as fh:
                yield pickle.load(fh)
    postrun._process_all = replay
    try:
        yield
    finally:
        postrun._process_all = orig


def _resources_for(name: str, cfg: dict):
    if cfg.get("resources") is not None:        # injected: the tests
        return cfg["resources"]
    from icsa.pipeline.resources import Production
    return Production(Path(cfg["index_root"]) if cfg.get("index_root") else None, cfg.get("s1_dir") or "s1z",
                      Path(cfg["mount_root"]) if cfg.get("mount_root") else None, Path(cfg["data_dir"]) if cfg.get("data_dir") else None)


def _release(res) -> None:
    """A `Production` keeps the last instance's reference (the whole required baseline's SST) after its pass: with several providers they would add up."""
    if hasattr(res, "_cache"):
        res._cache = None


def _require_own_index(main: str, needed: list[str], providers: dict[str, dict]) -> None:
    """A B provider's runs are labelled with ITS file ids. `Production(None)` would quietly use main's index (and `index_root/s1z` for a data dir that is not there), and
    a run whose result is in the cache never shows it: so a provider other than main must name its own index_root and data_dir, and not main's."""
    from icsa.instruments import fullindex
    cfg0 = providers.get(main) or {}
    main_dir = None if cfg0.get("resources") is not None else fullindex.index_dir(Path(cfg0["index_root"]) if cfg0.get("index_root") else None).resolve()
    for p in needed:
        c = providers[p]
        if p == main or c.get("resources") is not None:
            continue
        if not (c.get("index_root") and c.get("data_dir")):
            raise MergeError(f"provider {p!r} needs its own index_root and data_dir in the config: without them its runs would be labelled with main's file ids")
        if main_dir is not None and fullindex.index_dir(Path(c["index_root"])).resolve() == main_dir:
            raise MergeError(f"provider {p!r} names main's index: its runs would be labelled with main's file ids")


def _keep_only(db_path: Path, keep: set[str]) -> None:
    db = sqlite3.connect(db_path, isolation_level=None)
    try:
        db.execute("BEGIN IMMEDIATE")
        drop = [(r[0],) for r in db.execute("SELECT run_key FROM runs") if r[0] not in keep]
        db.executemany("DELETE FROM attempts WHERE run_key=?", drop)
        db.executemany("DELETE FROM runs WHERE run_key=?", drop)
        db.execute("COMMIT")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        db.close()


def assemble_merged(cut_root, providers_path, providers: dict[str, dict], out, *, record_dir, jobs: int = 1, worker_gib: int = 8,
                    max_planned_misses: int | None = None) -> dict:
    """The frozen pipeline over `cut_root` (a cut of the merged store), each run labelled by its provider's resources and served from its provider's cache.
    `providers`: name -> {"cache": dir, and "index_root"/"data_dir"/"s1_dir"/"mount_root" for `Production`, or "resources": an injected Resources}. A provider is
    needed (and its cache and resources read) only if it owns a finished run in the cut. Returns {"manifest", "pcache": counts summed over the providers
    (the shape `snapshot.run` reads), "merge": {"providers": per-provider counts}}. Writes `out` (the frozen pipeline's files) and, in `record_dir`,
    `providers.json` and `assemble.json`; nothing else outside private temporary directories."""
    t0 = time.monotonic()
    cut_root, out, record_dir = Path(cut_root), Path(out), Path(record_dir)
    spec = json.loads(Path(providers_path).read_text())
    if spec.get("format") != PROVIDERS_FORMAT:
        raise MergeError(f"{providers_path} is not a bmerge providers file")
    tmp = Path(tempfile.mkdtemp(prefix="bmerge-cut-"))
    try:
        all_root = tmp / "all"
        cutmod.copy_store(cut_root / "state.sqlite", all_root / "state.sqlite")
        db = sqlite3.connect(all_root / "state.sqlite")
        try:
            runs = {r[0]: r[1] for r in db.execute("SELECT run_key, status FROM runs")}
            prov = db.execute("SELECT value FROM meta WHERE key=?", (PROVIDERS_META,)).fetchone()
        finally:
            db.close()
        if prov is None:
            raise MergeError(f"the cut's store carries no {PROVIDERS_META}: it is not a cut of a merged store, so who owns each run is unknown")
        in_store = json.loads(prov[0])
        owner: dict[str, str] = in_store["providers"]
        unknown = [k for k in runs if k not in owner]
        if unknown:
            raise MergeError(f"{len(unknown)} runs of the cut have no provider in the store's own record: it is not a cut of a merge")
        stale = sum(1 for k in runs if spec["providers"].get(k) != owner[k])
        if stale or spec.get("main") != in_store["main"]:
            raise MergeError(f"{providers_path} disagrees with the store the cut was made from on {stale} runs: it belongs to another merge (a rehearsal, or an earlier one)")
        done_by: dict[str, set[str]] = {}
        for k, st in runs.items():
            if st == "done":
                done_by.setdefault(owner[k], set()).add(k)
        needed = sorted(done_by)
        lacking = [p for p in needed if p not in providers]
        if lacking:
            raise MergeError(f"no provider config for {', '.join(lacking)}: each provider that won a finished run needs its cache and index")
        _require_own_index(in_store["main"], needed, providers)
        per: dict[str, dict] = {}
        paths: list[Path] = []
        resources = {}
        for p in needed:
            keep = {k for k, w in owner.items() if w == p and k in runs}
            sub = tmp / "sub" / p
            sub.mkdir(parents=True)
            shutil.copyfile(all_root / "state.sqlite", sub / "state.sqlite")
            _keep_only(sub / "state.sqlite", keep)
            spill = tmp / "spill" / p
            spill.mkdir(parents=True)
            resources[p] = res = _resources_for(p, providers[p])
            with _capturing(spill, paths):
                r = pcache.assemble(sub, Path(providers[p]["cache"]), tmp / "pass" / p, res, jobs=jobs, worker_gib=worker_gib, max_planned_misses=max_planned_misses)
            _release(res)
            per[p] = {"analysed": len(done_by[p]), **{k: v for k, v in r["pcache"].items() if k != "pipeline_seconds"},
                      "scored": r["manifest"]["counts"]["scored"], "failed": r["manifest"]["counts"]["failed"]}
        res0 = resources[needed[0]] if needed else _resources_for(next(iter(providers)), providers[next(iter(providers))])
        store = postrun.ReadOnlyStore(all_root / "state.sqlite")
        try:
            from icsa.campaign.export import export_infra
            expected = {(e["block"], e["key"]) for e in export_infra(store, res0.instances())["analysed_attempts"]}
            _release(res0)
        finally:
            store.close()
        done: dict = {}
        failed: list[dict] = []
        for p in paths:
            with open(p, "rb") as fh:
                d, f = pickle.load(fh)
            done.update({k: None for k in d})
            failed += f
        check_covered(expected, done, failed)
        del done
        with _replaying(paths):
            manifest = postrun.run_pipeline(all_root, out, res0, jobs=1, worker_gib=worker_gib)
    finally:
        pcache._remove_tree(tmp)
    record_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(providers_path, record_dir / "providers.json")
    agg = {k: sum(v[k] or 0 for v in per.values()) for k in ("planned_hits", "planned_misses", "planned_uncacheable", "planned_unexplained_misses")}
    agg["planned_miss_limit"] = {p: v["planned_miss_limit"] for p, v in per.items()}
    info = {"providers": per, "seconds": round(time.monotonic() - t0, 3)}
    (record_dir / "assemble.json").write_text(json.dumps(info, indent=1, sort_keys=True))
    return {"manifest": manifest, "pcache": agg, "merge": info}


def load_config(path) -> tuple[Path, dict[str, dict]]:
    """{"merge_root": dir holding providers.json, "providers": {name: {"cache": ..., "index_root": ..., "data_dir": ..., "s1_dir": ..., "mount_root": ...}}}"""
    c = json.loads(Path(path).read_text())
    try:
        root, providers = Path(c["merge_root"]), c["providers"]
        assert isinstance(providers, dict) and all("cache" in v for v in providers.values())
    except (KeyError, AssertionError, TypeError) as e:
        raise MergeError(f"{path} must hold merge_root and providers (each with a cache)") from e
    return root / "providers.json", providers


def read_merge_info(providers_path) -> dict | None:
    """The merge's own counts (`merge.json`, beside `providers.json`), or None if it is not there."""
    try:
        return json.loads((Path(providers_path).parent / "merge.json").read_text())
    except (OSError, ValueError):
        return None


# ---- command line -------------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.bmerge", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stores", help="merge main's store and the B stores into one campaign root")
    s.add_argument("--main-root", required=True, type=Path, help="main's fetch mirror (holds state.sqlite)")
    s.add_argument("--main-name", default="site_g")
    s.add_argument("--b", action="append", default=[], metavar="NAME=ROOT", help="a B store's name and its fetch mirror; repeatable")
    s.add_argument("--out", required=True, type=Path)
    s.add_argument("--no-prefix-check", action="store_true", help="do not require a distinct fetch_run_dir_prefix per store (rehearsals on copies only)")
    a = sub.add_parser("assemble", help="label each run with its provider's index and cache, then the frozen pipeline over the merged cut")
    a.add_argument("--cut", required=True, type=Path, help="holds state.sqlite: the cut of the merged store")
    a.add_argument("--config", required=True, type=Path)
    a.add_argument("--out", required=True, type=Path)
    a.add_argument("--record-dir", type=Path, default=None, help="where providers.json and assemble.json go (default: beside --out)")
    a.add_argument("--jobs", type=int, default=1)
    a.add_argument("--worker-gib", type=int, default=8)
    a.add_argument("--max-planned-misses", type=int, default=None)
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "stores":
            b = []
            for spec in ns.b:
                n, _, r = spec.partition("=")
                if not n or not r:
                    raise MergeError(f"--b {spec!r} is not NAME=ROOT")
                b.append((n, Path(r)))
            i = merge_stores(ns.main_root, b, ns.out, main_name=ns.main_name, check_prefix=not ns.no_prefix_check)
            print(f"bmerge stores runs={i['runs']} duplicates={i['duplicates']} ties={i['ties']} loser_done_winner_not_done={i['loser_done_winner_not_done']} "
                  f"winner_differs_by_counted_start={i['winner_differs_by_counted_start']} " + " ".join(f"dup_option_{o}={c}" for o, c in sorted(i["duplicates_by_option"].items())) + " " + " ".join(f"won_{n}={c}" for n, c in i["duplicates_won"].items())
                  + " " + " ".join(f"started_{n}={c}" for n, c in i["started"].items()))
            return 0
        providers_path, providers = load_config(ns.config)
        r = assemble_merged(ns.cut, providers_path, providers, ns.out, record_dir=ns.record_dir or ns.out.parent / "merge", jobs=ns.jobs,
                            worker_gib=ns.worker_gib, max_planned_misses=ns.max_planned_misses)
    except (MergeError, cutmod.CutError, pcache.PcacheError, sqlite3.Error) as e:
        print(f"bmerge {ns.cmd} FAILED {type(e).__name__}: {str(e)[:300]}", file=sys.stderr)
        return 2
    m, c = r["manifest"], r["pcache"]
    print(f"bmerge assemble scored={m['counts']['scored']} failed={m['counts']['failed']} planned_hits={c['planned_hits']} planned_misses={c['planned_misses']} "
          + " ".join(f"{p}_hits={v['planned_hits']}/{v['analysed']}" for p, v in sorted(r["merge"]["providers"].items())))
    return 1 if m["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
