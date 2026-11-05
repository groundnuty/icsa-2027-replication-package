"""From a campaign's run directories to the files the analysis, the dossier and the cause coder read.

For every run the campaign store marks done, the analysed attempt only (the export's
`analysed_attempts`, `icsa.campaign.export`): label it (#9), score it (#13), build its cause evidence
and code it (#17). Nothing is ever written into a run directory, outputs are sorted by
(block, run_key) and carry no timestamp or path, so the same inputs give byte-identical files.
A run that cannot be processed is listed in the manifest (reason and detail) and makes the exit code
non-zero; it is never dropped silently. A run with no trace is labelled `unknown`, reason `no_trace`.
"""
from __future__ import annotations

import collections
import dataclasses
import hashlib
import json
import multiprocessing
import os
import re
import resource
import shutil
import sqlite3
import threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from icsa.campaign.export import export_infra
from icsa.causes import evidence_from
from icsa.causes.batch import Batch
from icsa.causes.evidence import truncated_downloads
from icsa.causes.rules import code_run
from icsa.causes.sampling import sheet_row, write_sheet
from icsa.instruments.crosscheck import gate_truncated_downloads
from icsa.instruments.labeller import code_cells_of, coverage_upper_bound, label_run
from icsa.instruments.readext import jsonl
from icsa.records import OmissionLabel, Option, ScoredRow, Termination
from icsa.scoring.scorer import score_run

from .loadrec import PipelineError, resolve_record
from .resources import Resources

FORMAT = "icsa-pipeline-manifest-v1"
NO_TRACE = "no_trace"
OUTPUTS = ("scored_rows.jsonl", "run_records.jsonl", "run_labels.jsonl", "causes.csv", "cause_flags.csv",
           "infra.json", "none_counts.json", "manifest.json")
PLATFORM_FILES = ("gate_requests.jsonl", "oneclient_perf", "proxy.jsonl", "fuse.jsonl", "remote.jsonl", "localread.jsonl", "strace.txt")
HASHED = ("instruments", "scoring", "causes", "pipeline")
SHEET_DIR = "second_coder"     # sheet.csv and the runs' files go to the second coder; key.csv stays here (causes.sampling)


