"""The per-run labeller (#9): one call per run, its result feeds scoring (#13).

    lab = label_run(option, trace_dir, output_dir, index, required, platform_dir=...)
    score_run(record, run_dir, ref, lab.analysed, lab.label, ...)

`lab.label` and `lab.analysed` (A_lo) come from the in-process traces only,
identically in every option (DESIGN.md, "The decision rule"). So do, on every
run, `lab.read` (values decoded by a data library, from the ledger, plus D's
download records) and `lab.listing` (T, T-unpaginated, D: from the listing
stream, requests.Session.send). They feed cause codes, never the label.

The logs give the outside view, also never the label: `lab.fetched`, `lab.delivered`
and `flags["cross_check"]` (crosscheck.py). A log that is absent yields None
("not observed"), never an empty extent or an agreement. In `platform_dir`:
- `gate_requests.jsonl` T, T-unpaginated, D: the gate's log (the sandbox's `collect`);
- `oneclient_perf/*.csv` M, M+: oneclient's performance log, when it is on;
- `proxy.jsonl`        the local path: the local server's log, with listing fields;
- `fuse.jsonl`         M, M+: FUSE operations (op, path, offset, bytes), if provided;
- `remote.jsonl`       M, M+: the oneclient's remote reads (path, offset, size), if provided;
- `localread.jsonl`    D: reads of downloaded files (op, path, offset, bytes), or
- `strace.txt`         D, M on the local path: `strace -f -y` of the agent's processes.
"""
from __future__ import annotations

import ast
import dataclasses
import json
import re
from pathlib import Path

import numpy as np

from ..extent import PartedExtent
from ..records import OmissionLabel
from . import readext as R
from .crosscheck import cross_check, file_sizes, gate_reads
from .analyse import RunAnalysis, _fidmaps, _key_indices, analyse, load_trace
from .layout import LayoutIndex
from .listing import DirListing, listing_from_http

REST_OPTIONS = ("T", "T-unpaginated", "D")
MOUNT_OPTIONS = ("M", "M+")

