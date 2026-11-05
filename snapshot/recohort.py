"""The cohort of a snapshot is the snapshot's own cut, not the launch's (#34, found 5 Nov by lane-prov78; the lead).

A dispatcher stamps `out_of_cohort` = 1 into a run directory when the run's counted first start is at or after the cohort cut of ITS launch (`scheduler.py:2193`), and the stamp reaches the
scored row through `record.out_of_cohort` (`scoring/scorer.py:139`); `analysis/adapter.py:85` then keeps such a run out of every contrast. A started store's cut cannot move, and every started B
store carries 15:50Z. A snapshot whose cut lies LATER than that (the final: cohort cut 6 Nov 00:50Z, amendment 43(a)) would silently drop every B run first started in between, although the
run is in the snapshot's cohort by the snapshot's own definition. `cut.py` re-stamps the store's meta (`cohort_cut_utc`, which `export._in_cohort` reads, so the infra account already follows
the cut) but cannot reach the run directories (they are never written). This closes the one place that still follows the launch: after the pipeline, before the analysis, every scored row's
`out_of_cohort` is recomputed with the SCHEDULER'S OWN RULE against THIS cut's `cohort_cut_utc` (stamped by `cut.py` into the cut's store as `t - cap + 1 s`): out iff the run's counted first
start (`Store.counted_starts`: the earliest of its first started attempt and its deferral; a retry never moves it) is at or after it.

On a cut that does not pass the launch's own cut it changes nothing (the stamp already says the same); that is the no-op checked at each earlier interim. The run directories and the pipeline's
own files are untouched; the rows are replaced in memory (and, for H3's measure, in the file `scored_coded.py` writes). `recohort.json` (in OUT/work) holds totals only, no option split.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import sqlite3
from pathlib import Path

from icsa.campaign.store import Store

from . import cut as cutmod


def cohort_cut(store_path) -> dt.datetime:
    """The cut's own `cohort_cut_utc` (meta), as `cut.apply_cut` stamped it. A store with none is not a cut: refused."""
    con = sqlite3.connect(f"file:{Path(store_path)}?mode=ro", uri=True)
    try:
        r = con.execute("SELECT value FROM meta WHERE key='cohort_cut_utc'").fetchone()
    finally:
        con.close()
    if r is None:
        raise cutmod.CutError(f"{store_path} has no cohort_cut_utc: it is not a snapshot's cut, so there is no cohort to recompute against")
    return cutmod.utc(r[0])


def apply(rows, store_path) -> tuple[list, dict]:
    """(the rows with `out_of_cohort` recomputed, totals). `rows` are `ScoredRow`s (anything with `.block`, `.run.key()`, `.out_of_cohort` that `dataclasses.replace` takes).
    A row whose run has no counted start in the store keeps its stamp and is counted (`no_counted_start`)."""
    cut = cohort_cut(store_path)
    store = Store(Path(store_path))
    try:
        starts = store.counted_starts()
    finally:
        store.close()
    out, to_in, to_out, same, nostart = [], 0, 0, 0, 0
    for r in rows:
        ts = starts.get(f"{r.block}__{r.run.key()}")
        if ts is None:
            nostart += 1
            out.append(r)
            continue
        new = cutmod.utc(ts) >= cut
        if new == bool(r.out_of_cohort):
            same += 1
            out.append(r)
        else:
            to_in += (not new)
            to_out += new
            out.append(dataclasses.replace(r, out_of_cohort=new))
    return out, {"rows": len(out), "cohort_cut_utc": cut.strftime("%Y-%m-%dT%H:%M:%SZ"), "stamp_out_to_in": to_in, "stamp_in_to_out": to_out, "unchanged": same,
                 "no_counted_start": nostart}


def write_info(info: dict, path) -> None:
    Path(path).write_text(json.dumps(info, indent=1, sort_keys=True))
