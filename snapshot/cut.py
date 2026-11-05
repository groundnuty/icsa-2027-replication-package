"""The cut: a copy of the campaign's store, reduced to what a snapshot at t covers. Reads the campaign's store; changes nothing in it."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from icsa.campaign.store import Store

STATUS_KEPT_IF = ("done", "infra_exhausted", "harness_error")


class CutError(ValueError):
    pass


def utc(ts: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)


def parse_t(text: str) -> dt.datetime:
    try:
        return utc(text)
    except ValueError as e:
        raise CutError(f"--t {text!r} is not an ISO UTC time") from e


def iso_z(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def check_final(final, t: str, no_outcome: str) -> None:
    """`--final true` only on the fixed cut: the same instant as FINAL_T (however it is spelled) with FINAL_NO_OUTCOME. `final` must be a real bool: the
    text "false" is truthy. Not final is never refused here (a rehearsal of the fixed cut included). `t` is the text of --t."""
    if not isinstance(final, bool):
        raise CutError(f"--final must be true or false, not {final!r}")
    if final and (parse_t(t) != FINAL_T or no_outcome != FINAL_NO_OUTCOME):
        raise CutError(f"--final true is only for the paper's fixed cut, --t {iso_z(FINAL_T)} with --no-outcome {FINAL_NO_OUTCOME} (amendment 29(c)); "
                       f"got --t {t} --no-outcome {no_outcome}")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def copy_store(src: Path, dest: Path) -> str:
    """A consistent copy of the store, made without writing anything beside it.
    Live store (its -wal or -shm exists, so a campaign holds it open): `VACUUM INTO` over a read-only connection. It reads in one transaction, so a
    writer is neither blocked nor seen half-way, and the files that exist already are all it touches.
    Quiescent store (neither exists): a read-only SQLite open would CREATE -wal and -shm beside it (found 3 Nov), so the file is copied as bytes, and
    if a -wal or -shm shows up meanwhile (a campaign started) the byte copy is thrown away and the live way is used.
    Returns the copy's sha256."""
    src, dest = Path(src), Path(dest)
    if not src.is_file():
        raise CutError(f"no campaign store at {src}")
    if dest.exists():
        raise CutError(f"{dest} exists: a cut is never overwritten")
    dest.parent.mkdir(parents=True, exist_ok=True)
    side = [src.with_name(src.name + sfx) for sfx in ("-wal", "-shm")]
    if not any(p.exists() for p in side):
        shutil.copyfile(src, dest)
        if not any(p.exists() for p in side):
            return sha256_file(dest)
        dest.unlink()
    con = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=30)
    try:
        con.execute("VACUUM INTO '" + str(dest).replace("'", "''") + "'")
    finally:
        con.close()
    return sha256_file(dest)


NO_OUTCOME = ("report", "as-exhausted")
# Amendment 29(c): the paper's confirmatory analysis is ONE fixed snapshot. Holm decisions and smallest-effect verdicts are read only from it, and
# `--final true` is accepted for nothing else. These two values are the only place that says what it is.
FINAL_T = dt.datetime(2026, 11, 6, 9, 0, tzinfo=dt.timezone.utc)     # amendment 43(a): 6 Nov 09:00Z (was 29(c)'s 00:00Z)
FINAL_NO_OUTCOME = "as-exhausted"
NOTE_KEY = "snapshot_no_outcome_runs"      # read by campaign.export.export_infra: the converted runs, told apart per cell