# The instrument's guarantee (no omitting run labelled complete) comes from fail-closed
# scope, not from out-tracking every Python trick: agent code for this task has no
# legitimate need for raw buffers or for introspection of live objects, so a run whose
# code uses any of these constructs is unknown (reason raw_buffer_or_introspection).
#
# Two deliberate carve-outs. `.data` is not listed: a regex cannot tell an array from an
# xarray DataArray, and da.data is idiomatic; ndarray.data is rejected at run time instead
# (tracer.TArray.data), for arrays only. stride_tricks is not listed as a whole: its
# sliding_window_view is a natural way to code the +-5-day pooling and 31-day smoothing,
# and it is read-only and modelled; as_strided and writeable views are listed.
BYPASS_PATTERNS = {
    # buffers
    "memoryview": re.compile(r"\bmemoryview\b"),
    "raw_buffer": re.compile(r"\.cast\s*\(\s*['\"]|__buffer__|\bndarray\.data\b"),
    "frombuffer": re.compile(r"\bfrombuffer\b"),
    "buffer_info": re.compile(r"\bbuffer_info\b"),
    "ctypes": re.compile(r"\bctypes\b"),
    "array_interface": re.compile(r"__array_interface__|__array_struct__"),
    # views that can be written through
    "as_strided": re.compile(r"\bas_strided\b"),
    "nditer_write": re.compile(r"\bnditer\b[^\n]*(?:readwrite|writeonly)"),
    "writeable_view": re.compile(r"\bwriteable\s*=\s*True\b|\.writeable\s*=|\bsetflags\s*\("),
    # new strides remap a view onto any part of its buffer (deprecated in numpy 2.4)
    "strides_assignment": re.compile(r"\.strides\s*=(?!=)"),
    # writes below the array type
    "unbound_ndarray_method": re.compile(r"\bndarray\.(?!__name__|__doc__)\w+\s*\("),
    # the base class under another name (an import alias or an assignment)
    "ndarray_alias": re.compile(r"\bimport\b[^\n]*\bndarray\s+as\b|=\s*(?:np|numpy)\.ndarray\s*(?:$|[;#\n])",
                               re.M),
    "dataset_id_write": re.compile(r"\.id\.write\s*\(|\bh5py\.h5d\b"),
    # introspection of live objects
    "profile_trace_hooks": re.compile(r"\b(?:sys|threading)\.(?:setprofile|settrace)(?:_all_threads)?\b"
                                      r"|\bsys\.monitoring\b"),
    "gc_introspection": re.compile(r"\bgc\.get_(?:referents|referrers|objects)\b"),
    "instance_dict": re.compile(r"__dict__|\bvars\s*\("),
    "object_attribute": re.compile(r"\bobject\.__(?:setattr|getattribute|delattr)__\b"),
    # ufunc.at writes its first argument in place (out= of the other ufunc methods: the
    # AST check below, which sees multiline calls and positional outputs)
    "ufunc_method_write": re.compile(r"\.at\s*\("),
    # code loaded at interpreter start (the sandbox's user site directory is writable, #9
    # finding 1 Nov; tests/sandbox/test_site_packages.py)
    "startup_code": re.compile(r"\b(?:usercustomize|sitecustomize)\b|\.pth\b|\bPYTHONSTARTUP\b"),
    # rebinding names of the data libraries at run time (np.ma.MaskedArray = ...)
    "library_patching": re.compile(
        r"\b(?:np|numpy|h5py|netCDF4|xr|xarray|h5netcdf)(?:\.\w+)+\s*=(?!=)"
        r"|\bsetattr\s*\(\s*(?:np|numpy|h5py|netCDF4|xr|xarray|h5netcdf)\b"),
    # code that reaches into the tracer or the array machinery it relies on
    "tracer_tampering": re.compile(
        r"\bicsa\.instruments\.(?:tracer|hooks|prov)\b"
        r"|\bfrom\s+icsa\.instruments\s+import\b[^\n]*\b(?:tracer|hooks|prov)\b"
        r"|\._p\b|['\"]_p['\"]|\b_baseclass\b|__array_finalize__"),
}
REJECTED_REASON = "raw_buffer_or_introspection"


# ufunc methods that write a destination with no Python-level call when the destination is
# a masked array; the position of `out` among their positional parameters
_UFUNC_OUT_POS = {"reduce": 3, "accumulate": 3, "reduceat": 4, "outer": None}
_UFUNC_METHOD_CALL = re.compile(r"\.(?:reduce|accumulate|reduceat|outer)\s*\(")


def _cell_ufunc_out_writes(cell: str) -> bool | None:
    """Whether one code cell calls a ufunc method (reduce, accumulate, reduceat, outer)
    with an output: an `out` keyword, a positional output, or */** arguments that could
    carry one. None if the cell does not parse."""
    try:
        tree = ast.parse(cell)
    except (SyntaxError, ValueError):
        return None
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        # captured as a value (a name bound to it, an argument, functools.partial): its
        # later calls cannot be checked, so it is rejected
        if isinstance(node, ast.Attribute) and node.attr in _UFUNC_OUT_POS and id(node) not in called:
            return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr"
                and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in tuple(_UFUNC_OUT_POS) + ("at",)):
            return True
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in _UFUNC_OUT_POS):
            continue
        if any(k.arg == "out" or k.arg is None for k in node.keywords):
            return True
        pos = _UFUNC_OUT_POS[node.func.attr]
        if pos is not None and (len(node.args) > pos or any(isinstance(a, ast.Starred) for a in node.args)):
            return True
    return False


def _ufunc_out_writes(cells: list[str]) -> bool:
    """Per cell, with the AST. A cell that does not parse never ran (Python raises before
    executing any of it) and is skipped; but text that is not split into cells and does
    not parse as a whole fails closed on any ufunc-method call."""
    if len(cells) == 1:
        got = _cell_ufunc_out_writes(cells[0])
        return bool(_UFUNC_METHOD_CALL.search(cells[0])) if got is None else got
    return any(_cell_ufunc_out_writes(c) for c in cells)


