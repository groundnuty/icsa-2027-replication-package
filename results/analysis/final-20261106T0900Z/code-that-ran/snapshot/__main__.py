import sys
sys.dont_write_bytecode = True      # before anything else is imported: a .pyc written beside the source is a write outside --out

import argparse                     # noqa: E402
from pathlib import Path            # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="snapshot", description=__doc__)
    ap.add_argument("stage", choices=["run", "cut", "analyse"])
    ap.add_argument("--campaign-root", required=True, type=Path, help="holds state.sqlite (read-only here); run directories are read where the store says")
    ap.add_argument("--t", required=True, help="the snapshot's time, ISO UTC, not in the future")
    ap.add_argument("--cap-s", required=True, type=float, help="the run time cap in seconds. NO default: it is the main block's cap")
    ap.add_argument("--out", required=True, type=Path, help="a new directory; the only place anything is written. In a git work tree it must be an ignored path")
    ap.add_argument("--overhead", required=True, help="#12's overhead JSON, or 'none' (stated: not measured)")
    ap.add_argument("--fidelity-rows", required=True, help="#11's adapter_rows.jsonl, or 'none' (stated: not run)")
    ap.add_argument("--inspection-labels", required=True, help="the coders' labels JSONL, or 'none' (stated: inspection has not run)")
    ap.add_argument("--no-outcome", required=True, choices=["report", "as-exhausted"],
                    help="a cohort run with no outcome at t: left unfinished (earlier parts), or counted as an exhausted run (amendment 29(c): the paper's snapshot). No default")
    ap.add_argument("--final", required=True, choices=["true", "false"],
                    help="true only for the paper's fixed snapshot (amendment 29(c)): --t 2026-11-06T09:00:00Z (amendment 43(a)) with --no-outcome as-exhausted; refused for any other cut. No default")
    ap.add_argument("--inspection-coverage", default=None)
    ap.add_argument("--h3-table", default=None)
    ap.add_argument("--instrument-audit", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--index-root", default=None)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--s1-dir", default="s1z")
    ap.add_argument("--mount-root", default=None)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--worker-gib", type=int, default=8)
    ap.add_argument("--pipeline-cache", default=None,
                    help="a pcache directory filled by `python -m snapshot.pcache fill`; read only; runs missing from it are processed here")
    ap.add_argument("--max-planned-misses", type=int, default=None,
                    help="with --pipeline-cache: refuse (exit 2, the cut kept for `analyse`) more planned misses than this that the last fill's failures.json does not "
                         "explain; -1: no limit; default max(20, 10%% of the analysed runs)")
    ap.add_argument("--recohort", choices=["true", "false"], default="true",
                    help="recompute every row's out_of_cohort against this cut's cohort before the analysis (a dispatcher stamps it against its launch's cut, which a later cut passes); default true")
    ap.add_argument("--unscorable-correction", default=None,
                    help="correction-unscorable-1.json: runs that ended done by the time cap but cannot be scored here (memory): counted K by count, no measures (science 6 Nov 09:25Z)")
    ap.add_argument("--k-by-count", default=None,
                    help="comma-separated run keys that ended done by the time cap but cannot be scored here (memory): counted K by count, no measures (science 6 Nov, fallback for main I48 D S1)")
    ap.add_argument("--capped-stores", default=None,
                    help="the directory of the frozen store copies (<dir>/<store>/state.sqlite): a capped attempt that the merge dropped (its retry finished on another store) is put back from its own store")
    ap.add_argument("--capped-correction", default=None,
                    help="lane-site_aaudit's correction-capped-7.json: runs whose earliest analysable attempt ran past the cap and ended infra_fail count as ended by the cap (exhausted here: no record is made up); the other attempts are held aside")
    ap.add_argument("--exclude-runs", default=None,
                    help="a JSON file naming runs to leave out of the cut (a sensitivity: the flagged Lab-504 runs); not for the primary tables")
    ap.add_argument("--final-t", default=None,
                    help="ISO UTC: the instant --final true is tied to, instead of 2026-11-06T09:00:00Z (only for the rerun after the re-freeze; then --t must equal it)")
    ap.add_argument("--cohort-cut", default=None,
                    help="ISO UTC: the last start the cohort includes, instead of t - cap-s (a fixed instant, not later than --t); the cohort stamp, recohort and the cut follow it")
    ap.add_argument("--providers", default=None,
                    help="B's merge (python -m snapshot.bmerge): the config file naming the merge root and each provider's cache and index; --campaign-root is then the merged root, "
                         "and each run is labelled by its provider's index and served from its provider's cache. Not with --pipeline-cache")
    ap.add_argument("--campaign-tree", default=None,
                    help="the campaign's code tree on this host: the icsa files the pipeline and the analysis import, and data/, must equal it byte for byte, or the "
                         "snapshot is refused (exit 2, nothing made). REQUIRED with --final true")
    ns = ap.parse_args(argv)
    from .run import Args, run
    a = Args(**{k: v for k, v in vars(ns).items() if k != "stage"} | {"final": ns.final == "true", "recohort": ns.recohort == "true"})
    code, line = run(a, {"run": "all"}.get(ns.stage, ns.stage))
    print(line, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