def apply_cut(path: Path, t: dt.datetime, cap_s: float, now: dt.datetime | None = None, no_outcome: str = "report") -> dict:
    """Reduce the COPY at `path` to the snapshot at `t`: keep the runs whose counted start is <= t - cap_s, and their attempts as they stood at t
    (an attempt that ended after t, or was still running, is dropped, and the run's status is rebuilt from what remains). Returns counts only.
    Refuses a `t` in the future: the attempts after the copy are not there yet."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if no_outcome not in NO_OUTCOME:
        raise CutError(f"--no-outcome must be one of {NO_OUTCOME}")
    if t > now:
        raise CutError(f"--t {t.isoformat()} is after now ({now.isoformat()}): the store cannot show what ended by then")
    if cap_s <= 0:
        raise CutError("--cap-s must be positive")
    limit = t - dt.timedelta(seconds=cap_s)
    store = Store(Path(path))
    try:
        starts = store.counted_starts()
        keep = {k for k, ts in starts.items() if utc(ts) <= limit}
        all_runs = store.q("SELECT run_key, status FROM runs")
        t_iso = iso_z(t)

        converted: list[str] = []

        def go():
            db = store.db
            infra_before = {r["run_key"]: r["n"] for r in db.execute("SELECT run_key, COUNT(*) n FROM attempts WHERE state='infra_fail' GROUP BY run_key")}
            for r in all_runs:
                if r["run_key"] not in keep:
                    db.execute("DELETE FROM attempts WHERE run_key=?", (r["run_key"],))
                    db.execute("DELETE FROM runs WHERE run_key=?", (r["run_key"],))
            # as of t: an attempt that had not ended by t was in flight. It stays as a 'running' row with nothing of what it ended with (its start is what
            # makes the run a cohort member, and export reads it from the attempt), and the run's status is rebuilt from the attempts that had ended
            late = [a["id"] for a in db.execute("SELECT id, ended_utc, state FROM attempts").fetchall()
                    if a["state"] == "running" or not a["ended_utc"] or utc(a["ended_utc"]) > t]
            late_set = set(late)
            for r in all_runs:
                k = r["run_key"]
                if k not in keep:
                    continue
                rows_k = db.execute("SELECT id, state FROM attempts WHERE run_key=?", (k,)).fetchall()
                left = {x["state"] for x in rows_k if x["id"] not in late_set}
                n_infra = sum(1 for x in rows_k if x["id"] not in late_set and x["state"] == "infra_fail")
                st = r["status"]
                if st == "done" and "done" not in left:
                    st = "pending"
                elif st == "infra_exhausted" and n_infra != infra_before.get(k, 0):
                    st = "pending"
                elif st == "harness_error" and "harness_error" not in left:
                    st = "pending"
                db.execute("UPDATE runs SET status=? WHERE run_key=?", (st, k))
            for i in late:
                db.execute("UPDATE attempts SET state='running', ended_utc=NULL, wall_s=NULL, input_tokens=0, output_tokens=0, cache_creation_tokens=0,"
                           " cache_read_tokens=0, bytes_into_context=0, bytes_moved=NULL, termination=NULL, infra_kind=NULL, infra_detail=NULL WHERE id=?", (i,))
            if no_outcome == "as-exhausted":      # amendment 29(c): a cohort run with no outcome at t counts as an exhausted run; the list lets the tables tell them apart
                converted.extend(sorted(x[0] for x in db.execute("SELECT run_key FROM runs WHERE status IN ('pending','harness_error')")))
                db.execute("UPDATE runs SET status='infra_exhausted' WHERE status IN ('pending','harness_error')")
                db.execute("INSERT INTO meta(key,value,set_utc) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, set_utc=excluded.set_utc",
                           (NOTE_KEY, json.dumps(converted), t_iso))
            # the cohort the analysis reads (export._in_cohort: began BEFORE the stamp) is this cut's: started by t - cap, one second added for "by"
            db.execute("INSERT INTO meta(key,value,set_utc) VALUES('cohort_cut_utc',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, set_utc=excluded.set_utc",
                       ((limit + dt.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), t_iso))
            # the tables the snapshot's readers must not take from the live campaign
            db.execute("DELETE FROM events")
            db.execute("DELETE FROM endpoint_windows")
        store._tx(go)
        counts = {s: n for s, n in ((x["status"], x["n"]) for x in store.q("SELECT status, COUNT(*) n FROM runs GROUP BY status"))}
        run_dirs = sorted({r["run_dir"] for r in store.q(
            "SELECT a.run_dir FROM attempts a JOIN runs r USING(run_key) WHERE r.status='done' AND a.state='done' AND a.run_dir IS NOT NULL")})
        planned = len(all_runs)
    finally:
        store.close()
    return {"t": t_iso, "cap_s": cap_s, "last_start_included": limit.strftime("%Y-%m-%dT%H:%M:%SZ"), "runs_in_cut": len(keep),
            "done": counts.get("done", 0), "infra_exhausted": counts.get("infra_exhausted", 0),
            "unfinished": counts.get("pending", 0) + counts.get("harness_error", 0),
            "planned_runs": planned, "no_outcome": no_outcome, "no_outcome_as_exhausted": len(converted), "runs_started_later_or_never": planned - len(keep), "run_dirs": run_dirs}


def make_cut(campaign_root: Path, work: Path, t: dt.datetime, cap_s: float, now: dt.datetime | None = None, no_outcome: str = "report") -> dict:
    """`work/cut/state.sqlite` (the reduced copy), `run_dirs.txt` (the done runs' directories, for the rsync) and `cut.json`."""
    cut = Path(work) / "cut"
    sha = copy_store(Path(campaign_root) / "state.sqlite", cut / "state.sqlite")
    info = apply_cut(cut / "state.sqlite", t, cap_s, now, no_outcome)
    dirs = info.pop("run_dirs")
    (cut / "run_dirs.txt").write_text("".join(d + "\n" for d in dirs))
    info.update(store_copy_sha256=sha, copied_at=(now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                reduced_store_sha256=sha256_file(cut / "state.sqlite"))
    (cut / "cut.json").write_text(json.dumps(info, indent=1, sort_keys=True))
    return info