def bypass_scan(code) -> list[str]:
    """Names of the bypass constructs present in the agent's code: the cells it ran (a list,
    as `code_cells_of` returns), or one text."""
    cells = [code] if isinstance(code, str) else [str(c) for c in (code or [])]
    text = "\n".join(cells)
    hits = {k for k, rx in BYPASS_PATTERNS.items() if rx.search(text)}
    if _ufunc_out_writes(cells or [""]):
        hits.add("ufunc_method_write")
    return sorted(hits)


def code_cells_of(code_cells_path) -> list[str]:
    """The code cells the agent ran, from the harness's code-cell log (#8 writes
    `code_cells.json`, a JSON list of {"code", "exit_code", "duration_s"}); JSON lines with a
    `code` or `source` field, or plain text (one cell), are read too."""
    p = Path(code_cells_path)
    if not p.is_file():
        raise FileNotFoundError(f"code-cell log not found: {p}")
    text = p.read_text(errors="replace")

    def cell(x):
        if isinstance(x, dict):
            return str(x.get("code", x.get("source", "")))
        return str(x)
    try:
        data = json.loads(text)
        return [cell(x) for x in data] if isinstance(data, list) else [cell(data)]
    except ValueError:
        pass
    out, lines = [], text.splitlines()
    try:
        out = [cell(json.loads(line)) for line in lines if line.strip()]
    except ValueError:
        out = [text]
    return out


def code_text_of(code_cells_path) -> str:
    """All code the agent ran, as one text (prefer `code_cells_of` for label_run)."""
    return "\n".join(code_cells_of(code_cells_path))


@dataclasses.dataclass
class RunLabel:
    option: str
    analysis: RunAnalysis
    fetched: R.ReadExtent | None        # None: not observed for this option or run
    read: R.ReadExtent | None
    listing: dict[str, DirListing] | None
    observed: dict[str, str]            # which trace gave each of fetched / delivered / read / listing
    delivered: R.ReadExtent | None = None  # bytes delivered to the process, from the logs

    # ---- what scoring takes
    @property
    def label(self) -> OmissionLabel:
        return self.analysis.label

    @property
    def analysed(self) -> PartedExtent:
        return self.analysis.analysed

    @property
    def reasons(self) -> list[str]:
        return self.analysis.reasons

    def summary(self) -> dict:
        def ext(e: R.ReadExtent | None):
            if e is None:
                return None
            return {"units_baseline": int(e.extent.baseline.count()), "units_target": int(e.extent.target.count()),
                    "files": e.files, "bytes_total": e.bytes_total, "bytes_data": e.bytes_data,
                    "unmapped_bytes": sum(e.unmapped.values()), "beyond_units": e.beyond,
                    "beyond_days": e.beyond_days}
        out = self.analysis.summary()
        out.update({"option": self.option, "fetched": ext(self.fetched), "delivered": ext(self.delivered),
                    "read": ext(self.read),
                    "listing": None if self.listing is None else {k: v.to_json() for k, v in self.listing.items()},
                    "observed": self.observed})
        return out


