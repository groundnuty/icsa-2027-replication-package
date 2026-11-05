"""Each attempt's provider and the concurrency level in force when it STARTED, for a snapshot's sealed path (lane-snap, #34; science 5 Nov 11:33Z: tables can then read M by level).

    python run_level.py <seal dir>        -> <seal>/run_level.csv (mode 600); stdout: totals only

One row per attempt of every run in the cut (out/work/cut/state.sqlite, started attempts only): run_key, provider (the store that won the run in the merge, M/providers.json), attempt, started_utc,
option, layout, steps (the step in force, 0 = the top of the ladder), steps_of (the ladder's length minus one), cap_main_s1, cap_main_s2_a, cap_global (the caps in force) and level_at_start (the cap that
applies to the run: main_s1 for layout S1, main_s2_a for S2, else global). They come from the owner store's `level_changed` events (`step A -> B of N` and `caps now {...}`, which the dispatcher writes at
every change, the launch's own start included): the last event with a timestamp at or before the attempt's start. An attempt that started before its store's first event has empty fields (the level was not
yet recorded), counted. Reads only the frozen copies of the stores in the seal; writes only the CSV.
"""
from __future__ import annotations

import ast
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

STEP = re.compile(r"step (\d+) -> (\d+)(?: of (\d+))?")
CAPS = re.compile(r"caps now (\{[^}]*\})")


def events(path: Path) -> list[tuple[str, int | None, int | None, dict]]:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = db.execute("select ts, detail from events where kind='level_changed' order by id").fetchall()
    finally:
        db.close()
    out = []
    for ts, d in rows:
        m, c = STEP.search(d or ""), CAPS.search(d or "")
        caps = {}
        if c:
            try:
                caps = ast.literal_eval(c.group(1))
            except (ValueError, SyntaxError):
                caps = {}
        out.append((ts, int(m.group(2)) if m else None, int(m.group(3)) if m and m.group(3) else None, caps))
    out.sort(key=lambda r: r[0])
    return out


def main(argv=None) -> int:
    seal = Path((argv or sys.argv[1:])[0])
    cut = seal / "out" / "work" / "cut" / "state.sqlite"
    prov = json.loads((seal / "M" / "providers.json").read_text())
    owner_of, main_name = prov["providers"], prov["main"]
    db = sqlite3.connect(f"file:{cut}?mode=ro", uri=True)
    try:
        rows = db.execute("select r.run_key, r.option, r.layout, a.attempt, a.started_utc from attempts a join runs r on r.run_key = a.run_key "
                          "where a.started_utc is not null order by r.run_key, a.attempt").fetchall()
    finally:
        db.close()
    ev: dict[str, list] = {}
    n = missing = no_store = 0
    by_provider: dict[str, int] = {}
    out = seal / "run_level.csv"
    tmp = out.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_key", "provider", "attempt", "started_utc", "option", "layout", "steps", "steps_of", "cap_main_s1", "cap_main_s2_a", "cap_global", "level_at_start"])
        for rk, opt, lay, att, st in rows:
            p = owner_of.get(rk)
            if p is None:
                no_store += 1
                continue
            store = seal / "frozen" / ("main" if p == main_name else p) / "state.sqlite"
            if p not in ev:
                ev[p] = events(store) if store.is_file() else []
            last = None
            for e in ev[p]:
                if e[0] <= st:
                    last = e
                else:
                    break
            by_provider[p] = by_provider.get(p, 0) + 1
            n += 1
            if last is None:
                missing += 1
                w.writerow([rk, p, att, st, opt, lay, "", "", "", "", "", ""])
                continue
            caps = last[3]
            lvl = caps.get("main_s1") if lay == "S1" else caps.get("main_s2_a") if lay == "S2" else caps.get("global")
            if lvl is None:
                lvl = caps.get("global")
            w.writerow([rk, p, att, st, opt, lay, last[1] if last[1] is not None else "", last[2] if last[2] is not None else "", caps.get("main_s1", ""),
                        caps.get("main_s2_a", ""), caps.get("global", "") if caps.get("global") is not None else "", lvl if lvl is not None else ""])
    tmp.chmod(0o600)
    tmp.replace(out)
    print(f"run_level rows={n} providers={len(by_provider)} before_first_level_event={missing} no_owner={no_store} file=run_level.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