def _jd(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if hasattr(o, "value") and hasattr(o, "name"):      # an enum
        return o.value
    raise TypeError(f"not JSON-serialisable: {type(o).__name__}")


def dumps(o) -> str:
    return json.dumps(o, sort_keys=True, default=_jd)


def tree_hash(package: str) -> str:
    """sha256 over the sorted (relative path, bytes) of a package's source files: the instrument as it is on
    disk, a dirty tree included (a git commit would hide it)."""
    root = Path(__file__).resolve().parents[1] / package
    h = hashlib.sha256()
    for p in sorted(q for q in root.rglob("*") if q.is_file() and q.suffix in (".py", ".md", ".toml", ".json")
                    and "__pycache__" not in q.parts):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


class ReadOnlyStore:
    """Just `q`, on the campaign's SQLite opened read-only (the pipeline changes nothing in the campaign)."""

    def __init__(self, path: Path):
        if not Path(path).is_file():
            raise PipelineError("no_campaign_state", f"{path}")
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
        self.db.row_factory = sqlite3.Row

    def q(self, sql, args=()):
        return self.db.execute(sql, tuple(args)).fetchall()

    def close(self):
        self.db.close()


@dataclasses.dataclass
class Processed:
    row: ScoredRow
    record_json: str
    label_row: dict
    coding: object            # causes.rules.Coding | Skipped
    evidence: object          # RunEvidence, slimmed (no extents)
    label: OmissionLabel
    reasons: list[str]
    sheet: dict | None = None  # the second coder's row, if the run is coded (causes.sampling.sheet_row)
    run_dir: str = ""


def _has_trace(trace: Path) -> bool:
    """A trace is a tracer that started. Streams without its start event say nothing about what was read, and labelling them would
    make the run omitting, `not_loaded`, for reads nobody watched."""
    if not trace.is_dir():
        return False
    for p in trace.glob("events.*.jsonl"):
        with open(p, errors="replace") as fh:
            for line in fh:
                try:
                    if json.loads(line).get("kind") == "start":
                        return True
                except (ValueError, AttributeError):         # a torn line
                    continue
    return False


_ICSA_PACKAGE = re.compile(r"\bicsa\b")          # the tracer's package: `import icsa`, sys.modules["icsa"], /opt/icsa/
_DATASET_DIR = re.compile(r"icsa2027_data_\w*")
_ICSA_NAME = re.compile(r"[\w./-]*icsa[\w./-]*", re.I)


def code_names_package(code: list[str] | None) -> bool | None:
    """Whether a run's code names the tracer's package (science, for the pilot's report): a word-bounded, case-sensitive
    search, so the dataset's directory and ICSA_DATASET_LOCATION do not count. None: no code to search."""
    return None if code is None else any(_ICSA_PACKAGE.search(c) for c in code)


def icsa_names(code: list[str] | None) -> list[str] | None:
    """Every name holding `icsa` in any case in a run's code, as written, beside that count: a run reading
    ICSA_DATASET_LOCATION from its environment shows here. The dataset's own directory does not, since every run has to
    name it to read anything. None: no code to search, which is not the same as no name."""
    if code is None:
        return None
    return sorted({m.group(0) for m in _ICSA_NAME.finditer("\n".join(code)) if "icsa" in _DATASET_DIR.sub("", m.group(0)).lower()})


def _xcheck(lab, name: str):
    """One of #9's cross-check flags: None with no trace (no outside view to compare), else what the labeller says,
    by a key it always sets, so a flag that stopped reaching the cause coder fails here and cannot pass as None."""
    return None if lab is None else lab.analysis.flags[name]


GATED = (Option.T, Option.T_UNPAGINATED, Option.D)


def _not_observed(option: Option, lab) -> list[str]:
    """For T, T-unpaginated and D (the gated options): the evidence a run lacks, by named reason. It blocks
    dossier criterion 2, so the manifest counts it per option. A run with no trace lacks all of it."""
    if option not in GATED:
        return []
    out = []
    if lab is None or lab.read is None:
        out += ["read_not_observed", "read_beyond_days_not_observed"]
    if lab is None or lab.listing is None:
        out.append("listing_not_observed")
    return out


def escape_kinds(trace_dir: Path) -> dict[str, int] | None:
    """The tracer's escapes in a run, by kind (the event's `how`: scalar, scalar_index, tolist, iter, a library call, ...), from every events
    stream. `escape_log_full` counts the runs whose escape log filled, so the counts are a lower bound there. None when there is no stream."""
    from icsa.instruments.analyse import _jsonl
    files = sorted(Path(trace_dir).glob("events.*.jsonl"))
    if not files:
        return None
    out: dict[str, int] = {}
    for f in files:
        for e in _jsonl(f):
            k = e.get("kind")
            if k == "escape":
                how = str(e.get("how") or "unnamed")
                out[how] = out.get(how, 0) + 1
            elif k == "escape_log_full":
                out["escape_log_full"] = 1
    return out


def process_run(entry: dict, store_row, res: Resources) -> Processed:
    run_dir = Path(entry["run_dir"])
    if not run_dir.is_dir():
        raise PipelineError("run_dir_missing", str(run_dir))
    rec, raw = resolve_record(run_dir, entry, store_row)
    iid, layout, option = rec.run.instance_id, rec.run.layout, rec.run.option
    required, ref = res.required(iid), res.reference(iid)
    trace = run_dir / "trace"
    lab = None
    # the sandbox's cell log is the code that really ran; the harness's code_cells.json is the fallback
    cells = next((c for c in (run_dir / "cells" / "cells.jsonl", run_dir / rec.code_cells_path) if c.is_file()), None)
    if not _has_trace(trace):
        # No trace: the extent cannot be known. Never complete, never dropped (the run is scored on its output).
        label, analysed, reasons = OmissionLabel.UNKNOWN, None, [NO_TRACE]
        try:
            code = code_cells_of(cells) if cells else None
        except OSError:                                               # only the count of names needs it: no reason to lose the run
            code = None
    else:
        code = code_cells_of(cells) if cells else None                # None: code_not_scanned, so never complete
        lab = label_run(option.value, trace, run_dir / rec.output_dir, res.index(layout), required,
                        platform_dir=run_dir,
                        local_roots=res.local_roots(option, run_dir), dir_sizes=res.dir_sizes(layout),
                        code_text=code)
        label, analysed, reasons = lab.label, lab.analysed, list(lab.reasons)
    saw = lab.analysis.flags.get("agent_saw_data_error") if lab else None
    raw_label = lab.analysis.flags.get("raw_label") if lab else None      # not `raw`: that is the run record, written to run_records.jsonl below
    row = score_run(rec, run_dir, ref, analysed, label,
                    agent_saw_data_error=saw if isinstance(saw, bool) else None,
                    coverage_upper=coverage_upper_bound(lab.analysis) if lab else None,       # amendment 26(h)
                    label_raw=OmissionLabel(raw_label) if raw_label in {x.value for x in OmissionLabel} else None,
                    label_reasons=reasons if lab else None, tracking=lab.analysis.flags.get("tracking") if lab else None,
                    escape_kinds=escape_kinds(trace) if lab else None)

    caveats = None
    if row.report_valid:
        c = json.loads((run_dir / rec.output_dir / "report.json").read_text()).get("caveats")
        caveats = c if isinstance(c, str) else None
    read = lab.read if lab else None
    tdl = None
    if option == Option.D:     # from the logs, the outside view: a run with no trace may have them
        if (run_dir / "proxy.jsonl").is_file():             # the local server's log
            tdl = truncated_downloads(jsonl(run_dir / "proxy.jsonl"), {k: v.size for k, v in res.index(layout).layouts.items()})
        elif (run_dir / "gate_requests.jsonl").is_file():   # the gate's, the only one a real run has
            index = res.index(layout)
            tdl = gate_truncated_downloads(jsonl(run_dir / "gate_requests.jsonl"), getattr(index, "ids", None),
                                           {k: v.size for k, v in index.layouts.items()})
    ev = evidence_from(rec, row, required, analysed=analysed, read=read.extent if read else None,
                       listing=None if not lab or lab.listing is None else {d: v.to_json() for d, v in lab.listing.items()},
                       truncated_downloads=tdl, read_beyond_units=read.beyond if read else None,
                       read_beyond_days=read.beyond_days if read else None,
                       read_other_days=read.other_days if read else None, caveats=caveats,
                       listing_disagrees=_xcheck(lab, "listing_disagrees"),
                       decoded_not_delivered=_xcheck(lab, "decoded_not_delivered"),
                       delivered_not_decoded=_xcheck(lab, "delivered_not_decoded"))
    coding = code_run(ev)
    # The sample depends on every run's code, so it is known only at the end, when the extents are gone. What the sheet takes from
    # them is two shares each, so a coded run keeps its row, about 1 KB, and the extents are never stored.
    sheet = sheet_row(ev, "") if hasattr(coding, "primary") else None
    if sheet is not None:      # the code the labeller scanned, not the harness's copy of it
        sheet["code_cells_path"] = "" if cells is None else cells.relative_to(run_dir).as_posix() if cells.is_relative_to(run_dir) else str(cells)
    slim = dataclasses.replace(ev, required=None, analysed=None, read=None)    # the extents are large; the tables need none
    lrow = lab.summary() if lab else {}
    lrow["not_observed"] = _not_observed(option, lab)
    lrow.update(tracer_share_of_run(lab, rec))
    lrow["code_names_package"] = code_names_package(code)
    lrow["code_icsa_names"] = icsa_names(code)
    # fields that are None for this run (dossier criterion 2: all-None must not pass as success)
    lrow["none_fields"] = (["read", "read_beyond_days"] if lab is None or lab.read is None else []) + \
        (["listing"] if option in GATED and (lab is None or lab.listing is None) else [])
    pdir = run_dir
    lrow.update({"platform_evidence": any((pdir / f).exists() for f in PLATFORM_FILES),
                 "block": rec.block, "run_key": rec.run.key(), "store_run_key": entry["run_key"],
                 "attempt": rec.attempt, "label": label.value, "reasons": reasons, "no_trace": lab is None,
                 "finished": row.finished})
    return Processed(row, json.dumps(raw, sort_keys=True), lrow, coding, slim, label, reasons, sheet, str(run_dir))


class _Spool:
    """Keeps the big per-run records off the heap: appended to a file, read back in sorted order."""

    def __init__(self, path: Path):
        self.fh = open(path, "w+b")
        self.at: dict[tuple, tuple[int, int]] = {}

    def add(self, key: tuple, text: str) -> None:
        b = (text + "\n").encode()
        self.fh.seek(0, os.SEEK_END)
        self.at[key] = (self.fh.tell(), len(b))
        self.fh.write(b)

    def lines(self):
        for k in sorted(self.at):
            off, n = self.at[k]
            self.fh.seek(off)
            yield self.fh.read(n)

    def close(self, path: Path) -> None:
        self.fh.close()
        path.unlink(missing_ok=True)


def _not_observed_counts(done, keys) -> dict:
    out: dict = {}
    for k in keys:
        o = done[k].evidence.option
        if o in GATED:
            d = out.setdefault(o.value, {"runs": 0})
            d["runs"] += 1
            for r in done[k].label_row["not_observed"]:
                d[r] = d.get(r, 0) + 1
    return {o: dict(sorted(d.items())) for o, d in sorted(out.items())}


def none_counts(done, keys, block: str = "pilot") -> dict:
    """The pilot's per-option None counts, the format the dossier's `none_counts` input defines (#18):
    {"T": {"runs", "read", "read_beyond_days", "listing"}, ..., "M": {"runs", "read", "read_beyond_days"}}."""
    out: dict = {}
    for k in keys:
        ev = done[k].evidence
        if ev.block != block:
            continue
        o = ev.option
        d = out.setdefault(o.value, {"runs": 0, "read": 0, "read_beyond_days": 0, **({"listing": 0} if o in GATED else {})})
        d["runs"] += 1
        for f in done[k].label_row["none_fields"]:
            d[f] += 1
    return {"none_counts": dict(sorted(out.items()))}


def tracer_share_of_run(lab, rec) -> dict:
    """The tracer's own time against the run's wall time and its cap, per run from the pilot on (science, #34). A lower bound: it
    counts the outermost hooks, not the patched conversions or the file hashing (instruments/DESIGN.md). None: no record, not none."""
    tt = lab.analysis.flags.get("tracer_time") if lab is not None else None
    if not tt or not tt.get("processes"):
        return {"tracer_hook_wall_s": None, "tracer_share_of_wall": None, "tracer_share_of_cap": None}
    cap = ((rec.extras or {}).get("limits") or {}).get("time_cap_s")
    return {"tracer_hook_wall_s": tt["hook_wall_s"], "tracer_share_of_wall": tt["hook_wall_s"] / rec.wall_time_s if rec.wall_time_s else None,
            "tracer_share_of_cap": tt["hook_wall_s"] / cap if cap else None}


def tracer_time_counts(done, keys) -> dict:
    """Per block: runs with a record, and how many spend over 5% and over 10% of their wall time in the tracer (science's trigger),
    and how many stopped at the time cap with over 10% of the cap in it (DESIGN.md). Each is a lower bound until the tracer's own
    counter covers what it misses (tracer finding #9), and says so: a count of 0 does not clear the trigger."""
    out: dict = {}
    for k in keys:
        r = done[k].label_row
        d = out.setdefault(done[k].evidence.block, {"lower_bound": True, "runs": 0, "no_record": 0, "no_wall_time": 0, "over_5pct_of_wall": 0,
                                                    "over_10pct_of_wall": 0, "cap_stops": 0, "cap_stops_over_10pct_of_cap": 0,
                                                    "largest_share_of_wall": None})
        d["runs"] += 1
        share = r["tracer_share_of_wall"]
        if r["tracer_hook_wall_s"] is None:
            d["no_record"] += 1
        elif share is None:
            d["no_wall_time"] += 1
        else:
            d["over_5pct_of_wall"] += share > 0.05
            d["over_10pct_of_wall"] += share > 0.10
            d["largest_share_of_wall"] = max(share, d["largest_share_of_wall"] or 0.0)
        if done[k].evidence.termination == Termination.TIME_CAP:
            d["cap_stops"] += 1
            d["cap_stops_over_10pct_of_cap"] += (r["tracer_share_of_cap"] or 0.0) > 0.10
    return dict(sorted(out.items()))


def pilot_icsa_count(done, keys) -> dict:
    """How many of the pilot's runs have code naming the tracer's package, and every name holding `icsa` beside it. The sizing
    runs (amendment 13) are outside the campaign's store, in their own sealed directory, so they never reach a manifest."""
    rows = [done[k].label_row for k in keys if done[k].evidence.block == "pilot"]
    return {"runs": len(rows), "code_names_package": sum(bool(r["code_names_package"]) for r in rows),
            "no_code": sum(r["code_names_package"] is None for r in rows),
            "names": dict(sorted(collections.Counter(n for r in rows for n in (r["code_icsa_names"] or [])).items()))}


def _atomic(path: Path, data: bytes | str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data.encode() if isinstance(data, str) else data)
    os.replace(tmp, path)


def _by_instance(entries: list[dict]) -> list[list[dict]]:
    """The runs of one instance share a reference, the expensive input, so a group goes to one worker, in its order."""
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["key"].split("__")[0], []).append(e)
    return list(groups.values())