def ledger_read(tr, index: LayoutIndex, loaded: PartedExtent, baseline_days, target_days
                ) -> tuple[R.ReadExtent | None, dict[str, set[int]]]:
    """What the run read, on every option: values a data library decoded (the ledger), plus D's
    whole-file downloads for the days. Also the time indices decoded per file, for the
    cross-check. None if the tracer did not run: not observed, never empty. A header-only read
    decodes nothing, so it is not a read; bytes delivered come only from the logs."""
    if not any(e.get("kind") == "start" for e in tr.events):
        return None, {}
    maps = _fidmaps(tr, index)
    required = {int(d) for d in baseline_days} | {int(d) for d in target_days}
    box = loaded.baseline.box
    decoded: dict[str, set[int]] = {}
    unmapped: dict[str, int] = {}
    named: set[int] = set()
    s1_days: set[int] = set()                         # days of one-day files (S1) the run decoded
    sels: dict[tuple[bytes, bytes], int] = {}       # one (rows, columns) selection, however many days
    arrays: list[tuple[np.ndarray, np.ndarray]] = []
    day_sels: dict[int, set[int]] = {}
    for rec in tr.ledger:
        fl = maps.get(rec["pid"], {}).get(rec["fid"])
        if fl is None:
            ident = tr.files.get(rec["pid"], {}).get(rec["fid"], "?")
            unmapped[ident] = 0
            d = R.day_of_name(ident.rsplit(":", 1)[-1])
            if d is not None:
                named.add(d)
            continue
        if tuple(rec["var_shape"]) != tuple(fl.shape):
            continue
        t, j, i = _key_indices(rec["key"], rec["var_shape"])
        if not (t.size and j.size and i.size):
            continue                                # an empty selection reads nothing
        decoded.setdefault(fl.relpath, set()).update(int(x) for x in t)
        lat, lon = np.unique(fl.lat_idx[j]), np.unique(fl.lon_idx[i])
        key = (lat.tobytes(), lon.tobytes())
        if key not in sels:
            sels[key] = len(arrays)
            arrays.append((lat, lon))
        for d in fl.days[t]:
            day_sels.setdefault(int(d), set()).add(sels[key])
        if fl.days.size == 1:
            s1_days.add(int(fl.days[0]))
    counted: dict[frozenset, tuple[int, int]] = {}   # the union of some selections: units, units in the box
    beyond = 0
    for d, ks in day_sels.items():
        fk = frozenset(ks)
        if fk not in counted:
            la = np.unique(np.concatenate([arrays[k][0] for k in fk]))
            lo = np.unique(np.concatenate([arrays[k][1] for k in fk]))
            m = np.zeros((la.size, lo.size), bool)
            for k in fk:
                m[np.ix_(np.searchsorted(la, arrays[k][0]), np.searchsorted(lo, arrays[k][1]))] = True
            inside = m[np.ix_((la >= box.lat0) & (la < box.lat1), (lo >= box.lon0) & (lo < box.lon1))]
            counted[fk] = (int(m.sum()), int(inside.sum()))
        total, in_box = counted[fk]
        beyond += total if d not in required else total - in_box
    # read_beyond_days (science, #9 19:52Z, amendment 2): evidence that the run knew names past a listing, so
    # decoded or delivered by its own choice: S1 days it decoded, or named files it reached, and D's downloads
    # by name. S2's one file is always listed, so nothing in S2 is ever beyond: its decodes add none.
    # (T's fetches are added in label_run, from the logs.) `read` itself stays what was decoded.
    downloaded = {R.day_of_name(str(r.get("rpath", ""))) for r in tr.downloads} - {None}
    beyond_days = sorted((s1_days | named | downloaded) - required)
    return R.ReadExtent(loaded, len(decoded), None, None, unmapped, beyond, beyond_days, source="ledger",
                        downloaded_days=sorted(downloaded),
                        other_days=sorted(set(day_sels) - required)), decoded


def _download_map(trace_dir: Path) -> dict[str, str]:
    """Local path of each downloaded copy -> remote path, from the tracer's download records."""
    out = {}
    for f in sorted(Path(trace_dir).glob("downloads.*.jsonl")):
        for rec in R.jsonl(f, torn_ok=True):
            if rec.get("lpath") and rec.get("rpath"):
                out[rec["lpath"]] = rec["rpath"]
    return out


def _s1_days_delivered(reads: R.ByteReads, index: LayoutIndex) -> set[int]:
    """Days of the one-day files (S1) a log delivered any bytes of."""
    out = set()
    for p in set(reads.ranges) | set(reads.whole_files):
        if not (p in reads.whole_files or any(b > a for a, b in reads.ranges.get(p, ()))):
            continue
        fl = index.get(p)
        if fl is None:
            d = R.day_of_name(str(p))            # a file the index does not hold: its day by name (S1 names only)
            if d is not None:
                out.add(int(d))
        elif fl.days.size == 1:
            out.add(int(fl.days[0]))
    return out


