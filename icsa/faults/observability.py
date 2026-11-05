"""Observability of every fault type, per layout x option x record x condition, classed BEFORE any
run and written by hand from the #10 facts. Never derived from detector output.

Values:
- OBSERVABLE: the record's content, as documented, differs between a run with this fault and a
  fault-free one in a way the frozen detector reads. (Fidelity is still measured, not assumed.)
- UNOBSERVABLE: by design the record cannot show it (its granularity is coarser than the fault).
- NOT_APPLICABLE: the fault cannot occur or is not scripted for this cell (reason says why).
- UNKNOWN_UNTIL_LIVE: depends on behaviour not yet seen on a live system.
- PER_INSTANCE: the option's client serves some injected omissions whole and not others; each scripted run's
  verdict (masked = unobservable, else observable) is computed BEFORE it runs by `masking.py` and sealed into
  the claimed plan (science, #11, 21:54Z; amendment 12).

Amended 1 Nov 2026 (amendment 12) from the live check (`results/faults-live/`) under detector v2; every changed
cell carries a dated note (CHANGES, rendered at the end of OBSERVABILITY.md).

Facts used (day0/REPORT.md): the audit log is one line per fslogic request with NO offsets or
sizes; REST and proxy-I/O reads log `remote_read`, opens are logged in every mode; M runs in proxy
I/O. Traefik (if switched on with Range kept) sees path + Range + status; REST names files by ID.
The oneclient perf CSV has offset and size per client read, plus prefetch rows (ignored).
"""
from __future__ import annotations

import datetime as dt
import enum
import functools
import itertools
import json
from pathlib import Path
from typing import NamedTuple

from icsa.records import Layout, Option

from .records.base import Record
from .scenarios import Condition, Fault


class Obs(str, enum.Enum):
    OBSERVABLE = "observable"
    UNOBSERVABLE = "unobservable_by_design"
    NOT_APPLICABLE = "n/a"
    UNKNOWN_UNTIL_LIVE = "unknown_until_live"
    PER_INSTANCE = "observable_per_instance"


class Cell(NamedTuple):
    obs: Obs
    reason: str


OPTIONS = (Option.T, Option.D, Option.M)
LAYOUTS = (Layout.S1, Layout.S2)
FAULTS = [f for f in Fault if f is not Fault.NONE]
RECORDS_OF = {Option.T: (Record.AUDIT, Record.TRAEFIK), Option.D: (Record.AUDIT, Record.TRAEFIK),
              Option.M: (Record.AUDIT, Record.PERF)}
BYTE_LEVEL = (Record.TRAEFIK, Record.PERF)

# Faults of the "a file / time step is never touched" family, scripted per layout.
_SKIP_S1 = (Fault.WHOLE_FILE_SKIP, Fault.FILE_RANGE_SKIP)
_SKIP_S2 = (Fault.CHUNK_SKIP, Fault.CHUNK_RANGE_SKIP)
_PERIOD = (Fault.BASELINE_DROPPED, Fault.TARGET_DROPPED, Fault.WRONG_PERIOD)

_NA_LAYOUT = "scripted only for {}: {}"
_A12 = " [changed 2026-11-01, amendment 12]"
_T_READAHEAD = ("T's client (onedatarestfsspec, fsspec read-ahead, 5 MiB blocks, not settable) serves 5 MiB past each "
                "request: {} is served whole when it lies inside a fetched block; decided per scripted run before it runs "
                "(masking.py)" + _A12)

# Dated notes per changed cell (rendered at the end of OBSERVABILITY.md). Evidence: results/faults-live/.
CHANGES = [
    ("2026-11-01", "header_only / S1 / T / traefik", "observable -> unobservable_by_design",
     "live 21:20Z: a 15,241 B header read went out as Range bytes=0-173179, the whole file (T's 5 MiB read-ahead); "
     "the chunk is served whole under v1 and v2"),
    ("2026-11-01", "chunk_skip, chunk_range_skip, header_only / S2 / T / traefik", "observable -> observable_per_instance",
     "live 22:05Z: reading chunk 200 fetched it plus exactly 5 MiB, serving skipped chunk 201 whole; the model "
     "(masking.py; results/faults-live/model-readahead-20261101) decides each scripted run before it runs"),
    ("2026-11-01", "chunk_skip, chunk_range_skip / S2 / M / perf", "observable (reason only)",
     "live 22:06Z, default and prefetch_on: with chunk 201 skipped, the FsLogic rows reach 2,100 B into it (page rounding), "
     "never the whole chunk; v2 counts it as not read. Traefik's part of the old shared reason moved to the T cells"),
    ("2026-11-01", "header_only / S1, S2 / M / perf", "observable (reason only)",
     "v2: oneclient rounds a read up to whole 4 KiB pages from its offset (live 21:21Z: [0,16384) for 15,241 B), "
     "never the whole chunk; under v1 the 1,143 B overlap would have credited the day"),
    ("2026-11-01", "{whole_file_skip, file_range_skip, baseline_dropped, target_dropped, wrong_period} / S1 / M / audit "
     "/ {warm_buffer, prefetch_on}", "unknown_until_live -> observable (LIVE_CLASSES.json)",
     "warm_buffer equals cold on oneclient 25.0 (every open refetches; live 21:21Z); prefetch_on with the frozen "
     "flags --read-buffer-prefetch-duration 30 --read-buffer-max-size 1073741824 leaves the same lines as cold "
     "(live 22:04Z)"),
]
_D_SUBFILE = "D downloads whole files, so a sub-file fault does not arise; its blindness follows from the design (issue #11)"