def _failure(e: dict, reason: str, detail: str) -> dict:
    return {"block": e["block"], "run_key": e["key"], "store_run_key": e["run_key"], "reason": reason, "detail": detail}


def _process_group(group: list[dict], flags_of, res: Resources) -> tuple[dict[tuple, Processed], list[dict]]:
    done: dict[tuple, Processed] = {}
    failed: list[dict] = []
    for e in group:
        k = (e["block"], e["key"])
        try:
            if k in done:
                raise PipelineError("duplicate_run", f"two analysed attempts for {k}")
            done[k] = process_run(e, flags_of[e["run_key"]], res)
        except PipelineError as err:
            failed.append(_failure(e, err.reason, err.detail))
        except Exception as err:    # noqa: BLE001 -- listed, never dropped; the exit code reports it
            failed.append(_failure(e, f"error:{type(err).__name__}", str(err)[:300]))
    return done, failed


_SHARED: tuple = ()         # set in each worker: the store's flags (sqlite rows do not pickle) and the resources, inherited by the fork


def _init_worker(worker_gib: int, flags_of, res: Resources) -> None:
    global _SHARED
    resource.setrlimit(resource.RLIMIT_AS, (worker_gib << 30, worker_gib << 30))
    _SHARED = (flags_of, res)


def _work(group: list[dict]) -> tuple[dict[tuple, Processed], list[dict]]:
    return _process_group(group, *_SHARED)