def label_run(option: str, trace_dir, output_dir, index: LayoutIndex, required: PartedExtent, *,
              platform_dir=None, local_roots=(), dir_sizes: dict[str, int] | None = None,
              code_text: str | list[str] | None = None) -> RunLabel:
    """Label one run. `local_roots`: directories whose local reads count as reads of
    dataset files (D: the scratch download dir; M under strace: the mount root).
    `code_text`: the code the agent ran, preferably its cells (`code_cells_of(record.code_cells_path)`). If it
    uses a rejected construct the run is unknown, whatever the traces say (the traces
    cannot be trusted either way). Fail closed: without the code (None) a run is never
    certified complete (reason code_not_scanned)."""
    an = analyse(trace_dir, output_dir, index, required,
                 cells_path=Path(platform_dir) / "cells" / "cells.jsonl" if platform_dir is not None else None)
    lost = an.flags.setdefault("read_tracking_lost", [])         # amendment 26(h); analyse.py names the trace-side causes
    if code_text is None:
        lost.append("code_not_scanned")                           # no code, so no telling whether a read went round the hooks
        an.notes.append("code_not_scanned")
        if an.label == OmissionLabel.COMPLETE:
            an.label = OmissionLabel.UNKNOWN
            an.reasons.append("code_not_scanned")
    else:
        hits = bypass_scan(code_text)
        an.flags["bypass_scan"] = hits
        if hits:
            if an.label != OmissionLabel.UNKNOWN:
                an.notes.append(f"label_from_traces_alone:{an.label.value}")
            an.label = OmissionLabel.UNKNOWN
            if REJECTED_REASON not in an.reasons:
                an.reasons.append(REJECTED_REASON)
            lost.append(REJECTED_REASON)                          # "the traces cannot be trusted either way": nor the loaded extent
    box = required.baseline.box
    base, tgt = required.baseline.days, required.target.days
    pd = Path(platform_dir) if platform_dir is not None else None
    fetched = delivered = None
    observed: dict[str, str] = {}
    tr = load_trace(trace_dir)

    # What the run decoded and listed: the tracer, the same in every option.
    read, decoded = ledger_read(tr, index, an.loaded, base, tgt)
    if read is not None:
        observed["read"] = "ledger"
    listing = None
    if option in REST_OPTIONS and any(e.get("kind") == "listing_hook" for e in tr.events):
        listing = listing_from_http(tr.http, getattr(index, "ids", None), dir_sizes)
        observed["listing"] = "session_send"

    # What the logs delivered: descriptive, and the outside view of the cross-check.
    def has(name):
        return pd is not None and (pd / name).is_file()

    gate_lines = list(R.jsonl(pd / "gate_requests.jsonl")) if has("gate_requests.jsonl") else None
    fetched_reads = None
    if option in REST_OPTIONS and has("proxy.jsonl"):
        fetched_reads = R.proxy_reads(R.jsonl(pd / "proxy.jsonl"))
        observed["fetched"] = "proxy.jsonl"
    elif option in REST_OPTIONS and gate_lines is not None:
        fetched_reads = gate_reads(gate_lines, getattr(index, "ids", None), file_sizes(index))[0]
        observed["fetched"] = "gate_requests.jsonl"
    if fetched_reads is not None:
        fetched = R.to_units(fetched_reads, index, box, base, tgt)
        if option != "D" and read is not None:
            # a T fetch of an S1 file is the run reaching that name (amendment 2), decoded or not
            known = _s1_days_delivered(fetched_reads, index)
            req_days = {int(d) for d in base} | {int(d) for d in tgt}
            read = dataclasses.replace(read, beyond_days=sorted(set(read.beyond_days) | (known - req_days)))
    if option in REST_OPTIONS and option != "D" and fetched is not None:
        delivered = fetched                   # range reads are delivered to the process as fetched
        observed["delivered"] = observed["fetched"]
    strace_reads = None
    if option == "D" or option in MOUNT_OPTIONS:
        dmap = _download_map(trace_dir) if option == "D" else {}
        pm = (lambda p: dmap.get(p, p))
        if option in MOUNT_OPTIONS and has("fuse.jsonl"):
            delivered = R.to_units(R.fuse_reads(R.jsonl(pd / "fuse.jsonl")), index, box, base, tgt)
            observed["delivered"] = "fuse.jsonl"
        elif option == "D" and has("localread.jsonl"):
            delivered = R.to_units(R.fuse_reads(R.jsonl(pd / "localread.jsonl")), index, box, base, tgt, path_map=pm)
            observed["delivered"] = "localread.jsonl"
        elif has("strace.txt") and local_roots:
            strace_reads = R.strace_reads((pd / "strace.txt").read_text(errors="replace"),
                                          roots=[str(r) for r in local_roots])
            delivered = R.to_units(strace_reads, index, box, base, tgt, path_map=pm)
            observed["delivered"] = "strace.txt"
        if option in MOUNT_OPTIONS and has("remote.jsonl"):
            rem = R.ByteReads()
            for e in R.jsonl(pd / "remote.jsonl"):
                rem.add(e["path"], e["offset"], e["offset"] + e["size"])
            fetched = R.to_units(rem, index, box, base, tgt)
            observed["fetched"] = "remote.jsonl"
    perf = sorted((pd / "oneclient_perf").glob("read_write_perf-*.csv")) if pd is not None else None
    cc = cross_check(option, an.label.value, decoded=decoded, index=index, gate_lines=gate_lines, perf_csvs=perf,
                     local_reads=strace_reads, http_lines=tr.http)
    an.flags["cross_check"] = cc
    for k in ("listing_disagrees", "decoded_not_delivered", "delivered_not_decoded"):
        an.flags[k] = cc[k]
    route_loaded_not_used(an)
    return RunLabel(option, an, fetched, read, listing, observed, delivered)


