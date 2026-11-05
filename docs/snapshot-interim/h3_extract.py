"""`python -m icsa.faults.mainaudit extract`, skipping an attempt whose perf CSV is too big for the memory cap (lane-snap, #34; the lead, 4 Nov 19:5xZ).

    cd <main's tree> && PYTHONPATH=. python docs/snapshot-interim/h3_extract.py extract --store DIR --mirror M ... (the same arguments)

The switched-on phase holds about 10x the largest perf CSV of an attempt (558 MB -> 5.9 GB). Under a 12 GiB memcap an attempt with a perf CSV over H3_PERF_CSV_MAX_GIB (1.1) would get
the whole extract killed, so those attempts, and every other attempt of their runs, are left out of the list `extract()` is given, and counted on stderr (`skipped_perf_csv_over_limit=N runs_skipped=M`). The cap is not raised. The attempts that
every option contributes to the orphan calculation (`every`, inside run_extract) are untouched; only the target list passed to `extract` is filtered, so a skipped attempt has no
platform row and the measure counts its run as `no_platform_row`. Glue only: the frozen extract, its checks and its outputs are the merged code.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
LIMIT = int(float(os.environ.get("H3_PERF_CSV_MAX_GIB", "1.1")) * 2 ** 30)

from icsa.faults.mainaudit import extract as EX   # noqa: E402

_orig = EX.extract


def extract(store, attempts, *a, **k):
    from icsa.faults.mainaudit import windows as W
    big = {W.run_key_of(rec) for d, rec in attempts
           if any(f.stat().st_size > LIMIT for f in (Path(d) / "oneclient_perf").glob("read_write_perf-*.csv"))}
    # the whole RUN goes, not only the oversized attempt: the join takes a run's numerically latest attempt among those it is given, so dropping only the latest
    # would certify an earlier attempt's evidence for the run; with the run out, the measure counts it as no_platform_row
    keep = [(d, rec) for d, rec in attempts if W.run_key_of(rec) not in big]
    print(f"h3_extract: attempts={len(attempts)} skipped_perf_csv_over_limit={len(attempts) - len(keep)} runs_skipped={len(big)} limit_bytes={LIMIT}", file=sys.stderr, flush=True)
    return _orig(store, keep, *a, **k)


_orig_summary = EX._summary_and_join


def _summary_with_exclusions(store, attempts, host_of):
    """Between the records and the platform-rows summary: the data-driven exclusion list (snapshot/h3exclusions.py; science 5 Nov 02:50Z) marks the audit records of leases that a foreign actor
    shared a slot user with, so the summary (and the measure after it) read them as not_observed:foreign_lines. Counts by reason go to the log, never a run key."""
    from snapshot import h3exclusions
    counts = h3exclusions.apply(store, attempts, Path(store).name)
    print(f"h3_extract: exclusions applied by reason={counts}", file=sys.stderr, flush=True)
    return _orig_summary(store, attempts, host_of)


EX._summary_and_join = _summary_with_exclusions
EX.extract = extract

if __name__ == "__main__":
    from icsa.faults.mainaudit.__main__ import main
    raise SystemExit(main(sys.argv[1:]))