def _cell(f: Fault, layout: Layout, opt: Option, rec: Record) -> Cell:
    O, U, N = Obs.OBSERVABLE, Obs.UNOBSERVABLE, Obs.NOT_APPLICABLE
    byte = rec in BYTE_LEVEL

    if f is Fault.NONE:
        return Cell(N, "fault-free control: no omission injected")
    if f in _SKIP_S1:
        if layout is Layout.S2:
            return Cell(N, _NA_LAYOUT.format("S1", "S2 has one file, so no whole file can be skipped"))
        return Cell(O, "a skipped file has no open/remote_read in the audit log" if not byte else
                    "a skipped file has no content request / no FsLogic read row")
    if f in _SKIP_S2:
        if layout is Layout.S1:
            return Cell(N, _NA_LAYOUT.format("S2", "S1 skips whole files instead"))
        if opt is Option.D:
            return Cell(N, _D_SUBFILE)
        if not byte:
            return Cell(U, "the single S2 file is opened and read either way; the audit log has no offsets or sizes")
        if opt is Option.T:
            return Cell(Obs.PER_INSTANCE, _T_READAHEAD.format("a skipped chunk"))
        return Cell(O, "offset+size (perf) show which chunks were read; page rounding never covers a skipped chunk whole" + _A12)
    if f in _PERIOD:
        if layout is Layout.S1:
            return Cell(O, "whole files of the dropped period are never touched")
        if opt is Option.D:
            return Cell(N, _D_SUBFILE)
        if not byte:
            return Cell(U, "dropped chunks of a file that is still opened: no offsets in the audit log")
        return Cell(O, "chunks of the dropped period are never requested (byte ranges visible)")
    if f is Fault.HEADER_ONLY:
        if opt is Option.D:
            return Cell(U, "D downloads the whole file when it touches it: the record shows a full download "
                           "whether or not the data is then used")
        if not byte:
            return Cell(U, "open + read logged, no sizes: a header read and a full read look the same")
        if opt is Option.T and layout is Layout.S1:
            return Cell(U, "T's client (onedatarestfsspec, 5 MiB read-ahead) fetches the whole S1 file for a header read: "
                           "the record shows a full read" + _A12)
        if opt is Option.T:
            return Cell(Obs.PER_INSTANCE, _T_READAHEAD.format("a header-only day"))
        return Cell(O, "oneclient reads whole 4 KiB pages from offset 0, never the whole chunk (detector v2)" + _A12)
    if f in (Fault.FULL_READ_PARTIAL_USE, Fault.WRONG_REGION):
        return Cell(U, "all bytes are fetched; what the analysis does with them is invisible to any platform record")
    if f is Fault.LISTING_TRUNCATION:
        if layout is Layout.S2:
            return Cell(N, _NA_LAYOUT.format("S1", "S2 has no directory of files to list"))
        if opt is Option.M:
            return Cell(N, "oneclient readdir of 15,340 entries is complete (day0 Q3), so M has no truncation to script")
        return Cell(O, "files past the first page are never touched" if not byte else
                    "files past the first page get no content request")
    raise ValueError(f)


LIVE_CLASSES = Path(__file__).with_name("LIVE_CLASSES.json")


class CalibrationNotReady(RuntimeError):
    """A cell is still unknown_until_live: no calibration may run (nothing is classed after seeing results)."""


def cell_key(f: Fault, layout: Layout, opt: Option, rec: Record, cond: Condition) -> str:
    return "|".join(x.value for x in (f, layout, opt, rec, cond))


@functools.lru_cache(maxsize=8)
def _load_live(path: str, mtime: float) -> dict[str, tuple[Obs, str]]:
    raw = json.loads(Path(path).read_text())
    out = {}
    for k, v in raw.get("classes", {}).items():
        c = Obs(v["class"])
        if c not in (Obs.OBSERVABLE, Obs.UNOBSERVABLE):
            raise ValueError(f"live class for {k} must be observable or unobservable_by_design")
        when = dt.datetime.fromisoformat(v["recorded_at"])
        if when.tzinfo is None:
            raise ValueError(f"live class for {k}: recorded_at needs a time zone")
        if when > dt.datetime.now(dt.timezone.utc):
            raise ValueError(f"live class for {k}: recorded_at {v['recorded_at']} is in the future")
        if not str(v.get("evidence", "")).strip():
            raise ValueError(f"live class for {k}: evidence required")
        out[k] = (c, f"live check {v['recorded_at']}: {v['evidence']}")
    return out


