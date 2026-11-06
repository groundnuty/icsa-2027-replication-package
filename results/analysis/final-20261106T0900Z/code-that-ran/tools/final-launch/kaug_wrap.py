"""ROUTE D, the composition side step (lane-snap6, 6 Nov; science's condition on option B): `python -m snapshot analyse` where the FROZEN analysis (icsa/analysis, unchanged) is called with the primary frame df
EXTENDED by the exhausted_frame() rows (K rows without measures) of ONLY the capped-correction runs, so that the omission bounds' denominators, the time-cap share, the end-to-end denominator and the cell counts
include them; the same runs are taken OUT of the infra account so the exhausted-sensitivity tables do not count them twice. Every rows_to_frame call inside run_all is extended with the K rows (see r2f). The output is a separate directory (out-kaug/) and the plain out/ stays the frozen result.
    cd <overlay tree> && PYTHONPATH=. python kaug_wrap.py analyse <the same arguments as `python -m snapshot analyse`, with --out .../out-kaug>
The capped runs are read from the cut store's meta (capped_correction_runs, written by cut --capped-correction) under <out>/work/cut/state.sqlite. Nothing is printed but one line of counts."""
import dataclasses
import json
import os
import runpy
import sqlite3
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.getcwd())


def _capped_keys() -> set:
    out = sys.argv[sys.argv.index("--out") + 1]
    try:
        c = sqlite3.connect(f"file:{out}/work/cut/state.sqlite?mode=ro", uri=True)
        r = c.execute("select value from meta where key='capped_correction_runs'").fetchone()
        return set(json.loads(r[0])) if r else set()
    except Exception:       # noqa: BLE001
        return set()


def _install() -> None:
    import pandas as pd
    import icsa.analysis.run as R
    import icsa.analysis.infra as I
    import icsa.analysis.adapter as A
    from icsa.analysis import config as cfgmod
    orig_run_all, orig_r2f = R.run_all, A.rows_to_frame

    def run_all(rows, out, cfg=None, causes=None, bootstrap=True, fidelity_rows=None, *, infra, overhead, inspection, audit=None, cause_flags=None, h3_table=None):
        acc = I.coerce(infra)
        keys = _capped_keys()
        cap = tuple(e for e in acc.exhausted if e["run_key"] in keys)
        rest = dataclasses.replace(acc, exhausted=tuple(e for e in acc.exhausted if e["run_key"] not in keys))
        kept, _ = I.exhausted_scope(dataclasses.replace(acc, exhausted=cap), cfg or cfgmod.load())
        kframe = I.exhausted_frame(kept)
        def r2f(rws, c, blocks=None, *a, **k):
            # EVERY frame built from the scored rows gets the K rows of the capped runs (their blocks permitting): the frozen analysis compares frames built from the same rows with each other (strict_beside refuses a frame
            # that is not the frame of its rows; the Sol-only and instrument-only sensitivities compare two frames of the same runs), so a K row in one and not in the other would break them
            df = orig_r2f(rws, c, blocks, *a, **k)
            if not len(kframe):
                return df
            allowed = set(blocks) if blocks is not None else set(c["blocks"]["primary"])
            extra = kframe[kframe["block"].isin(allowed)]
            return pd.concat([df, extra], ignore_index=True) if len(extra) else df
        A.rows_to_frame = r2f
        print(f"kaug_wrap: {len(cap)} capped-correction run(s) in the account, {len(kframe)} K row(s) added to the primary frame", file=sys.stderr, flush=True)
        try:
            return orig_run_all(rows, out, cfg, causes, bootstrap, fidelity_rows, infra=rest, overhead=overhead, inspection=inspection, audit=audit, cause_flags=cause_flags, h3_table=h3_table)
        finally:
            A.rows_to_frame = orig_r2f
    R.run_all = run_all


def _install_reuse() -> None:
    """TABLE-ONLY mode (KAUG_SRC_OUT=<a finished out/ of the SAME cut>): the pipeline stage of `snapshot analyse` is replaced by a copy of that out/'s pipeline/ (scored rows, causes, infra.json ... byte for byte, plain copies) and its
    merge/pipeline-cache records, so only the frozen analysis tables are computed again (minutes, not a fingerprint pass). The cut under --out was made by `snapshot cut` with the same arguments, so the two cuts are identical."""
    import shutil
    from snapshot import bmerge
    src = os.environ.get("KAUG_SRC_OUT")
    if not src:
        return
    src = os.path.abspath(src)

    def fake_assemble(cut_root, providers_path, providers, out, *, record_dir, jobs=1, worker_gib=8, max_planned_misses=None):
        shutil.copytree(os.path.join(src, "pipeline"), out, dirs_exist_ok=True, copy_function=shutil.copy2)      # a plain copy: the snapshot write guard checks both paths of a hard link and the source is outside --out
        os.makedirs(record_dir, exist_ok=True)
        for f in ("providers.json", "assemble.json"):
            shutil.copy2(os.path.join(src, "work", "merge", f), os.path.join(str(record_dir), f))
        manifest = json.load(open(os.path.join(src, "pipeline", "manifest.json")))
        pcache = json.load(open(os.path.join(src, "SNAPSHOT.json")))["pipeline_cache"]
        info = json.load(open(os.path.join(src, "work", "merge", "assemble.json")))
        print(f"kaug_wrap: table-only: pipeline/ reused from {src}", file=sys.stderr, flush=True)
        return {"manifest": manifest, "pcache": pcache, "merge": {"providers": info["providers"]}}
    bmerge.assemble_merged = fake_assemble


if __name__ == "__main__":
    _install()
    _install_reuse()
    sys.argv = ["snapshot"] + sys.argv[1:]
    runpy.run_module("snapshot", run_name="__main__", alter_sys=True)
