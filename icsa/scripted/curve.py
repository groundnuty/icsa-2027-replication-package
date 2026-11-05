"""The concurrency cap rule (science, #12, 19:58Z; `protocol/parameters.md`), evaluated on run records.

The cap, per block (science's amendment on #12, 1 Nov 17:30Z, before any curve data): the highest level at which EVERY cell
of that block, run as that block's mix, keeps >= 80% of its single-run throughput (<= 1.25 x single-run wall time), with no
errors, no OOM kill and within disk limits. The curve runs traced (#9). A run is compared with the single-run time of ITS OWN instance.
Two readings of "keeps" are reported: `max_ratio` (every run within 1.25x, the rule as applied here, so that a starved
run is not averaged away) and `median_ratio`. Pure functions, except where a file is read (`load_host_ratios`, `find_host_ratios`).

The host in the reference (science, #34): a curve over two hosts judges every run against the single-run times of ONE host (the baselines' host, the
reference host). A host whose unloaded runs differ per cell from that host's has its own reference: the reference host's value times a per-cell ratio
(wall and read phase apart), from a file (`load_host_ratios`). No other rule changes: the limits, the shares, the cycles and the decisions are the same
for every option and host. Without the file every function here behaves, and hashes, exactly as before.

The duty-cycle form's verdict is on the MEDIANS (science, #34, 11:50Z, amendment 25(b)): see `level_table`. The registered form's stays on the maxima.
"""
from __future__ import annotations

import math
import statistics
from typing import Iterable

WALL_RATIO_LIMIT = 1.25
READ_RATIO_LIMIT = 1.25     # the second pass condition (science, #2, 3 Nov 09:17Z): both must pass, per cell at each level
HOST_RATIOS_FORMAT = "icsa-host-reference-ratios-v1"
HOST_RATIOS_COPY = "host_reference_ratios.json"       # the copy `curve-multi` keeps in its --out, which the report reads
DUTY_MEDIAN_RULE = "duty-median"                       # the `rule` of a duty-cycle row of `level_table` (the dossier's cap rule reads it from the exported point)


def required_containers(option: str) -> set[str]:
    return {"agent", "gate", "sidecar"} if option in ("M", "M+") else {"agent", "gate"}


def clean(r: dict) -> bool:
    """The one test of a run the cap may rest on: it finished clean, and the OOM counter of every container that option
    has is known to be zero. A record with an unknown or absent counter is not clean, whatever its `ok` says."""
    ooms = r.get("oom_kills") or {}
    return (r.get("ok") is True and required_containers(r.get("option", "")) <= set(ooms)
            and all(v == 0 for v in ooms.values()))


def counted(rows: Iterable[dict]) -> list[dict]:
    """A mix keeps its level full with padding runs until every slot's counted runs have finished: those saw a falling
    concurrency at their end, or were cancelled, and enter no statistic."""
    return [r for r in rows if not r["extra"].get("padding")]


def single_run_walls(rows: Iterable[dict]) -> dict[tuple[str, str, str], float]:
    """(option, layout, instance) -> median wall time of its single runs that finished clean."""
    walls: dict[tuple[str, str, str], list[float]] = {}
    for r in rows:
        if clean(r):
            walls.setdefault((r["option"], r["layout"], r["instance_id"]), []).append(r["wall_s"])
    return {k: statistics.median(v) for k, v in walls.items()}


def read_phase_s(r: dict) -> float | None:
    """The run's read phase from `script.stamps_s`: `read_done - first_compute`, plus for D the download (`opened - listing_done`, where the
    layout has an `opened` stamp: S2). None when a stamp that applies is missing or not a number: a missing stamp does not pass."""
    st = (r.get("script") or {}).get("stamps_s")
    if not isinstance(st, dict):
        return None
    need = ["read_done", "first_compute"]
    if r.get("option") == "D" and r.get("layout") == "S2":
        need += ["opened", "listing_done"]
    vals = {k: st.get(k) for k in need}
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v != v for v in vals.values()):
        return None
    v = vals["read_done"] - vals["first_compute"]
    if "opened" in vals:
        v += vals["opened"] - vals["listing_done"]
    return v if v >= 0 else None


def single_read_phases(rows: Iterable[dict]) -> dict[tuple[str, str, str], float]:
    """(option, layout, instance) -> median read phase of its single runs that finished clean and carry the stamps."""
    got: dict[tuple[str, str, str], list[float]] = {}
    for r in rows:
        v = read_phase_s(r) if clean(r) else None
        if v is not None:
            got.setdefault((r["option"], r["layout"], r["instance_id"]), []).append(v)
    return {k: statistics.median(v) for k, v in got.items()}


