"""cut -> pipeline -> analysis, all under `out`. Prints one line: counts of the whole cut, never a per-option figure or a contrast."""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

from . import codecheck
from . import cut as cutmod
from . import stamp
from .guard import GuardError, WriteGuard, captured, check_out

HERE = Path(__file__).resolve().parent
NONE = "none"        # an explicit statement that an input does not exist yet (the analysis's own 'not run' / 'not measured')
NO_TREE = "not run: no --campaign-tree"


class SnapshotRefused(RuntimeError):
    """A refusal that comes after the cut was made: the exit code is 2 and the --out stays as it is, for `analyse` to resume."""


def running_root() -> Path:
    """The tree this process runs the pipeline and the analysis from."""
    import icsa
    return Path(icsa.__file__).resolve().parents[1]


@dataclasses.dataclass
class Args:
    campaign_root: Path
    t: str
    cap_s: float
    out: Path
    overhead: str
    fidelity_rows: str
    inspection_labels: str
    no_outcome: str
    final: bool                  # no default: the paper's snapshot or not (cut.check_final)
    inspection_coverage: str | None = None
    h3_table: str | None = None
    instrument_audit: str | None = None
    config: str | None = None
    index_root: str | None = None
    data_dir: str | None = None
    s1_dir: str = "s1z"
    mount_root: str | None = None
    jobs: int = 1
    worker_gib: int = 8
    pipeline_cache: str | None = None     # a pcache directory (`python -m snapshot.pcache fill`): read only; runs missing from it are processed here
    campaign_tree: str | None = None      # the campaign's code tree on this host: the pipeline and the analysis must be its code, byte for byte (codecheck.py)
    max_planned_misses: int | None = None  # with a pipeline cache: refuse more unexplained planned misses than this (-1: no limit; default: pcache's own)
    recohort: bool = True                 # recompute each row's out_of_cohort against THIS cut before the analysis (snapshot/recohort.py); false: the launch's stamp stands
    providers: str | None = None          # B's merge (snapshot/bmerge.py): a config file; the cut is of the merged store, and each run is labelled by its provider's index and cache


def _log(out: Path, msg: str) -> None:
    with open(out / "snapshot.log", "a") as fh:
        fh.write(f"{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}\n")