def route_loaded_not_used(an: RunAnalysis) -> None:
    """Amendment 19(a): an `omitting` whose only cause is data loaded but not analysed goes to inspection as `unknown`; tracking lost
    through a plain array can produce exactly that label. An omission of data never loaded stays definite. The label before this
    route is kept, on every run, for the instrument-only sensitivity."""
    an.flags["raw_label"] = an.label.value
    if an.label == OmissionLabel.OMITTING and "loaded_not_used" in an.reasons and "not_loaded" not in an.reasons:
        an.label = OmissionLabel.UNKNOWN
        an.notes.append("inspection:loaded_not_used")


def coverage_upper_bound(an: RunAnalysis) -> dict[str, float]:
    """The coverage upper bound that scoring carries (amendment 26(h), changing 19(f)): 1 for a run with lost read tracking (`flags["read_tracking_lost"]`,
    such as an unmatched child process), and the loaded extent for every other run not labelled `complete`; it can't fall below true coverage, where the tight
    bound H could (a selection that selects nothing leaves its units out of H). An instrument-labelled `complete` keeps its own. A run resolved complete by
    the coders is 1 as well, known only after inspection: icsa.analysis.adapter. Never below the lower value."""
    if an.label is OmissionLabel.COMPLETE:
        return dict(an.coverage_upper)
    if an.flags.get("read_tracking_lost"):
        return {"baseline": 1.0, "target": 1.0}
    return {k: float(max(an.coverage_loaded[k], an.coverage[k])) if an.coverage_loaded[k] == an.coverage_loaded[k] else an.coverage_loaded[k]
            for k in ("baseline", "target")}


def write_summary(lab: RunLabel, path) -> None:
    Path(path).write_text(json.dumps(lab.summary(), indent=1, sort_keys=True, default=str))
