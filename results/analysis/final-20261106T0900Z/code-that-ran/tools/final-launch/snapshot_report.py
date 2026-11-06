"""The report line set an interim snapshot hands to the lead (#34, amendment 43): the sealed path, the stage timings, and WHOLE-RUN counts only.

    python snapshot_report.py <seal dir>        # writes <seal>/report.txt (0600) and prints it

Counts, never a figure by option or by cell: runs in the cut per provider (main = site_g), the cut's done / unfinished / exhausted, scored and failed from the pipeline, each provider's cache hits
and misses, and the H3 join account (scored rows, platform rows, runs without a platform row, platform rows without a scored row, attempt mismatches). Reads only the snapshot's own logs and
counts (cut.json, snapshot.log, assemble.json, the measure's stdout `join` block, stages.jsonl) and the cut's store for the owner of each run (a run key is read to count it, never printed).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path


def main(seal: Path) -> int:
    out = []
    t = None
    stages = [json.loads(l) for l in (seal / "stages.jsonl").read_text().splitlines() if l.strip()] if (seal / "stages.jsonl").is_file() else []
    notes = {r["note"]: r["value"] for r in stages if "note" in r}
    cutp = seal / "out" / "work" / "cut" / "cut.json"
    cut = json.loads(cutp.read_text()) if cutp.is_file() else {}
    t = cut.get("t", seal.name)
    out.append(f"sealed dir: {seal}")
    snap = {}
    try:
        snap = json.loads((seal / "out" / "SNAPSHOT.json").read_text())
    except (OSError, ValueError):
        pass
    out.append(f"t={cut.get('t')} cut(last start included)={cut.get('last_start_included')} cap_s={cut.get('cap_s')} no_outcome={cut.get('no_outcome')} final={str(snap.get('final', False)).lower()}"
               + (f" cohort_cut_explicit={cut.get('cohort_cut_explicit')}" if cut.get("cohort_cut_explicit") else ""))
    # which table sets are the PRIMARY ones (science #34 03:30Z): PRIMARY.json when written, else the directories as they stand (the partial report is written before it)
    prim = None
    try:
        prim = json.loads((seal / "PRIMARY.json").read_text())
    except (OSError, ValueError):
        pass
    def _done(d: str) -> bool:
        return (seal / d / "tables" / "manifest.json").is_file()
    if prim:
        out.append(f"PRIMARY TABLES: {prim.get('primary_tables')}/ (coded: {prim.get('primary_coded_tables')}/); the frozen analysis beside: {prim['frozen_beside'].get('tables')}/ ({prim['frozen_beside'].get('coded_tables')}/); "
                   f"runs counted as K: {prim['k_augmented'].get('capped_runs_applied')} {prim['k_augmented'].get('capped_runs_by_option')} (by the rule: {prim['k_augmented'].get('runs_applying_by_rule')}; unscorable here, memory: {prim['k_augmented'].get('unscorable_memory_runs')}), correction sha256 {str(prim['k_augmented'].get('correction_file_sha256'))[:16]}")
        if prim['k_augmented'].get('table_note'):
            out.append("K-AUG TABLE NOTE: " + prim['k_augmented']['table_note'])
    else:
        out.append("PRIMARY TABLES (PRIMARY.json not written yet): " + ("out-kaug/" if _done("out-kaug") else "out/") + (" (coded: out-coded-kaug/)" if _done("out-coded-kaug") else ""))
    if cut:
        out.append(f"cut: runs_in_cut={cut['runs_in_cut']} done={cut['done']} unfinished={cut['unfinished']} exhausted={cut['infra_exhausted']} "
                   f"no_outcome_as_exhausted={cut['no_outcome_as_exhausted']} planned_runs={cut['planned_runs']}")
    # runs in the cut per provider: the cut's store lists the runs, the merge's providers.json says who owns each
    prov_p, store_p = seal / "M" / "providers.json", seal / "out" / "work" / "cut" / "state.sqlite"
    if prov_p.is_file() and store_p.is_file():
        owner = json.loads(prov_p.read_text())["providers"]
        c = sqlite3.connect(f"file:{store_p}?mode=ro", uri=True)
        try:
            keys = [r[0] for r in c.execute("SELECT run_key FROM runs")]
        finally:
            c.close()
        per: dict[str, int] = {}
        for k in keys:
            per[owner.get(k, "?")] = per.get(owner.get(k, "?"), 0) + 1
        out.append("runs in cut per provider: " + " ".join(f"{p}={n}" for p, n in sorted(per.items())))
    log = seal / "out" / "snapshot.log"
    if log.is_file():
        txt = log.read_text()
        m = re.search(r"pipeline: scored=(\d+) failed=(\d+)", txt)
        if m:
            out.append(f"pipeline: scored={m.group(1)} failed={m.group(2)}")
        m = re.search(r"analysis: rows=(\d+) files=(\d+)", txt)
        if m:
            out.append(f"analysis: rows={m.group(1)} files={m.group(2)}")
    logc = seal / "out-coded" / "snapshot.log"
    if logc.is_file():
        txt = logc.read_text()
        m = re.search(r"pipeline: scored=(\d+) failed=(\d+)", txt)
        m2 = re.search(r"analysis: rows=(\d+) files=(\d+)", txt)
        out.append("analysis with the coding decisions (out-coded/): " + (f"scored={m.group(1)} failed={m.group(2)} " if m else "") + (f"rows={m2.group(1)} files={m2.group(2)}" if m2 else "NOT COMPLETE"))
    lab = seal / "frozen" / "inspection-labels.jsonl"
    if lab.is_file():
        out.append(f"coding decisions applied: label records={sum(1 for l in lab.read_text().splitlines() if l.strip())}")
        fo = seal / "inspection" / "filter.out"
        if fo.is_file():
            out.append("labels outside this cut (left out): " + (re.search(r"dropped_not_in_cut=(\d+)", fo.read_text()) or [None, "?"])[1])
    if notes.get("unmirrored_dispatchers"):
        out.append("WARNING launch files with NO mirror (a started dispatcher among them has runs in no snapshot): " + " ".join(notes["unmirrored_dispatchers"]))
    mj = seal / "M" / "merge.json"
    if mj.is_file():          # science, #34 09:12Z: the duplicates per option (a duplicate is settled by the earliest start, never by an outcome), with the total
        try:
            m_ = json.loads(mj.read_text())
            out.append(f"merge duplicates: total={m_.get('duplicates')} by option: " + " ".join(f"{o}={c}" for o, c in sorted((m_.get("duplicates_by_option") or {}).items())))
        except Exception:       # noqa: BLE001
            out.append("merge duplicates: unreadable")
    if "assemble_counts" in notes:
        out.append("cache per provider: " + " ".join(f"{p}:hits={v.get('planned_hits')}/{v.get('analysed')},misses={v.get('planned_misses')}" for p, v in sorted(notes["assemble_counts"].items())))
    mo = seal / "h3" / "measure.out"
    if mo.is_file():
        m = re.search(r'"join": (\{[^}]*\})', mo.read_text())
        if m:
            j = json.loads(m.group(1))
            out.append("H3 join: " + " ".join(f"{k}={v}" for k, v in sorted(j.items())))
    jn = seal / "h3" / "join.out"
    if jn.is_file():
        out.append("H3 platform rows joined: " + (jn.read_text().strip().splitlines() or ["?"])[-1][:300])
    # how current each extract store's records are against t: its platform_rows.jsonl is rewritten whole at the end of every extract pass of that store
    if cut:
        import datetime as dt
        ts = dt.datetime.fromisoformat(cut["t"].replace("Z", "+00:00")).timestamp()
        ages = {}
        for n in ["site_g"] + sorted(d.name for d in (seal / "frozen").iterdir() if d.is_dir() and d.name != "main" and (d / "fetch.json").is_file()):     # the stores only (not daytruth/, kernel-hung/)
            f = Path("/mnt/volume2/icsa-2027/snap-h3") / n / "platform_rows.jsonl"
            ages[n] = f"{int(f.stat().st_mtime - ts):+d}" if f.is_file() else "none"
        out.append("H3 extract store last completed pass vs t (s): " + " ".join(f"{n}={a}" for n, a in ages.items()))
    if notes.get("layout_bypass"):
        out.append(f"BYPASS: it happened (see {seal}/layout/bypass.csv)")
    mu = seal / "h3" / "mon_used.json"
    if mu.is_file():
        try:
            m = json.loads(mu.read_text())
            hel = {k: v for k, v in m.items() if k.startswith("icsa-site_a-")}
            if hel:
                used = sorted({v.get("mon_file") for v in hel.values()})
                out.append(f"HPC monitor source: {', '.join(str(u) for u in used)}; leases resting on the derived first line: "
                           f"{sum(int(v.get('leases_resting_on_derived_line') or 0) for v in hel.values())} of {sum(int(v.get('leases') or 0) for v in hel.values())} "
                           f"({len(hel)} providers)")
        except Exception:       # noqa: BLE001
            out.append("HPC monitor source: unreadable")
    st = [r for r in stages if "stage" in r]
    out.append("stage seconds: " + " ".join(f"{r['stage']}={r['seconds']}(rc{r['rc']})" for r in st))
    usub = notes.get("unseal_substages") or []
    if usub:
        out.append("unseal sub-stages: " + " ".join(f"{r['substage']}={r.get('seconds')}(rc{r.get('rc')})" for r in usub))
    lsub = notes.get("layout_substages") or []
    if lsub:
        out.append("layout sub-stages: " + " ".join(f"{r['substage']}={r.get('seconds')}(rc{r.get('rc')})" for r in lsub))
    sub = notes.get("h3_substages") or []
    if sub:
        out.append("h3 sub-stages: " + " ".join(f"{r['substage']}={r.get('seconds', 'skipped')}" + (f"(rc{r['rc']})" if 'rc' in r else "") for r in sub))
    if "mirrors_freshness" in notes:
        out.append("store copies after t (s): " + " ".join(f"{n}={v['store_copied_after_t_s']}" for n, v in sorted(notes["mirrors_freshness"].items())))
    tj = seal / "timings.json"
    if tj.is_file():
        tt = json.loads(tj.read_text())
        out.append(f"total_s={tt['total_s']} under_1h={tt['total_s'] < 3600} exit={tt['exit']}" + ("" if tt["exit"] == 0 else " (NOT A CLEAN SNAPSHOT: 6 = a mirror or main's extract inputs not fresh at t, 7 = the H3 stage did not run clean, 8 = no coding decisions in this snapshot)"))
    text = "\n".join(out) + "\n"
    fd = os.open(seal / "report.txt", os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