def prepare(a: Args, resume: bool = False) -> WriteGuard:
    """Checks the paths, creates `out`, points every temporary and cache directory into it, and arms the write guard. `resume`: `out` may hold the cut an
    earlier `cut` stage made (and nothing of an analysis)."""
    out = check_out(a.out, a.campaign_root, resume_cut=resume)
    for d in (out, out / ".tmp", out / ".captured", out / "work"):
        d.mkdir(parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    tmp = out / ".tmp"
    os.environ.update(TMPDIR=str(tmp), MPLCONFIGDIR=str(tmp / "mpl"), XDG_CACHE_HOME=str(tmp / "cache"), PYTHONDONTWRITEBYTECODE="1")
    sys.dont_write_bytecode = True
    import tempfile
    tempfile.tempdir = str(tmp)
    return WriteGuard([out]).install()


def do_cut(a: Args, now: dt.datetime | None = None) -> dict:
    info = cutmod.make_cut(a.campaign_root, a.out / "work", cutmod.parse_t(a.t), a.cap_s, now, a.no_outcome)
    _log(a.out, f"cut: runs_in_cut={info['runs_in_cut']} done={info['done']} exhausted={info['infra_exhausted']} unfinished={info['unfinished']} "
                f"started_later_or_never={info['runs_started_later_or_never']} no_outcome_as_exhausted={info['no_outcome_as_exhausted']}")
    return info


def _empty_file(p: Path, text: str = "") -> Path:
    p.write_text(text)
    return p


def do_analyse(a: Args, resources=None) -> dict:
    import pandas as pd
    from icsa.analysis import adapter, config as cfgmod, inspection as INS, overhead as OV
    from icsa.analysis.run import run_all
    from icsa.pipeline.postrun import run_pipeline
    from icsa.pipeline.resources import Production

    out, cutdir = a.out, a.out / "work" / "cut"
    if not (cutdir / "state.sqlite").is_file():
        raise GuardError("no cut under --out/work/cut: run `cut` first")
    cut = json.loads((cutdir / "cut.json").read_text())
    cutmod.check_final(a.final, cut["t"], cut["no_outcome"])      # against the cut that was made, not only against the arguments
    res = None if a.providers else (resources or Production(Path(a.index_root) if a.index_root else None, a.s1_dir,
                                                            Path(a.mount_root) if a.mount_root else None, Path(a.data_dir) if a.data_dir else None))
    pdir, tdir = out / "pipeline", out / "tables"
    pc = merge = None
    with captured(out / ".captured" / "pipeline.log"):
        if a.providers:
            if a.pipeline_cache:
                raise SnapshotRefused("--providers names each provider's own cache: it does not combine with --pipeline-cache")
            from . import bmerge, pcache
            try:
                providers_path, providers = bmerge.load_config(a.providers)
                if isinstance(resources, dict):      # the tests: a Resources per provider
                    providers = {p: {**c, "resources": resources[p]} for p, c in providers.items()}
                r = bmerge.assemble_merged(cutdir, providers_path, providers, pdir, record_dir=out / "work" / "merge", jobs=a.jobs, worker_gib=a.worker_gib,
                                           max_planned_misses=a.max_planned_misses)
            except pcache.PlannedMissLimit as e:      # before anything was written to pipeline/: the out keeps its cut, and `analyse` can follow a fill
                raise SnapshotRefused(f"{e}: a provider's cache does not match this host's code, data, limits or mirror; run its fill or check the key") from e
            except bmerge.MergeError as e:
                raise SnapshotRefused(f"{e}") from e
            pm, pc = r["manifest"], r["pcache"]
            merge = {"stores": bmerge.read_merge_info(providers_path), "providers": r["merge"]["providers"]}
        elif a.pipeline_cache:
            from . import pcache
            try:
                r = pcache.assemble(cutdir, Path(a.pipeline_cache), pdir, res, jobs=a.jobs, worker_gib=a.worker_gib, max_planned_misses=a.max_planned_misses)
            except pcache.PlannedMissLimit as e:      # before anything was written to pipeline/: the out keeps its cut, and `analyse` can follow a fill
                raise SnapshotRefused(f"{e}: the cache does not match this host's code, data, limits or mirror; run fill or check the key") from e
            pm, pc = r["manifest"], r["pcache"]
        else:
            pm = run_pipeline(cutdir, pdir, res, jobs=a.jobs, worker_gib=a.worker_gib)
    _log(out, f"pipeline: scored={pm['counts']['scored']} failed={pm['counts']['failed']}")
    if pc is not None:
        _log(out, f"pipeline: planned_hits={pc['planned_hits']} planned_misses={pc['planned_misses']} planned_unexplained_misses={pc['planned_unexplained_misses']}")
    cfg = cfgmod.load(a.config)
    ov = OV.OverheadTable.absent() if a.overhead == NONE else OV.load(a.overhead, cfg)
    fid = [] if a.fidelity_rows == NONE else adapter.load_fidelity_rows(a.fidelity_rows)
    if a.inspection_labels == NONE:
        ins = INS.InspectionInput.not_run()
    else:
        ins = INS.load(a.inspection_labels, a.inspection_coverage)
    rows = adapter.load_jsonl(pdir / "scored_rows.jsonl")
    recohort_info = None
    if a.recohort:          # the cohort of THIS cut, not the launch's stamp in the run directory (snapshot/recohort.py): a no-op on any cut that does not pass the launch's own
        from . import recohort
        rows, recohort_info = recohort.apply(rows, cutdir / "state.sqlite")
        recohort.write_info(recohort_info, out / "work" / "recohort.json")
        _log(out, f"recohort: rows={recohort_info['rows']} stamp_out_to_in={recohort_info['stamp_out_to_in']} stamp_in_to_out={recohort_info['stamp_in_to_out']} "
                  f"no_counted_start={recohort_info['no_counted_start']}")
    with captured(out / ".captured" / "analysis.log"):
        am = run_all(rows, tdir, cfg, pd.read_csv(pdir / "causes.csv"), fidelity_rows=fid,
                     h3_table=pd.read_csv(a.h3_table) if a.h3_table else None,
                     cause_flags=pd.read_csv(pdir / "cause_flags.csv"), infra=pdir / "infra.json", overhead=ov, inspection=ins,
                     audit=a.instrument_audit)
    line = stamp.header(a.final, cut["t"])          # after run_all returned: a refusal there (no primary row) leaves no table claiming anything
    stamp.stamp_tables(tdir, line)
    stamp.check_tables(tdir, line)
    _log(out, f"analysis: rows={len(rows)} files={sum(1 for _ in tdir.rglob('*') if _.is_file())}")
    return {"pipeline": pm, "analysis": am, **({"pipeline_cache": pc} if pc is not None else {}), **({"merge": merge} if merge is not None else {}),
            **({"recohort": recohort_info} if recohort_info is not None else {})}


def manifest(a: Args, cut: dict, res: dict | None, check: dict | None = None) -> dict:
    from icsa import codestamp
    root = running_root()
    tool = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(HERE.glob("*.py")))).hexdigest()
    m = {"format": "icsa-snapshot-v1", "t": cut["t"], "cap_s": cut["cap_s"], "last_start_included": cut["last_start_included"],
         "cut": {k: v for k, v in cut.items() if k not in ("t", "cap_s", "last_start_included")},
         "no_outcome": cut["no_outcome"], "final": a.final, "inputs": {"overhead": a.overhead, "fidelity_rows": a.fidelity_rows, "inspection_labels": a.inspection_labels},
         "snapshot_tool_sha256": tool, "output_dir": str(a.out),
         "snapshot_code": codestamp.version(root), "tree_data_sha256": codecheck.tree_data_hash(root)}
    if res:
        m["pipeline_hashes"] = res["pipeline"].get("hashes")
        m["analysis_config_sha256"] = res["analysis"].get("config_sha256")
        m["analysis_git_commit"] = res["analysis"].get("git_commit")
        m["analysis_git_dirty"] = res["analysis"].get("git_dirty")
        if res.get("pipeline_cache") is not None:
            pc = res["pipeline_cache"]
            m["pipeline_cache"] = {"dir": str(a.pipeline_cache or a.providers), "planned_hits": pc["planned_hits"], "planned_misses": pc["planned_misses"],
                                   "planned_unexplained_misses": pc["planned_unexplained_misses"], "planned_miss_limit": pc["planned_miss_limit"]}
        if res.get("recohort") is not None:       # totals only: how many rows' stamps this cut changed
            m["recohort"] = res["recohort"]
        if res.get("merge") is not None:      # counts only: the duplicates, who won, and each provider's hits and misses
            m["merge"] = res["merge"]
    if a.campaign_tree:
        tree = Path(a.campaign_tree)
        m["campaign_tree"] = {"path": str(tree), "version": codestamp.version(tree), "data_sha256": codecheck.tree_data_hash(tree)}
        m["code_check"] = check
    else:
        m["code_check"] = NO_TREE
    if res:       # what the runs were made by, to read beside the check; recorded, never refused on (an older rehearsal's records carry an older commit)
        commits = codecheck.run_record_commits(a.out / "pipeline" / "run_records.jsonl")
        m["run_record_commits"] = commits
        if a.campaign_tree:
            m["campaign_head_in_records"] = m["campaign_tree"]["version"]["commit"] in commits
    return m