def _process_all(groups: list[list[dict]], flags_of, res: Resources, jobs: int, worker_gib: int):
    """Yields each instance's (done, failed). With `jobs` > 1, in forked workers, each under `worker_gib` of address space, so
    one that needs more fails its run (a MemoryError, listed) instead of taking the host down. A worker that dies is listed
    against every run of its group; nothing is dropped. The outputs are sorted afterwards, so `jobs` changes no byte of them."""
    if jobs <= 1:
        for g in groups:
            yield _process_group(g, flags_of, res)
        return
    if threading.active_count() > 1:     # a fork copies a lock another thread holds, locked for good (the netCDF lock, say)
        raise ValueError("--jobs needs a single-threaded parent: it forks")
    try:
        res.preload()                    # shared with the workers by the fork, not built once by each
    except Exception:                    # noqa: BLE001 -- only a saving: each run then fails on it and is listed, as in serial
        pass
    with ProcessPoolExecutor(jobs, mp_context=multiprocessing.get_context("fork"), initializer=_init_worker,
                             initargs=(worker_gib, flags_of, res)) as ex:
        futures: list[tuple[list[dict], object]] = []
        for g in groups:
            try:
                futures.append((g, ex.submit(_work, g)))
            except Exception as err:     # noqa: BLE001 -- a worker already died: the pool takes no more
                futures.append((g, err))
        for g, f in futures:
            try:
                if isinstance(f, Exception):
                    raise f
                yield f.result()
            except Exception as err:     # noqa: BLE001 -- a worker killed mid-group: BrokenProcessPool, here and for the groups after it
                yield {}, [_failure(e, f"error:{type(err).__name__}", str(err)[:300]) for e in g]