def live_classes(path: Path | None = None) -> dict[str, tuple[Obs, str]]:
    p = Path(path or LIVE_CLASSES)
    return _load_live(str(p), p.stat().st_mtime) if p.exists() else {}


def classify(f: Fault, layout: Layout, opt: Option, rec: Record, cond: Condition = Condition.COLD,
             live: dict | None = None) -> Cell:
    """The table. Conditions apply to M only (warm buffer, prefetch). A cell that is
    unknown_until_live takes its class from LIVE_CLASSES.json once the live check has recorded it;
    only unknown cells can be classed that way (a hand-classed cell is never overridden)."""
    c = _classify(f, layout, opt, rec, cond)
    if c.obs is Obs.UNKNOWN_UNTIL_LIVE:
        got = (live_classes() if live is None else live).get(cell_key(f, layout, opt, rec, cond))
        if got:
            return Cell(*got)
    return c


def check_committed(path: Path) -> None:
    """The live classes must be exactly what is committed: classed before the runs, not edited after."""
    import subprocess
    d = path.parent
    def git(*a):
        return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True)
    if git("ls-files", "--error-unmatch", path.name).returncode != 0:
        raise CalibrationNotReady(f"{path.name} is not tracked by git: commit the live classes before calibrating")
    if git("diff", "--quiet", "HEAD", "--", path.name).returncode != 0:
        raise CalibrationNotReady(f"{path.name} differs from the committed version: commit it before calibrating")


def assert_ready_for_calibration(live: dict | None = None, path: Path | None = None) -> None:
    if live is None:
        live = live_classes(path)
        if live:
            check_committed(Path(path or LIVE_CLASSES))
    unknown = [cell_key(*x[:5]) for x in all_cells(live) if x[5].obs is Obs.UNKNOWN_UNTIL_LIVE]
    if unknown:
        raise CalibrationNotReady(f"{len(unknown)} cell(s) still unknown_until_live; run the live audit-log check "
                                  f"and record them in LIVE_CLASSES.json first, e.g. {unknown[:2]}")


def _classify(f: Fault, layout: Layout, opt: Option, rec: Record, cond: Condition = Condition.COLD) -> Cell:
    if rec not in RECORDS_OF[opt]:
        return Cell(Obs.NOT_APPLICABLE, f"{rec.value} is not a record of option {opt.value}")
    if cond is not Condition.COLD and opt is not Option.M:
        return Cell(Obs.NOT_APPLICABLE, "cache conditions are scripted for M only")
    c = _cell(f, layout, opt, rec)
    if opt is Option.M and cond is not Condition.COLD and rec is Record.AUDIT and c.obs is Obs.OBSERVABLE:
        return Cell(Obs.UNKNOWN_UNTIL_LIVE,
                    f"{cond.value}: whether a client-cache-served read still leaves an open/remote_read "
                    f"in the audit log is unknown until the log is on; a miss would show as false 'missing'")
    return c


def all_cells(live: dict | None = None):
    for f, layout, opt in itertools.product(FAULTS, LAYOUTS, OPTIONS):
        for rec in RECORDS_OF[opt]:
            for cond in (Condition if opt is Option.M else [Condition.COLD]):
                yield f, layout, opt, rec, cond, classify(f, layout, opt, rec, cond, live)


def applicable_faults(layout: Layout, opt: Option) -> list[Fault]:
    """Faults scripted for this option x layout (applicable for at least one of its records)."""
    return [f for f in FAULTS
            if any(classify(f, layout, opt, r).obs is not Obs.NOT_APPLICABLE for r in RECORDS_OF[opt])]


def to_markdown() -> str:
    rows = ["# Observability by design (generated by `python -m icsa.faults.observability`)", "",
            "Classed before any run, from the #10 facts. Cache conditions only change the M audit cells. Amended "
            "1 Nov 2026 (amendment 12) from the live check under detector v2; the changes are listed at the end. "
            "Each option is calibrated against its own records' lines only (ATTRIBUTION.md).", "",
            "| fault | layout | option | record | condition | class | reason |", "|---|---|---|---|---|---|---|"]
    for f, layout, opt, rec, cond, c in all_cells():
        rows.append(f"| {f.value} | {layout.value} | {opt.value} | {rec.value} | {cond.value} | {c.obs.value} | {c.reason} |")
    rows += ["", "## Changes", "", "| date | cells | class | note |", "|---|---|---|---|"]
    rows += [f"| {d} | {cells} | {cls} | {note} |" for d, cells, cls, note in CHANGES]
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    print(to_markdown(), end="")