def run(a: Args, stage: str = "all", resources=None, now: dt.datetime | None = None) -> tuple[int, str]:
    """Returns (exit code, the one line for stdout)."""
    a.out = Path(os.path.abspath(a.out))
    static = None
    try:
        cutmod.check_final(a.final, a.t, a.no_outcome)      # before anything is made
        if a.final and not a.campaign_tree:
            return 2, "snapshot refused: --final true needs --campaign-tree PATH, the campaign's code tree on this host (snapshot/codecheck.py)"
        if a.campaign_tree:
            if not Path(a.campaign_tree).is_dir():
                return 2, f"snapshot refused: --campaign-tree {a.campaign_tree} is not a directory"
            static = codecheck.static_check(running_root(), Path(a.campaign_tree))      # still before anything is made: a refusal leaves no --out
            if why := codecheck.refusal(static):
                return 2, f"snapshot refused: {why}"
        guard = prepare(a, resume=stage == "analyse")
    except (GuardError, cutmod.CutError) as e:
        return 2, f"snapshot refused: {type(e).__name__}: {e}"
    try:
        cut = do_cut(a, now) if stage in ("all", "cut") else json.loads((a.out / "work" / "cut" / "cut.json").read_text())
        res = do_analyse(a, resources) if stage in ("all", "analyse") else None
        check = None
        if static is not None:
            check = {k: v for k, v in static.items() if k != "static"}
            if res is not None:         # what was loaded must be what the walk found, and the campaign's, byte for byte
                rt = codecheck.runtime_check(running_root(), Path(a.campaign_tree), static["static"])
                check.update(runtime_files=rt["runtime_files"], runtime_not_in_static=rt["runtime_not_in_static"])
                if rt["runtime_not_in_static"] or rt["runtime_differ"]:
                    raise codecheck.CodeCheckError(f"runtime check: loaded but not in the static walk: {rt['runtime_not_in_static']}; "
                                                   f"loaded but differing from the campaign tree: {rt['runtime_differ']}")
        m = manifest(a, cut, res, check)
        (a.out / "SNAPSHOT.json").write_text(json.dumps(m, indent=1, sort_keys=True))
        sha = hashlib.sha256((a.out / "SNAPSHOT.json").read_bytes()).hexdigest()[:16]
        failed = res["pipeline"]["counts"]["failed"] if res else None
        return 0, (f"snapshot ok stage={stage} runs_in_cut={cut['runs_in_cut']} done={cut['done']} unfinished={cut['unfinished']} "
                   f"exhausted={cut['infra_exhausted']} no_outcome_as_exhausted={cut['no_outcome_as_exhausted']}" + (f" pipeline_failed={failed}" if failed is not None else "") + f" manifest={sha} out={a.out}")
    except SnapshotRefused as e:
        return 2, f"snapshot refused: {e}"
    except BaseException as e:    # noqa: BLE001 -- the detail goes into the sealed directory, never to the terminal
        (a.out / ".captured" / "error.txt").write_text(traceback.format_exc())
        return 1, f"snapshot FAILED {type(e).__name__} (detail in {a.out}/.captured/error.txt)"
    finally:
        guard.off()