def _ratio_value(v, where: str) -> float:
    """A ratio from the file: a number (not a bool), finite, above 0. A value below 1 is valid: the other host may be the faster one."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{where}: {v!r} is not a finite number above 0")
    try:
        f = float(v)
    except OverflowError:
        raise ValueError(f"{where}: {v!r} is not a finite number above 0") from None
    if f != f or f in (float("inf"), float("-inf")) or f <= 0:
        raise ValueError(f"{where}: {v!r} is not a finite number above 0")
    return f


def load_host_ratios(path, *, hosts: Iterable[str] | None = None, cells: Iterable[tuple[str, str]] = ()) -> dict:
    """The per-host, per-cell reference ratios (format `HOST_RATIOS_FORMAT`): {"path", "sha256" (of the file's bytes), "source", "reference_host",
    "ratios": {host: {(option, layout): {"wall", "read"}}}}. A host's reference is the reference host's baseline times its ratio, the wall and the
    read phase each by its own: `run_reference`.

    The file is `{"format", "reference_host", "source", "hosts": {host: {"<option>/<layout>": {"wall": x, "read": y}}}}`; another top-level key is
    allowed and hashed with the file. ValueError, naming the problem, for a file that cannot be read or parsed, a wrong format, no `source` or
    `reference_host`, no host, the reference host among the hosts, a cell key that is not `option/layout`, a cell without its `wall` or its `read` (the
    read is never taken from the wall, and nothing defaults to 1.0), or a value that is not a finite number above 0. With `hosts` (the run's hosts),
    the reference host must be one of them and the file's hosts exactly the others; with `cells`, every host of the file has every one of them (cells
    beyond them are allowed, one file serves both blocks)."""
    import hashlib
    import json
    from pathlib import Path
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as e:
        raise ValueError(f"{p} cannot be read: {e}") from None
    try:
        d = json.loads(raw)
    except ValueError as e:
        raise ValueError(f"{p} is not valid JSON: {e}") from None
    if not isinstance(d, dict):
        raise ValueError(f"{p}: the top level is not an object")
    if d.get("format") != HOST_RATIOS_FORMAT:
        raise ValueError(f"{p}: format {d.get('format')!r} is not {HOST_RATIOS_FORMAT!r}")
    src, ref = d.get("source"), d.get("reference_host")
    if not isinstance(src, str) or not src.strip():
        raise ValueError(f"{p}: source is missing or not a non-empty string (where the ratios come from)")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(f"{p}: reference_host is missing or not a non-empty string")
    blocks = d.get("hosts")
    if not isinstance(blocks, dict) or not blocks:
        raise ValueError(f"{p}: hosts is missing, not an object, or empty")
    if ref in blocks:
        raise ValueError(f"{p}: the reference_host {ref!r} appears inside hosts: it is the reference, it has no ratios")
    ratios: dict[str, dict[tuple[str, str], dict[str, float]]] = {}
    for host, block in blocks.items():
        if not isinstance(block, dict):
            raise ValueError(f"{p}: host {host!r} is not an object of cells")
        ratios[host] = {}
        for key, entry in block.items():
            parts = key.split("/")
            if len(parts) != 2 or not all(parts):
                raise ValueError(f"{p}: host {host!r}: cell key {key!r} is not of the form 'option/layout'")
            if not isinstance(entry, dict):
                raise ValueError(f"{p}: host {host!r} cell {key!r} is not an object with 'wall' and 'read'")
            got = {}
            for field in ("wall", "read"):
                if field not in entry:
                    raise ValueError(f"{p}: host {host!r} cell {key!r} lacks '{field}' (the read is never taken from the wall, nothing defaults to 1.0)")
                got[field] = _ratio_value(entry[field], f"{p}: host {host!r} cell {key!r} {field}")
            ratios[host][(parts[0], parts[1])] = got
    if hosts is not None:
        names = set(hosts)
        if ref not in names:
            raise ValueError(f"{p}: reference_host {ref!r} is not one of the run's hosts {sorted(names)}")
        want, have = names - {ref}, set(ratios)
        if want != have:
            raise ValueError(f"{p}: the file's hosts {sorted(have)} are not the run's hosts other than the reference {ref!r}, {sorted(want)}: "
                             f"missing {sorted(want - have)}, not in the run {sorted(have - want)}")
    need = [(o, la) for o, la in cells]
    for host, have_cells in ratios.items():
        gone = [f"{o}/{la}" for o, la in need if (o, la) not in have_cells]
        if gone:
            raise ValueError(f"{p}: host {host!r} has no ratio for the cell(s) {gone}")
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "source": src, "reference_host": ref, "ratios": ratios}


def run_reference(single: dict[tuple[str, str, str], float], single_read: dict[tuple[str, str, str], float] | None, r: dict,
                  host_ratios: dict | None = None) -> tuple[float | None, float | None]:
    """The (wall, read phase) reference run `r` is judged against: its own instance's single-run values, scaled by its host's ratios for the cell.

    Without `host_ratios` this is the lookup as it always was. With them, a run of the reference host takes the values as they are; a run of another
    host the file names takes each value times that host's ratio for the run's cell (a value that is None stays None); a host the file does not name,
    a cell it lacks for that host, or a record that says no host is ValueError: a run is refused, never judged with a ratio of 1.0."""
    key = (r.get("option"), r.get("layout"), r.get("instance_id"))
    base, rbase = single.get(key), (single_read or {}).get(key)
    if host_ratios is None:
        return base, rbase
    host = (r.get("extra") or {}).get("host")
    if host == host_ratios["reference_host"]:
        return base, rbase
    where = f"run {r.get('run_key')!r}"
    if host is None:
        raise ValueError(f"{where} carries no extra.host: a host reference was asked for and the run's host is not known")
    cells = host_ratios["ratios"].get(host) if isinstance(host, str) else None
    if cells is None:
        raise ValueError(f"{where} ran on host {host!r}, which the host-reference file names neither as the reference host "
                         f"{host_ratios['reference_host']!r} nor among its hosts {sorted(host_ratios['ratios'])}")
    cell = cells.get(key[:2])
    if cell is None:
        raise ValueError(f"{where}: host {host!r} has no ratio for the cell {key[0]}/{key[1]} in the host-reference file")
    wall = None if base is None else base * cell["wall"]
    read = None if rbase is None else rbase * cell["read"]
    for what, ref, was, ratio in (("wall", wall, base, cell["wall"]), ("read", read, rbase, cell["read"])):
        if ref is not None and not math.isfinite(ref):       # a ratio the loader takes (1e308) can overflow a reference: the run's ratio to it would be 0
            raise ValueError(f"{where}: the {what} reference {was!r} x host {host!r}'s ratio {ratio!r} for {key[0]}/{key[1]} is {ref!r}, not finite")
    return wall, read


def check_scaled_references(single: dict[tuple[str, str, str], float], single_read: dict[tuple[str, str, str], float] | None, host_ratios: dict,
                            cells: Iterable[tuple[str, str]]) -> list[str]:
    """What is wrong with the references a host-reference file gives, before a curve starts: for every host of the file, every one of `cells` and every
    instance with a baseline, the scaled wall and read-phase references (`run_reference`'s) must be finite and above 0. A line per value that is not."""
    out = []
    for host, by_cell in sorted(host_ratios["ratios"].items()):
        for o, la in cells:
            cell = by_cell.get((o, la))
            if cell is None:
                continue
            for what, base_of, field in (("wall", single, "wall"), ("read", single_read or {}, "read")):
                for (bo, bl, iid), base in sorted(base_of.items()):
                    if (bo, bl) != (o, la):
                        continue
                    ref = base * cell[field]
                    if not math.isfinite(ref) or ref <= 0:
                        out.append(f"host {host!r} cell {o}/{la} instance {iid}: the {what} reference {base!r} x ratio {cell[field]!r} = {ref!r} is not a finite number above 0")
    return out


def host_reference_record(host_ratios: dict) -> dict:
    """The loaded file as a JSON-able record, for a manifest and for the exported timing: where it came from, the hash of its bytes, the ratios."""
    return {"path": host_ratios["path"], "sha256": host_ratios["sha256"], "source": host_ratios["source"], "reference_host": host_ratios["reference_host"],
            "ratios": {h: {f"{o}/{la}": dict(v) for (o, la), v in sorted(cells.items())} for h, cells in host_ratios["ratios"].items()}}


def _named_host_references(d) -> set[str]:
    """The sha256 values of the host-reference files that the decision lines of the batch directory `d` name (`host_reference.sha256`); a line that does not
    parse, or names none, is skipped."""
    import json
    from pathlib import Path
    try:
        lines = (Path(d) / "curve_decisions.jsonl").read_text().splitlines()
    except OSError:
        return set()
    out = set()
    for ln in lines:
        try:
            ref = json.loads(ln).get("host_reference")
            sha = ref.get("sha256") if isinstance(ref, dict) else None
        except (ValueError, AttributeError):
            continue
        if isinstance(sha, str) and sha:
            out.add(sha)
    return out


def find_host_ratios(dirs: Iterable) -> dict | None:
    """The host-reference file the curve batches in `dirs` were judged with, from the copy each keeps (`HOST_RATIOS_COPY`), for the report, which recomputes
    the table from the runs and must judge them as the curve did. Each batch's copy is checked against its own decision lines (`curve_decisions.jsonl`; a torn
    line is skipped, as `decided_levels` does): when any line carries a `host_reference.sha256` the batch must have the copy, of exactly that file, and the lines
    must name one file; a copy that no line names does not belong to the curve; a batch with neither is judged as it always was. None when no batch has a
    copy; ValueError when only some do (one rule per report) or their bytes differ. Not checked against any host or cell here: `run_reference` refuses a
    run the file does not cover."""
    import hashlib
    from pathlib import Path
    dirs = [Path(d) for d in dirs]
    for d in dirs:
        named, copy = _named_host_references(d), d / HOST_RATIOS_COPY
        if len(named) > 1:
            raise ValueError(f"{d}: the decision lines name more than one host-reference file ({sorted(s[:12] for s in named)}): one curve, one set of host references")
        if named:
            (sha,) = named
            if not copy.exists():
                raise ValueError(f"{d}: the decision lines name the host-reference file {sha[:12]}.. but the directory has no {HOST_RATIOS_COPY}: "
                                 f"it would be judged against the baselines unscaled")
            try:
                kept = hashlib.sha256(copy.read_bytes()).hexdigest()
            except OSError as e:
                raise ValueError(f"{e}") from None
            if kept != sha:
                raise ValueError(f"{d}: the {HOST_RATIOS_COPY} ({kept[:12]}..) differs from the file its decision lines name ({sha[:12]}..)")
        elif copy.exists():
            raise ValueError(f"{d}: has a {HOST_RATIOS_COPY} but no decision line names a host-reference file: the copy does not belong to this curve")
    paths = [d / HOST_RATIOS_COPY for d in dirs]
    have = [p for p in paths if p.exists()]
    if not have:
        return None
    if len(have) != len(paths):
        raise ValueError(f"{[str(p.parent) for p in paths if p not in have]} have no {HOST_RATIOS_COPY} while {[str(p.parent) for p in have]} do: "
                         f"the batches were not judged by one reference")
    try:
        shas = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in have}
    except OSError as e:
        raise ValueError(f"{e}") from None
    if len(set(shas.values())) != 1:
        raise ValueError(f"the copies of the host-reference file differ between the batches: {[(str(p), sha[:12]) for p, sha in shas.items()]}")
    return load_host_ratios(have[0])


def level_table(single: dict[tuple[str, str, str], float], rows: Iterable[dict], limit: float = WALL_RATIO_LIMIT, *,
                single_read: dict[tuple[str, str, str], float] | None = None, read_limit: float = READ_RATIO_LIMIT,
                host_ratios: dict | None = None, duty: bool | None = None) -> list[dict]:
    """One row per (option, layout, level) from concurrent-run records carrying `extra.level` and `extra.rep`.

    Two pass conditions, both required: every run's whole wall within `limit` of its own instance's single-run wall, and every run's
    read phase (`read_phase_s`) within `read_limit` of its own instance's single-run read phase (`single_read`). A run or baseline
    without the stamps cannot pass the read condition; `single_read=None` is no baseline at all. With `host_ratios` (`load_host_ratios`) each run's
    references are its host's (`run_reference`); the limits are the same.

    The duty-cycle form (science, #34, 11:50Z, amendment 25(b)): the two conditions are on the MEDIANS, the median wall ratio within `limit` and the
    median read-phase ratio within `read_limit`, each over at least `plans.DUTY_MIN_READS` counted clean runs with a ratio (fewer fails the cell), each
    run still against its own reference. The vetoes stand: a run not clean (an error, an OOM kill, an OOM count not known), no baseline for an instance,
    a run without its read phase. A group is in the duty form when every run in it has a truthy `extra.duty_profile` (how `duty.report_vetoes` knows
    duty records); a group that has some runs of each form is ValueError, and so is an explicit `duty` that disagrees with a group (None: detect it per
    group). A duty row has two more fields, `rule` ("duty-median") and `reads` (the read-phase ratios the median is over); the maxima and medians stay
    in it as figures. The registered form (no profile) is as it always was: the maximum, one run enough, and its rows have no more fields."""
    groups: dict[tuple[str, str, int], list[dict]] = {}
    for r in counted(rows):
        groups.setdefault((r["option"], r["layout"], int(r["extra"]["level"])), []).append(r)
    out = []
    for (opt, lay, level), rs in sorted(groups.items()):
        in_duty = [bool(r["extra"].get("duty_profile")) for r in rs]
        if any(in_duty) and not all(in_duty):
            raise ValueError(f"{opt}/{lay} level {level}: {sum(in_duty)} of its {len(rs)} counted runs are duty-cycle runs (extra.duty_profile) and the rest are not: "
                             f"one group is judged in one form")
        is_duty = all(in_duty)
        if duty is not None and bool(duty) != is_duty:
            raise ValueError(f"{opt}/{lay} level {level}: judged as the {'duty-cycle' if duty else 'registered'} form, but its runs are {'duty-cycle' if is_duty else 'registered'} ones "
                             f"(extra.duty_profile {'set' if is_duty else 'not set'})")
        errors = [r["run_key"] for r in rs if not clean(r)]
        ooms = sum(v or 0 for r in rs for v in (r.get("oom_kills") or {}).values())
        oom_unknown = sum(v is None for r in rs for v in (r.get("oom_kills") or {}).values())
        ratios, missing = [], []
        read_ratios, read_missing = [], []
        for r in rs:
            base, rbase = run_reference(single, single_read, r, host_ratios)
            if base is None:
                missing.append(r["instance_id"])
            elif clean(r):
                ratios.append(r["wall_s"] / base)
            rv = read_phase_s(r)
            if rbase is None or rv is None or rbase <= 0:
                read_missing.append(r["run_key"])
            elif clean(r):
                read_ratios.append(rv / rbase)
        if is_duty:
            from .plans import DUTY_MIN_READS
            passes_wall = (not errors and not ooms and not oom_unknown and not missing and len(ratios) >= DUTY_MIN_READS
                           and statistics.median(ratios) <= limit)
            passes_read = not read_missing and len(read_ratios) >= DUTY_MIN_READS and statistics.median(read_ratios) <= read_limit
        else:
            passes_wall = not errors and not ooms and not oom_unknown and not missing and bool(ratios) and max(ratios) <= limit
            passes_read = not read_missing and bool(read_ratios) and max(read_ratios) <= read_limit
        passes = passes_wall and passes_read
        out.append({"option": opt, "layout": lay, "level": level, "runs": len(rs), "errors": len(errors), "oom_kills": ooms,
                    "oom_unknown": oom_unknown,
                    "error_runs": errors, "no_baseline_for": sorted(set(missing)),
                    "median_ratio": round(statistics.median(ratios), 3) if ratios else None,
                    "max_ratio": round(max(ratios), 3) if ratios else None,
                    "min_throughput_share": round(1 / max(ratios), 3) if ratios else None,
                    "median_wall_s": round(statistics.median([r["wall_s"] for r in rs if clean(r)]), 1) if ratios else None,
                    "read_median_ratio": round(statistics.median(read_ratios), 3) if read_ratios else None,
                    "read_max_ratio": round(max(read_ratios), 3) if read_ratios else None,
                    "read_missing": sorted(read_missing), "passes_wall": passes_wall, "passes_read": passes_read,
                    "passes": passes, **({"rule": DUTY_MEDIAN_RULE, "reads": len(read_ratios)} if is_duty else {})})
    return out


def level_passes(cap_row: dict, level: int, earlyoom_kills: list | None) -> bool:
    """The level's verdict with earlyoom's: ANY kill on the host in the level's window fails it, whichever run or process it hit (science,
    #34), because a host that had to kill has shown the level does not fit. A journal that could not be read is not a pass."""
    return cap_row["cap"] == level and earlyoom_kills == []


def level_verdict(cap_row: dict, level: int, since: float) -> tuple[bool, list[dict] | None]:
    """(passed, the kills in earlyoom's journal since the level began, None when it could not be read)."""
    from ..sandbox import earlyoom as EO
    kills = EO.read_kills(since)
    return level_passes(cap_row, level, None if kills is None else [k.record() for k in kills]), None if kills is None else [k.record() for k in kills]


def earlyoom_vetoes(dirs: Iterable, *, traced: bool = True) -> dict[int, set[int]]:
    """block -> the levels failed by earlyoom, from each batch's `curve_decisions.jsonl`: any kill in the level's window, or a journal that could not be read. A decision
    written before this field existed vetoes nothing. Within a batch a level's last line wins, as in `decided_levels`; across batches, either vetoes. Only decisions
    of the tracing state being reported count, as with the runs (a decision without the field is traced: every curve was)."""
    import json
    from pathlib import Path
    out: dict[int, set[int]] = {}
    for d in dirs:
        last: dict[tuple[int, int, int], bool] = {}
        try:
            lines = (Path(d) / "curve_decisions.jsonl").read_text().splitlines()
        except OSError:
            continue
        for ln in lines:
            try:
                rec = json.loads(ln)
                key = (int(rec["block"]), int(rec["level"]), int(rec.get("rep", 0)))
            except (ValueError, KeyError, TypeError):
                continue
            if bool(rec.get("traced", True)) is traced:
                last[key] = "earlyoom_kills" in rec and rec["earlyoom_kills"] != []
        for (block, level, _), vetoed in last.items():
            if vetoed:
                out.setdefault(block, set()).add(level)
    return out


def duty_decisions(dirs: Iterable, *, traced: bool = True) -> dict[tuple[int, int, int], str | None]:
    """(block, level, rep) -> None for a duty-cycle level whose last decision line passed, else why it did not, from each batch's `curve_decisions.jsonl`
    (review S1, finding 4): a line is the duty-cycle curve's when it names a `duty_profile_id`. `cmd_curve` fails a level for more than the timing
    table shows (earlyoom, the M gate's share, a counted run that waited for the pacer, a part's infrastructure failure), and the report, which
    recomputes the table from the runs, takes that failure from here. Within a batch a level's last line wins, as in `decided_levels`; across batches a
    failure stands. Only decisions of the tracing state being reported count (a line without the field is traced). A line that does not parse is
    skipped; a `passed` that is not true is a failure."""
    import json
    from pathlib import Path
    out: dict[tuple[int, int, int], str | None] = {}
    for d in dirs:
        last: dict[tuple[int, int, int], str | None] = {}
        try:
            lines = (Path(d) / "curve_decisions.jsonl").read_text().splitlines()
        except OSError:
            continue
        for ln in lines:
            try:
                rec = json.loads(ln)
                key = (int(rec["block"]), int(rec["level"]), int(rec["rep"]))
                if not rec.get("duty_profile_id") or bool(rec.get("traced", True)) is not traced:
                    continue
                if rec.get("passed") is True:
                    last[key] = None
                    continue
                bits = [str(rec[f]) for f in ("failed_for",) if rec.get(f)]
                if rec.get("infrastructure"):
                    bits.append(f"infrastructure: {rec['infrastructure']}")
                if rec.get("failing_cells"):
                    bits.append(f"failing cells {rec['failing_cells']}")
                if rec.get("paced_waits"):
                    bits.append(f"paced waits {rec['paced_waits'][:3]}")
                last[key] = ("; ".join(bits) or "passed is not true")[:300]
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
        for key, why in last.items():
            if key not in out or why is not None:
                out[key] = why
    return out


def duty_ladders(dirs: Iterable, *, traced: bool = True) -> dict[int, dict]:
    """block -> the ladder (`{"frozen", "climb", "floor"}`, copied from the frozen profile onto every line) of the duty-cycle curve in these batches' `curve_decisions.jsonl`
    (amendment 34(a): the report marks the ladder's levels that did not run). A line counts as `duty_decisions` counts it: it names a `duty_profile_id` and is of the tracing
    state being reported; one with no ladder (an older curve) gives its block none. More than one ladder in a block, in one batch or across them, is not one curve:
    ValueError. A line that does not parse is skipped."""
    import json
    from pathlib import Path
    seen: dict[int, dict[str, dict]] = {}
    for d in dirs:
        try:
            lines = (Path(d) / "curve_decisions.jsonl").read_text().splitlines()
        except OSError:
            continue
        for ln in lines:
            try:
                rec = json.loads(ln)
                block = int(rec["block"])
                if not rec.get("duty_profile_id") or bool(rec.get("traced", True)) is not traced or not isinstance(rec.get("ladder"), dict):
                    continue
                seen.setdefault(block, {})[json.dumps(rec["ladder"], sort_keys=True)] = rec["ladder"]
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
    many = {b: len(v) for b, v in seen.items() if len(v) > 1}
    if many:
        raise ValueError(f"the decision lines name more than one ladder in block(s) {sorted(many)}: not one curve")
    return {b: next(iter(v.values())) for b, v in sorted(seen.items())}


def cap(table: Iterable[dict], cells: Iterable[tuple[str, str]], levels: Iterable[int],
        single: dict[tuple[str, str, str], float], single_read: dict[tuple[str, str, str], float] | None = None) -> dict:
    """The highest measured level at which every cell passes, level 1 counting only with a clean single run per cell AND a
    measured read phase for every instance that has a wall baseline (`single_read`; none given is no evidence, as in `level_table`).

    `cap` is None when no level qualifies: nothing measured is never a cap. A cell not measured at a level means that
    level is not passed. The rule says "highest level", so a level passing above a failing one is what `cap` gives;
    `contiguous_cap` (stopping at the first failure) and `failing` show whether that happened."""
    t = {(r["option"], r["layout"], r["level"]): r for r in table}
    cells = list(cells)
    read_ok = {k for k, v in (single_read or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0}
    with_baseline = {(o, la) for o, la, _ in single if all(k in read_ok for k in single if k[:2] == (o, la))}
    failing = {1: [f"{o}/{la}" for o, la in cells if (o, la) not in with_baseline]}
    for level in sorted(levels):
        failing[level] = [f"{o}/{la}" for o, la in cells if not t.get((o, la, level), {}).get("passes", False)]
    passed = [lv for lv in sorted(failing) if not failing[lv] and cells]
    contiguous = None
    for lv in sorted(failing):
        if failing[lv] or not cells:
            break
        contiguous = lv
    return {"cap": passed[-1] if passed else None, "contiguous_cap": contiguous,
            "failing": {lv: f for lv, f in failing.items() if f}}


def search(levels: Iterable[int], stop: str, passes) -> list[tuple[int, bool]]:
    """Try `levels` in the order given, calling `passes(level)`. `first-pass` stops at the first that passes (the old top-down
    search, superseded by science's upward ruling on #2); `first-fail` at the first that fails (going up: the curve); `none` tries them all."""
    if stop not in ("first-pass", "first-fail", "none"):
        raise ValueError(f"unknown stop rule {stop!r}")
    out = []
    for lv in levels:
        ok = bool(passes(lv))
        out.append((lv, ok))
        if (stop == "first-pass" and ok) or (stop == "first-fail" and not ok):
            break
    return out


def sequence_state(frozen: Iterable[int], climb: Iterable[int], floor: int | None, decided: dict[int, bool]) -> dict:
    """Where a duty-cycle curve with a climb and step-downs stands (science, #34, 3 Nov 00:33Z), a pure function of the frozen levels and the levels
    decided so far (a level -> whether it passed; an undecided level is absent, so the order the results arrived in does not matter).

    "The climb is 8, 16, 24, 32, 42; a failure tests the frozen level below it (12 only if 16 fails, and so on); if 8 fails, go down to 4, then 2."
    `frozen` is the profile's levels (4, 8, 12, 16, 24, 32, 42), `climb` the subset that runs in order (8, 16, ..), `floor` the one level below the first
    frozen one (2). The climb goes up while levels pass. The first climb level to fail, L, starts a step-down: the frozen level directly below L is run
    (the floor below the first frozen level); if it passes it is the cap, if it fails the next one down is run, and so on. A step-down stops at once on
    a level already known to pass (the climb's last pass: 24 failing after 16 passed leaves nothing between, the cap is 16), and a ladder whose every
    level failed has no cap. A rerun (25(d)) is a one-level climb, [the first curve's cap], so it steps down until one passes.

    Returns {"next": the level to run now or None, "done": nothing more is due, "cap": the cap when done (None: no cap) and, while more is due, the
    provisional one: the highest level known to pass so far, which a step-down may still raise (None: none yet), "failed_at": the climb level that
    failed, "visited": the levels the sequence has reached}. A decided level not in "visited" is one the sequence never asked for."""
    frozen, climb = [int(x) for x in frozen], [int(x) for x in climb]
    if not frozen or any(b <= a for a, b in zip(frozen, frozen[1:])):
        raise ValueError(f"frozen {frozen}: must be strictly ascending")
    if floor is not None and not 1 <= floor < frozen[0]:
        raise ValueError(f"floor {floor}: must be below the first frozen level {frozen[0]}")
    ladder = ([int(floor)] if floor is not None else []) + frozen
    if not climb or any(b <= a for a, b in zip(climb, climb[1:])) or not set(climb) <= set(ladder):
        raise ValueError(f"climb {climb}: must be strictly ascending and a subset of the frozen levels {frozen} and the floor {floor} (a rerun at a first cap of 2 climbs [2])")
    visited: list[int] = []
    known: int | None = None                                   # the climb's last pass

    def out(nxt, done, cap, failed):
        return {"next": nxt, "done": done, "cap": cap, "failed_at": failed, "visited": list(visited)}
    for lv in climb:
        visited.append(lv)
        d = decided.get(lv)
        if d is None:
            return out(lv, False, known, None)
        if d:
            known = lv
            continue
        for c in [x for x in reversed(ladder) if x < lv]:
            if known is not None and c <= known:
                return out(None, True, known, lv)
            visited.append(c)
            d = decided.get(c)
            if d is None:
                return out(c, False, known, lv)
            if d:
                return out(None, True, c, lv)
        return out(None, True, None, lv)                       # every level down to the ladder's bottom failed: no cap
    return out(None, True, known, None)                        # the whole climb passed: its top is the cap


def run_sequence(frozen: Iterable[int], climb: Iterable[int], floor: int | None, passes) -> tuple[list[tuple[int, bool]], dict]:
    """Drives `sequence_state`: calls `passes(level)` for the level due until none is, and returns ([(level, passed)] in the order run, the final state).
    A level is only ever run when the sequence asks for it, so a step-down that was not needed never exists."""
    frozen, climb = list(frozen), list(climb)
    decided: dict[int, bool] = {}
    results: list[tuple[int, bool]] = []
    while True:
        st = sequence_state(frozen, climb, floor, decided)
        if st["next"] is None:
            return results, st
        ok = bool(passes(st["next"]))
        decided[st["next"]] = ok
        results.append((st["next"], ok))


DEFAULT_LEVELS = (2, 4, 8, 12, 16)


def plan_levels(levels: Iterable[int], max_level: int) -> list[int]:
    """The levels the curve tries, UPWARD (science, #2, 2 Nov 00:52Z): strictly ascending as given, none above `max_level`
    (the site_g capacity benchmark's safe level, or the hard maximum). A list not in ascending order is refused, never sorted:
    the order is the search."""
    lv = list(levels)
    if not lv or any(b <= a for a, b in zip(lv, lv[1:])) or lv[0] < 1:
        raise ValueError(f"levels {lv}: must be positive and strictly ascending (the curve searches upward)")
    return [x for x in lv if x <= max_level]


def baseline_id(single: dict[tuple[str, str, str], float], single_read: dict[tuple[str, str, str], float], host_ratios: dict | None = None) -> str:
    """Which baseline a level was judged against: a hash of every cell's wall and read-phase baseline. With a host-reference file (`load_host_ratios`) the
    hash of that hash and of the file's bytes: a level judged with other host references is another baseline. Without one, the hash is as it always was."""
    import hashlib
    import json
    flat = {"wall": sorted([*k, v] for k, v in single.items()), "read": sorted([*k, v] for k, v in single_read.items())}
    plain = hashlib.sha256(json.dumps(flat, sort_keys=True).encode()).hexdigest()
    if host_ratios is None:
        return plain
    return hashlib.sha256(json.dumps({"baseline_id": plain, "host_reference_sha256": host_ratios["sha256"]}, sort_keys=True).encode()).hexdigest()


def decided_levels(path, block: int, rep: int, *, traced: bool | None = None, baseline: str | None = None) -> dict[int, bool]:
    """Levels already decided for this block and rep in `curve_decisions.jsonl` (the last line of a level wins): a resumed
    curve does not run them again. A missing file or a torn last line decides nothing.

    With `traced` given, a decision may be reused only if it was made in that tracing state (a line without the field is traced:
    every curve was) and against `baseline` (`baseline_id`; a line without one cannot be checked): otherwise ValueError names
    the levels, because a cap would then rest on a level never measured as this run is configured."""
    import json
    out: dict[int, bool] = {}
    state: dict[int, tuple[bool, str | None]] = {}
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return out
    for ln in lines:
        try:
            r = json.loads(ln)
            if r["block"] == block and r.get("rep", 1) == rep:
                out[int(r["level"])] = bool(r["passed"])
                state[int(r["level"])] = (bool(r.get("traced", True)), r.get("baseline_id"))
        except (ValueError, KeyError, TypeError):
            continue
    if traced is not None:
        wrong = sorted(lv for lv, (t, b) in state.items() if t is not traced or b != baseline)
        if wrong:
            raise ValueError(f"levels {wrong} of block {block} rep {rep} in curve_decisions.jsonl were decided in another tracing state "
                             f"or against another baseline (or record neither): not reused")
    return out


def append_decision(path, rec: dict) -> None:
    """One JSON line per decided level. A file whose last line was torn (no final newline) gets a newline first, so the
    new line is not glued to the fragment and lost."""
    import json
    from pathlib import Path
    p = Path(path)
    torn = p.exists() and p.stat().st_size > 0 and not p.read_bytes().endswith(b"\n")
    with open(p, "a") as f:
        f.write(("\n" if torn else "") + json.dumps(rec) + "\n")


def set_aside_partial(runs_dir, aside_dir, block: int, level: int, rep: int, utc: str = "") -> list[str]:
    """A level cut mid-way is redone whole: its run directories (same plan keys, so they would collide) move to `aside_dir`
    and enter no statistic (`load_runs` reads `runs/*` only). Only the mix directories of exactly this block, level and rep move."""
    from pathlib import Path
    runs, aside = Path(runs_dir), Path(aside_dir)
    marker = f"-b{block}-c{level}-r{rep}-"
    moved = []
    if utc:
        aside = aside / f"{level}-{utc}"
    for d in sorted(runs.glob("*")) if runs.is_dir() else []:
        if d.is_dir() and (f"mix{marker}" in d.name or f"mixpad{marker}" in d.name):
            aside.mkdir(parents=True, exist_ok=True)
            dest, k = aside / d.name, 2
            while dest.exists():
                dest, k = aside / f"{d.name}.{k}", k + 1
            d.rename(dest)
            moved.append(d.name)
    return moved


def cap_of(results: Iterable[tuple[int, bool]]) -> int | None:
    """The cap of an upward search: the last level that passed before the first failure. None when the first level failed
    (or nothing ran): no cap. A pass after a failure is never a cap."""
    best = None
    for lv, ok in results:
        if not ok:
            break
        best = lv
    return best


MEM_RESERVE_GIB = 8.0       # kept free for the host and the other lanes
MEM_MARGIN = 1.15           # on the largest measured run: the mix has more variety than the baselines


def mem_per_run_gib(rows: Iterable[dict]) -> float | None:
    """The memory one run can take, from the baselines' measured cgroup peaks: the largest run's agent + gate + sidecar
    peaks summed (they need not peak together, so this errs high), with a margin. None unless EVERY run has a numeric
    peak for every container its option has: a run with an unknown peak is not skipped, it makes the estimate unknown."""
    tot = []
    for r in rows:
        cs = r.get("containers") or {}
        need = required_containers(r.get("option", ""))
        peaks = [(cs.get(c) or {}).get("peak_bytes") for c in need]
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0 for x in peaks):
            return None
        tot.append(sum(peaks))
    return round(max(tot) * MEM_MARGIN / 1024 ** 3, 3) if tot else None


def levels_that_fit(levels: Iterable[int], available_gib: float, per_run_gib: float,
                    reserve_gib: float = MEM_RESERVE_GIB) -> list[int]:
    """The levels whose `level` runs fit in MemAvailable with the reserve kept: a level that does not is dropped, never
    pushed, because a host OOM would invalidate the measurement (science, 17:49Z: if 16 does not fit, the top level is 12)."""
    return [lv for lv in levels if lv * per_run_gib + reserve_gib <= available_gib]