def run_pipeline(campaign_root: Path, out: Path, res: Resources, *, jobs: int = 1, worker_gib: int = 8) -> dict:
    """Process a campaign; write the outputs into `out`; return the manifest. Raises on a campaign that
    cannot be read; a single run that fails is listed in the manifest's `failed`. `jobs`: instances at a time."""
    campaign_root, out = Path(campaign_root), Path(out)
    store = ReadOnlyStore(campaign_root / "state.sqlite")
    try:
        export = export_infra(store, res.instances())
        flags_of = {r["run_key"]: r for r in store.q("SELECT run_key, exclude_from_analysis FROM runs")}
        attempt_dirs = [r["run_dir"] for r in store.q("SELECT run_dir FROM attempts") if r["run_dir"]]
    finally:
        store.close()
    here = out.resolve()
    for d in [*attempt_dirs, str(campaign_root / "runs")]:       # every attempt's directory, discarded ones too
        rd = Path(d).resolve()
        if here == rd or rd in here.parents:
            raise PipelineError("output_inside_run_dir", f"{out} is inside {rd}: the pipeline never writes into a run directory")
    out.mkdir(parents=True, exist_ok=True)
    # grouped by instance, so the one cached reference serves a whole group; outputs are sorted afterwards
    entries = sorted(export["analysed_attempts"], key=lambda e: (e["key"].split("__")[0], e["block"], e["run_key"]))
    done: dict[tuple, Processed] = {}
    failed: list[dict] = []
    spool_path = out / ".run_records.spool"
    spool = _Spool(spool_path)
    try:
        for g_done, g_failed in _process_all(_by_instance(entries), flags_of, res, jobs, worker_gib):
            failed += g_failed
            for k, p in g_done.items():
                spool.add(k, p.record_json)
                p.record_json = ""
                done[k] = p
        keys = sorted(done)
        codings = [done[k].coding for k in keys if hasattr(done[k].coding, "primary")]
        skipped = [done[k].coding for k in keys if not hasattr(done[k].coding, "primary")]
        batch = Batch(codings, skipped, {k: done[k].evidence for k in keys})
        _atomic(out / "scored_rows.jsonl", "".join(dumps(dataclasses.asdict(done[k].row)) + "\n" for k in keys))
        _atomic(out / "run_records.jsonl", b"".join(spool.lines()))
        _atomic(out / "run_labels.jsonl", "".join(dumps(done[k].label_row) + "\n" for k in keys))
        _atomic(out / "causes.csv", batch.table().to_csv(index=False))
        _atomic(out / "cause_flags.csv", batch.flags_table().to_csv(index=False))
        _atomic(out / "infra.json", json.dumps(export, indent=1))
        _atomic(out / "none_counts.json", dumps(none_counts(done, keys)) + "\n")
        shutil.rmtree(out / SHEET_DIR, ignore_errors=True)    # the sample of an earlier run in this directory must not stay beside this one's
        sheet_info = write_sheet(batch, out / SHEET_DIR, rows={k: done[k].sheet for k in keys if done[k].sheet},
                                 run_dirs={k: Path(done[k].run_dir) for k in keys if done[k].sheet})
    finally:
        spool.close(spool_path)
    counts_unknown = collections.Counter(r for k in keys if done[k].label == OmissionLabel.UNKNOWN
                                         for r in (done[k].reasons or ["unspecified"]))
    manifest = {
        "format": FORMAT,
        "hashes": {p: tree_hash(p) for p in HASHED},
        "inputs": {"infra_export_sha256": hashlib.sha256((out / "infra.json").read_bytes()).hexdigest()},
        "counts": {
            "runs_seen": len(entries),
            "scored": len(keys),
            "finished": sum(done[k].row.finished for k in keys),
            "labelled": sum(done[k].label != OmissionLabel.UNKNOWN for k in keys),
            "unknown": sum(done[k].label == OmissionLabel.UNKNOWN for k in keys),
            "unknown_by_reason": dict(sorted(counts_unknown.items())),
            "failed": len(failed),
            "failed_by_reason": dict(sorted(collections.Counter(f["reason"] for f in failed).items())),
            "exhausted_runs": len(export["exhausted_runs"]),
            "unfinished_runs": len(export["unfinished_runs"]),
            "platform_evidence_runs": sum(done[k].label_row["platform_evidence"] for k in keys),
            "evidence_not_observed_by_option": _not_observed_counts(done, keys),
            "coded_causes": len(codings),
            "not_coded": batch.skipped_counts(),
            "listing_disagrees_by_option": batch.listing_disagrees_by_option(),
            "listing_evidence_incomplete": batch.listing_evidence_incomplete_count(),
            "tracer_time": tracer_time_counts(done, keys),
            "pilot_code_names_icsa": pilot_icsa_count(done, keys),
            "second_coder": sheet_info,
        },
        "failed": sorted(failed, key=lambda f: (f["block"], f["run_key"])),
    }
    assert manifest["counts"]["runs_seen"] == manifest["counts"]["scored"] + manifest["counts"]["failed"]
    _atomic(out / "manifest.json", dumps(manifest) + "\n")
    return manifest
