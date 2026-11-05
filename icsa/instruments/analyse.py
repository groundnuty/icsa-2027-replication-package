"""Offline: a run's trace directory -> loaded, analysed and upper-bound extents -> label.

Implements the decision rule of DESIGN.md. Every extent is computed over the
instance's box and its baseline and target days only, as a boolean mask
(day x lat x lon) that becomes an `icsa.extent.PartedExtent` at the end.
"""
from __future__ import annotations

import dataclasses
import json
import re
import shlex
from pathlib import Path

import h5py
import numpy as np

from ..extent import CellBox, Extent, PartedExtent
from ..records import OmissionLabel
from . import config
from .hooks import cf_decoded, content_crc
from . import prov as P
from .layout import LayoutIndex, FileLayout, build_layout
from .tracer import load_prov


class Unmapped(Exception):
    """A provenance term names a file the layout index cannot resolve."""


@dataclasses.dataclass
class Space:
    box: CellBox
    baseline: np.ndarray   # sorted global day indices
    target: np.ndarray

    def __post_init__(self):
        self.baseline = np.unique(np.asarray(list(self.baseline), np.int64))
        self.target = np.unique(np.asarray(list(self.target), np.int64))
        self.days = np.union1d(self.baseline, self.target)

    def empty(self) -> np.ndarray:
        return np.zeros((len(self.days), *self.box.shape), bool)

    def day_ind(self, days) -> np.ndarray:
        ind = np.zeros(len(self.days), bool)
        d = np.asarray(days, np.int64)
        pos = np.searchsorted(self.days, d)
        ok = (pos < len(self.days)) & (self.days[np.minimum(pos, len(self.days) - 1)] == d)
        ind[pos[ok]] = True
        return ind

    def lat_ind(self, lat) -> np.ndarray:
        ind = np.zeros(self.box.shape[0], bool)
        v = np.asarray(lat, np.int64) - self.box.lat0
        ind[v[(v >= 0) & (v < len(ind))]] = True
        return ind

    def lon_ind(self, lon) -> np.ndarray:
        ind = np.zeros(self.box.shape[1], bool)
        v = np.asarray(lon, np.int64) - self.box.lon0
        ind[v[(v >= 0) & (v < len(ind))]] = True
        return ind

    def parted(self, mask: np.ndarray) -> PartedExtent:
        def part(days):
            sel = np.isin(self.days, days)
            m = mask[sel]
            d = self.days[sel]
            keep = m.any(axis=(1, 2))
            return Extent(self.box, d[keep], m[keep])
        return PartedExtent(part(self.baseline), part(self.target))

    def from_parted(self, pe: PartedExtent) -> np.ndarray:
        m = self.empty()
        for e in (pe.baseline, pe.target):
            if e.days.size:
                pos = np.searchsorted(self.days, e.days)
                ok = (pos < len(self.days)) & (self.days[np.minimum(pos, len(self.days) - 1)] == e.days)
                m[pos[ok]] |= e.mask[ok]
        return m


# --------------------------------------------------------------- the trace

@dataclasses.dataclass
class Trace:
    dir: Path
    files: dict[int, dict[int, str]]          # pid -> fid -> identity
    ledger: list[dict]
    sinks: list[dict]
    events: list[dict]
    counts: dict[str, int]
    errors: list[dict] = dataclasses.field(default_factory=list)   # data errors the agent saw (hooks)
    http: list[dict] = dataclasses.field(default_factory=list)     # listing requests (hooks)
    downloads: list[dict] = dataclasses.field(default_factory=list)  # whole-file downloads (hooks)
    sets: dict[str, list] = dataclasses.field(default_factory=dict)  # digest -> a dimension's set in an escape event
    scalars: dict[tuple, set] = dataclasses.field(default_factory=dict)  # (pid, f, t) -> {(j, i)}: floating scalars' escapes
    constant_writes: list = dataclasses.field(default_factory=list)  # (pid, seq, buffer, shape, key, value)


def _jsonl(path: Path):
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    yield {"kind": "corrupt_line"}


def _short_lines(path: Path, stream: str, pid: int, scalars: dict, cwrites: list, counts: dict) -> None:
    """The two streams that a Python loop makes long. A line that does not parse (a torn tail, a full disk)
    is counted, and `torn_trace` keeps the run from being called omitting on what it lost."""
    with open(path) as fh:
        for line in fh:
            try:
                rec = json.loads(line)
                if stream == "scalars":
                    _, f, t, j, i, _dt = rec
                    key = (pid, json.dumps(f), json.dumps(t))
                    scalars.setdefault(key, set()).add((json.dumps(j), json.dumps(i)))
                else:
                    cwrites.append((pid, *rec))
            except (json.JSONDecodeError, ValueError):
                counts["torn_trace"] = counts.get("torn_trace", 0) + 1


def load_trace(trace_dir) -> Trace:
    d = Path(trace_dir)
    files: dict[int, dict[int, str]] = {}
    ledger, sinks, events, errors, http, downloads = [], [], [], [], [], []
    sets: dict[str, list] = {}
    scalars: dict[tuple, set] = {}
    cwrites: list = []
    counts: dict[str, int] = {}
    first_counts: set[str] = set()
    for f in sorted(d.glob("*.jsonl")):
        parts = f.name.split(".")
        if len(parts) != 3 or not parts[1].isdigit():
            counts["foreign_trace_file"] = counts.get("foreign_trace_file", 0) + 1
            continue                      # not a tracer stream (<stream>.<pid>.jsonl)
        stream, pid = parts[0], int(parts[1])
        if stream in ("scalars", "cwrites"):
            _short_lines(f, stream, pid, scalars, cwrites, counts)
            continue
        for rec in _jsonl(f):
            if rec.get("kind") == "corrupt_line":
                # a torn line (a killed process, a full disk): what it held is not known
                counts["torn_trace"] = counts.get("torn_trace", 0) + 1
                continue
            rec["pid"] = pid
            if stream == "files":
                files.setdefault(pid, {})[rec["fid"]] = rec["ident"]
            elif stream == "ledger":
                ledger.append(rec)
            elif stream == "sinks":
                sinks.append(rec)
            elif stream == "errors":
                errors.append(rec)
            elif stream == "http":
                http.append(rec)
            elif stream == "downloads":
                downloads.append(rec)
            elif stream == "events":
                if rec.get("kind") == "counts":
                    for k, v in rec["counts"].items():
                        counts[k] = counts.get(k, 0) + v
                elif rec.get("kind") == "first_count":
                    first_counts.add(rec["key"])    # a process that never reached its final counts still said this
                elif rec.get("kind") == "set":
                    sets[rec["id"]] = rec["rle"]
                else:
                    events.append(rec)
                    if rec.get("kind") == "start" and rec.get("ok_marker") and not (d / f"ok.{pid}").exists():
                        counts["trace_write_failed"] = counts.get("trace_write_failed", 0) + 1
    for k in first_counts:
        counts[k] = max(counts.get(k, 0), 1)
    return Trace(d, files, ledger, sinks, events, counts, errors, http, downloads, sets, scalars, cwrites)


def instrument_loaded(trace_dir) -> dict:
    """Tracer #6: whether the instrument was in place in the run. `ok` needs at least one record, each saying ok, one from
    every process that recorded anything, and no `instrument-error.log` with anything in it. A process that only began to
    install (a helper such as multiprocessing's resource tracker, killed as the run ended) ran no agent code and needs
    none. The harness refuses the same run as invalid; this keeps a label from being read off a trace that says nothing."""
    d = Path(trace_dir)
    recs, bad = {}, 0
    for f in sorted(d.glob("instrument-loaded.*.json")):
        try:
            r = json.loads(f.read_text())
            if type(r.get("ok")) is not bool or not isinstance(r.get("pid"), int):
                raise ValueError
            recs[r["pid"]] = r
        except (OSError, ValueError, AttributeError):
            bad += 1
    log = d / "instrument-error.log"
    error_log = log.exists() and log.stat().st_size > 0
    active: set[int] = set()
    for f in d.glob("*.jsonl"):
        parts = f.name.split(".")
        if len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) in active or int(parts[1]) in recs:
            continue
        if parts[0] != "events" or any(e.get("kind") not in ("start", "listing_hook") for e in _jsonl(f)):
            active.add(int(parts[1]))
    missing = sorted(active)
    failed = sorted(pid for pid, r in recs.items() if not r["ok"])
    return {"ok": bool(recs) and not bad and not error_log and not missing and not failed, "processes": len(recs),
            "unreadable": bad, "error_log": error_log, "without_record": missing, "failed": failed}


def data_errors(records: list[dict]) -> dict:
    """The data errors the agent saw (the `errors` stream, hooks.py), outside its output
    directory, one definition for every option. agent_saw_data_error: any of any origin, except
    those its own request caused (caused_by_agent: a path that does not exist, a refused write,
    HTTP 404 and other client errors), which stay countable. Unparsed: neither errno nor HTTP
    status, kept in the flag. Never a label input."""
    recs = [r for r in records if not r.get("output")]
    path_errors = [r for r in recs if r.get("caused_by_agent") is not True]
    def tally(key):
        out: dict[str, int] = {}
        for r in recs:
            k = str(r.get(key)) if r.get(key) is not None else "null"
            out[k] = out.get(k, 0) + 1
        return out
    return {"records": len(recs), "by_errname": tally("errname"), "by_http_status": tally("http_status"),
            "by_op": tally("op"), "caused_by_agent": len(recs) - len(path_errors),
            "data_path": len(path_errors),
            "unparsed": sum(1 for r in path_errors if r.get("errno") is None and r.get("http_status") is None),
            "agent_saw_data_error": bool(path_errors)}


def tracer_time(trace_dir) -> dict:
    """The tracer's own time, summed over the run's processes (`ttime.<pid>.json`): wall time inside its hooks
    less the calls they wrap, the hook count, and each process's CPU time when last written. `processes` is 0
    when no record exists (a trace from before the counter, or a process that wrote none)."""
    out = {"hook_wall_s": 0.0, "hook_calls": 0, "process_cpu_s": 0.0, "processes": 0, "work": None, "limit": None}
    for f in sorted(Path(trace_dir).glob("ttime.*.json")):
        try:
            r = json.loads(f.read_text().strip())
        except (OSError, ValueError):
            continue
        out["hook_wall_s"] += r.get("hook_wall_ns", 0) / 1e9
        out["hook_calls"] += int(r.get("hook_calls", 0))
        out["process_cpu_s"] += r.get("process_cpu_ns", 0) / 1e9
        out["processes"] += 1
        if "work_parts" in r:                    # amendment 19(b)'s unit: rows produced by merges and products
            out["work"] = (out["work"] or 0) + int(r.get("work", 0))
            out["limit"] = r.get("limit", out["limit"])
    return out


def data_errors_of(trace_dir) -> dict:
    """data_errors() of a run's trace directory, without a layout index or an extent."""
    return data_errors(load_trace(trace_dir).errors)


def resolve_ident(ident: str, index: LayoutIndex) -> FileLayout | None:
    """A trusted identity (path or fsspec path) -> layout; in-memory -> None."""
    kind, _, rest = ident.partition(":")
    if kind == "path":
        return index.get(rest)
    if kind == "fsspec":
        return index.get(rest.partition(":")[2])
    if kind == "sha256":
        # an in-memory source, named by its content: the file with that content and length, or none
        digest, _, length = rest.partition(":")
        rel = index.shas.get(digest)
        fl = index.get(rel) if rel is not None else None
        return fl if fl is not None and str(fl.size) == length else None
    return None


def _fidmaps(tr: Trace, index: LayoutIndex) -> dict[int, dict[int, FileLayout | None]]:
    return {pid: {fid: resolve_ident(ident, index) for fid, ident in fm.items()}
            for pid, fm in tr.files.items()}


# --------------------------------------------------------------- mapping

def _key_indices(key_json, var_shape):
    out = []
    for (kind, v), n in zip(key_json, var_shape):
        if kind == "int":
            out.append(np.array([v], np.int64))
        elif kind == "slice":
            out.append(np.arange(*v, dtype=np.int64))
        else:
            out.append(np.concatenate([np.arange(a, b) for a, b in v]).astype(np.int64)
                       if v else np.empty(0, np.int64))
    return out


def loaded_mask(tr: Trace, index: LayoutIndex, sp: Space) -> tuple[np.ndarray, dict]:
    """L: units materialised by a ledgered call. Returns (mask, info)."""
    maps = _fidmaps(tr, index)
    m = sp.empty()
    info = {"records": len(tr.ledger), "unidentified": 0, "unmapped_files": set()}
    for rec in tr.ledger:
        fl = maps.get(rec["pid"], {}).get(rec["fid"])
        if fl is None:
            info["unidentified"] += 1
            info["unmapped_files"].add(tr.files.get(rec["pid"], {}).get(rec["fid"], "?"))
            continue
        t, j, i = _key_indices(rec["key"], rec["var_shape"])
        if tuple(rec["var_shape"]) != tuple(fl.shape):
            info.setdefault("shape_mismatch", 0)
            info["shape_mismatch"] += 1
            continue
        di = sp.day_ind(fl.days[t])
        yi = sp.lat_ind(fl.lat_idx[j])
        xi = sp.lon_ind(fl.lon_idx[i])
        m |= di[:, None, None] & yi[None, :, None] & xi[None, None, :]
    info["unmapped_files"] = sorted(info["unmapped_files"])
    return m, info


def _term_mask(factors, fmap: dict[int, FileLayout | None], sp: Space) -> np.ndarray:
    """Units of one term (a product of relations over f, t, j, i) as a mask."""
    facs = [(tuple(d), np.asarray(r, np.int64)) for d, r in factors]
    # Join the factors holding f and t: the day needs both.
    fi = next((n for n, (d, _) in enumerate(facs) if "f" in d), None)
    ti = next((n for n, (d, _) in enumerate(facs) if "t" in d), None)
    if fi is None or ti is None:
        raise Unmapped("term without file or time")
    if fi != ti:
        (da, ra), (db, rb) = facs[fi], facs[ti]
        joined = (da + db, P._product([ra, rb]))
        facs = [f for n, f in enumerate(facs) if n not in (fi, ti)] + [joined]
    out = np.ones((len(sp.days), *sp.box.shape), bool)
    for dims, rel in facs:
        cols = {d: rel[:, c] for c, d in enumerate(dims)}
        if "f" in cols:
            fids = np.unique(cols["f"])
            day = np.full(len(rel), -1, np.int64)
            lat = np.full(len(rel), -1, np.int64) if "j" in cols else None
            lon = np.full(len(rel), -1, np.int64) if "i" in cols else None
            for f in fids:
                fl = fmap.get(int(f))
                if fl is None:
                    raise Unmapped(f"file id {int(f)}")
                sel = cols["f"] == f
                tt = cols["t"][sel]
                ok = (tt >= 0) & (tt < len(fl.days))
                dd = np.full(len(tt), -1, np.int64)
                dd[ok] = fl.days[tt[ok]]
                day[sel] = dd
                if lat is not None:
                    lat[sel] = fl.lat_idx[cols["j"][sel]]
                if lon is not None:
                    lon[sel] = fl.lon_idx[cols["i"][sel]]
            ind = _scatter(sp, day, lat, lon)
        else:
            fl = _any_layout(fmap)
            lat = fl.lat_idx[cols["j"]] if "j" in cols else None
            lon = fl.lon_idx[cols["i"]] if "i" in cols else None
            ind = _scatter(sp, None, lat, lon)
        out &= ind
    return out


def _any_layout(fmap) -> FileLayout:
    fls = [fl for fl in fmap.values() if fl is not None]
    if not fls:
        raise Unmapped("no layout for lat/lon")
    ref = fls[0]
    for fl in fls[1:]:
        if not (np.array_equal(fl.lat_idx, ref.lat_idx) and np.array_equal(fl.lon_idx, ref.lon_idx)):
            raise Unmapped("files with different grids in one term")
    return ref


def _scatter(sp: Space, day, lat, lon) -> np.ndarray:
    """Indicator (broadcastable to the full mask) of a relation over some of day/lat/lon."""
    nd, (ny, nx) = len(sp.days), sp.box.shape
    if day is not None and lat is None and lon is None:
        return sp.day_ind(day[day >= 0])[:, None, None]
    if day is None and lat is not None and lon is None:
        return sp.lat_ind(lat)[None, :, None]
    if day is None and lat is None and lon is not None:
        return sp.lon_ind(lon)[None, None, :]
    # Joint relation: keep rows inside the space, then scatter.
    n = len(next(v for v in (day, lat, lon) if v is not None))
    ok = np.ones(n, bool)
    dpos = ypos = xpos = None
    if day is not None:
        dpos = np.searchsorted(sp.days, day)
        ok &= (day >= 0) & (dpos < nd)
        ok &= np.where(ok, sp.days[np.minimum(dpos, nd - 1)] == day, False)
    if lat is not None:
        ypos = lat - sp.box.lat0
        ok &= (ypos >= 0) & (ypos < ny)
    if lon is not None:
        xpos = lon - sp.box.lon0
        ok &= (xpos >= 0) & (xpos < nx)
    shape = (nd if day is not None else 1, ny if lat is not None else 1, nx if lon is not None else 1)
    ind = np.zeros(shape, bool)
    ind[(dpos[ok] if dpos is not None else 0, ypos[ok] if ypos is not None else 0,
         xpos[ok] if xpos is not None else 0)] = True
    return ind


def terms_mask(terms, fmap, sp: Space) -> np.ndarray:
    m = sp.empty()
    for t in terms:
        fs = t.factors()
        if fs:
            m |= _term_mask(fs, fmap, sp)
    return m


def _set_values(ref, table: dict[str, list]) -> np.ndarray:
    """A dimension's set in an escape event: inline run-lengths, or the digest of a written set. A
    digest with no record cannot be mapped (a torn trace): raises Unmapped."""
    if isinstance(ref, str):
        if ref not in table:
            raise Unmapped(f"escape set {ref} has no record")
        ref = table[ref]
    return np.concatenate([np.arange(a, b) for a, b in ref]) if ref else np.empty(0, np.int64)


def escapes_mask(tr: Trace, index: LayoutIndex, sp: Space, kinds=("escape", "observation")) -> tuple[np.ndarray, int]:
    """The union of the events' units. Events sharing a file and day set share their day mask: a
    per-cell loop writes thousands of events that differ only in the cell."""
    maps = _fidmaps(tr, index)
    m = sp.empty()
    unmapped = 0
    groups: dict[tuple, set] = {}
    for ev in tr.events:
        if ev.get("kind") not in kinds:
            continue
        sets = ev.get("sets", {})
        if not all(k in sets for k in ("f", "t", "j", "i")):
            continue
        key = (ev["pid"], json.dumps(sets["f"]), json.dumps(sets["t"]))
        groups.setdefault(key, set()).add((json.dumps(sets["j"]), json.dumps(sets["i"])))
    if "escape" in kinds:
        for key, cells in tr.scalars.items():
            groups.setdefault(key, set()).update(cells)
    for (pid, f_ref, t_ref), cells in groups.items():
        fmap = maps.get(pid, {})
        days, layout = None, None
        cm = np.zeros(sp.box.shape, bool)          # the group's cells, then once onto its days
        for j_ref, i_ref in cells:
            try:
                if days is None:
                    rels = [((d,), _set_values(json.loads(r), tr.sets).reshape(-1, 1)) for d, r in (("f", f_ref), ("t", t_ref))]
                    days = _term_mask(rels, fmap, sp).any(axis=(1, 2))
                    layout = _any_layout(fmap)
                lat = layout.lat_idx[_set_values(json.loads(j_ref), tr.sets)]
                lon = layout.lon_idx[_set_values(json.loads(i_ref), tr.sets)]
                cm |= np.outer(sp.lat_ind(lat), sp.lon_ind(lon))
            except (Unmapped, IndexError):
                unmapped += 1
        if days is not None and cm.any():
            m[days] |= cm
    return m, unmapped


# --------------------------------------------------------------- sinks

@dataclasses.dataclass
class SinkState:
    rel: str
    var: str
    shape: tuple
    prov: P.Prov
    pid: int
    writes: int
    untracked_writes: int
    complex_keys: int
    masked: np.ndarray | None = None     # flat positions stored as fill for masked elements


def _py_key(k):
    if k == "...":
        return Ellipsis
    out = []
    for e in k:
        if e == "...":
            out.append(Ellipsis)
        elif e is None or isinstance(e, int):
            out.append(e)
        elif e[0] == "slice":
            out.append(slice(e[1], e[2], e[3]))
        else:
            raise P._Unsupported
    return tuple(out)


def final_sinks(tr: Trace, output_dir: Path, spec=None) -> tuple[list[SinkState], list[str]]:
    """The provenance of each scientific output variable in its final state."""
    spec = spec or config.sink_spec()
    notes: list[str] = []
    writes: dict[tuple[str, str], list[dict]] = {}
    reread = False
    for ev in sorted(tr.sinks, key=lambda e: (e["t"], e["pid"], e["seq"])):
        rel = ev.get("rel")
        if rel is None:
            continue
        if ev["event"] == "open_w":
            for key in [k for k in writes if k[0] == rel]:
                del writes[key]
        elif ev["event"] == "reread":
            reread = True
        elif ev["event"] in ("write", "write_unrecorded"):
            if reread and rel in spec and ev["var"] in spec[rel] \
                    and "output_reread_then_written" not in notes:
                # Data were read back from an output file (untracked) before this write
                # of the sink: what was read may flow into it unseen. Sticky: the values
                # read stay in memory for the rest of the process.
                notes.append("output_reread_then_written")
            if ev["event"] == "write_unrecorded":
                notes.append(f"sink_write_unrecorded:{rel}:{ev['var']}")
            writes.setdefault((rel, ev["var"]), []).append(ev)
    out = []
    for fname, wanted in spec.items():
        path = Path(output_dir) / fname
        if not path.exists():
            notes.append(f"missing_output:{fname}")
            continue
        try:
            with h5py.File(path, "r") as h:
                names = [n for n, o in h.items() if isinstance(o, h5py.Dataset) and "CLASS" not in o.attrs]
                shapes = {n: h[n].shape for n in names}
                crcs = {}
                for v in wanted:
                    if v in shapes:
                        try:          # the stored values, and the same values CF-decoded
                            raw = h[v][()]
                            crcs[v] = {"raw": content_crc(raw),
                                       "decoded": content_crc(cf_decoded(raw, dict(h[v].attrs)))}
                        except Exception:  # noqa: BLE001
                            crcs[v] = {}
        except OSError:
            notes.append(f"unreadable_output:{fname}")
            continue
        chosen = [v for v in wanted if v in shapes]
        if not chosen:
            # No other variable is guessed: a mask without the protocol's variable is invalid.
            notes.append(f"no_sink_var:{fname}")
            continue
        for var in chosen:
            ws = writes.get((fname, var), [])
            shape = tuple(shapes[var])
            p = P.Prov.none()
            untracked = complex_keys = 0
            pid = ws[-1]["pid"] if ws else -1
            for w in ws:
                if w["pid"] != pid and f"sink_from_several_processes:{fname}:{var}" not in notes:
                    # Each process numbers its files its own way, and the merged provenance is read with the last
                    # writer's table, so one process's file can be credited as another's (b1 #1).
                    notes.append(f"sink_from_several_processes:{fname}:{var}")
                if w["event"] == "write_unrecorded":
                    # the tracer failed to record this write: nothing of the variable is certain
                    p, untracked = P.Prov.none(), untracked + 1
                    continue
                try:
                    vp = load_prov(tr.dir / "prov" / w["prov"]) if w.get("prov") else None
                except (OSError, ValueError, KeyError):
                    # a provenance file that was never written (a failed trace write): nothing certified, and
                    # nothing known about what the write held
                    notes.append(f"sink_prov_missing:{w.get('rel')}:{w.get('var')}")
                    vp = P.Prov.none()
                if vp is None:
                    untracked += 1
                try:
                    key = _py_key(w["key"])
                    p = P.setitem(p, shape, key, vp, tuple(w["value_shape"]))
                except (P._Unsupported, IndexError, ValueError):
                    complex_keys += 1
                    hi = list(p.hi) + (list(vp.hi) if vp is not None else [])
                    p = P.Prov((), P.merge(hi), p.flags | {"lo_dropped"})
            last = ws[-1] if ws else {}
            want = crcs.get(var, {}).get(last.get("mirror_repr", "raw"))
            if ws and (last.get("mirror_crc") is None or last["mirror_crc"] != want):
                # The file does not hold what the recorded writes produced (or the tracer
                # could not mirror them): some write was not seen. Nothing is certain.
                notes.append(f"sink_content_mismatch:{fname}:{var}")
                p = P.Prov((), p.hi, p.flags | {"lo_dropped"})
            masked = None
            if ws and ws[-1].get("masked") is not None:
                runs = ws[-1]["masked"]
                masked = (np.concatenate([np.arange(a, b) for a, b in runs]) if runs
                          else np.empty(0, np.int64))
                if list(ws[-1].get("masked_shape", [])) != list(shape):
                    masked = None
                    notes.append(f"sink_masked_shape:{fname}:{var}")
                    p = P.Prov((), p.hi, p.flags | {"lo_dropped"})
            out.append(SinkState(fname, var, shape, p, pid, len(ws), untracked, complex_keys, masked))
            if not ws:
                notes.append(f"no_sink_write:{fname}:{var}")
    return out, notes


def _masked_in_required(path: Path, var: str, shape, flat: np.ndarray, sp: Space, req_cells) -> bool:
    """Whether any position stored as fill lies on a cell that has a required unit. Fails
    closed: unreadable coordinates count as required."""
    try:
        fl = build_layout(path, path.parent, var=var)
        _, j, i = np.unravel_index(flat, tuple(shape))
        lat = fl.lat_idx[j] - sp.box.lat0
        lon = fl.lon_idx[i] - sp.box.lon0
        inside = (lat >= 0) & (lat < req_cells.shape[0]) & (lon >= 0) & (lon < req_cells.shape[1])
        return bool(req_cells[lat[inside], lon[inside]].any())
    except Exception:  # noqa: BLE001
        return True


def output_units(path: Path, var: str, sp: Space) -> np.ndarray | None:
    """For each element of an output variable shaped (time, lat, lon), whether its coordinates fall in the required space. None,
    which counts every uncovered position as required, if the coordinates cannot be read, or if the file does not say its
    dimensions are in that order: with a square grid the lengths would not show it, and the wrong cell would be judged."""
    try:
        with h5py.File(path, "r") as f:
            scales = [set(d.keys()) for d in f[var].dims]
        if not (len(scales) == 3 and scales[0] == {"time"} and scales[1] & {"lat", "latitude"} and scales[2] & {"lon", "longitude"}):
            return None
        fl = build_layout(path, path.parent, var=var)
        # masks over the output's own axes, in its own order. sp.day_ind and the like are masks over the required space, for other uses.
        di = np.isin(fl.days, sp.days)
        yi = (fl.lat_idx >= sp.box.lat0) & (fl.lat_idx < sp.box.lat1)
        xi = (fl.lon_idx >= sp.box.lon0) & (fl.lon_idx < sp.box.lon1)
        return di[:, None, None] & yi[None, :, None] & xi[None, None, :]
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------- the label

@dataclasses.dataclass
class RunAnalysis:
    label: OmissionLabel
    reasons: list[str]
    coverage: dict[str, float]          # A_lo over required, baseline/target
    coverage_upper: dict[str, float]    # H over required
    coverage_loaded: dict[str, float]
    loaded: PartedExtent
    analysed: PartedExtent              # A_lo
    analysed_upper: PartedExtent        # A_hi
    bound: PartedExtent | None          # H (None: unbounded)
    flags: dict
    notes: list[str]

    def summary(self) -> dict:
        return {"label": self.label.value, "reasons": self.reasons, "coverage": self.coverage,
                "coverage_upper": self.coverage_upper, "coverage_loaded": self.coverage_loaded,
                "flags": self.flags, "notes": self.notes}


def _cov(m: np.ndarray, req: np.ndarray, sp: Space) -> dict[str, float]:
    out = {}
    for name, days in (("baseline", sp.baseline), ("target", sp.target)):
        sel = np.isin(sp.days, days)
        n = int(req[sel].sum())
        out[name] = float((m[sel] & req[sel]).sum() / n) if n else float("nan")
    return out


# Tools that can't carry the data, so a launch of one needs no tracer in it. Anything else with no start is a process the trace
# did not see: `ncdump`, a `python -S`, a copy.
NO_DATA_TOOLS = frozenset({"ls", "pwd", "date", "mkdir", "df", "du", "uname", "nproc", "sleep", "echo", "which"})
_SHELLS = frozenset({"sh", "bash", "dash", "zsh"})
_SHELL_NO_OPS = frozenset({"cd", "true", ":"})     # a shell's own, with no process and nothing read
_SHELL_EXPANSION = re.compile(r"[`$\n]")
_SHELL_PUNCTUATION = frozenset("();<>|&")
_PYTHON = re.compile(r"python[\d.]*")
_ARGV_ITEM_CUT = 200                  # the tracer cuts each argv item to this: such a command line is not all there
_ARGV_ITEMS_CUT = 16


def _shell_commands(line: str) -> list[list[str]] | None:
    """The simple commands of a shell line, joined by `;` or `&&`. None if it needs a shell to read: a pipe, a redirection, an
    expansion, a line cut short. What is left over (a glob, an assignment before a command) fails later, as a program with no
    start or a command line no start has."""
    if len(line) >= _ARGV_ITEM_CUT or _SHELL_EXPANSION.search(line):
        return None
    lex = shlex.shlex(line, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        words = list(lex)
    except ValueError:
        return None
    commands: list[list[str]] = [[]]
    for w in words:
        if w in (";", "&&"):
            commands.append([])
        elif set(w) <= _SHELL_PUNCTUATION:
            return None
        else:
            commands[-1].append(w)
    return [c for c in commands if c]


def _launched_commands(rec: dict) -> list[tuple[str, list[str], bool]] | None:
    """What a launch runs: (program, its command line, through a shell), or None if that cannot be read from the record."""
    argv = [str(a) for a in rec.get("argv") or []]
    event = rec.get("event")
    if event == "pty.spawn":
        return None
    if event == "os.system":
        line = argv[0] if len(argv) == 1 else None
    else:
        tool = Path(str(rec.get("exe") or (argv[0] if argv else ""))).name
        if tool not in _SHELLS:
            return [(tool, argv, False)]
        line = argv[2] if len(argv) == 3 and argv[1] == "-c" else None
    commands = _shell_commands(line) if line is not None else None
    return None if commands is None else [(Path(c[0]).name, c, True) for c in commands]


def _read_launches(d: Path) -> tuple[list[tuple[float, int, dict]], list[str]]:
    """Every launch that ran something, in time order, and the torn records. A program that was not there ran nothing."""
    launches, torn = [], []
    for f in sorted(d.glob("launches.*.jsonl")):
        parts = f.name.split(".")
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        pid = int(parts[1])
        for rec in _jsonl(f):
            if rec.get("kind") == "corrupt_line":
                torn.append(f"launch_record_torn:{pid}")
            elif rec.get("found") is not False:
                launches.append((rec.get("t", float("inf")), pid, rec))
    return sorted(launches, key=lambda x: (x[0], x[1], x[2].get("seq", 0))), torn


def _launch_gaps(d: Path, starts: list[dict]) -> list[str]:
    """A child launched with no start of its own. Each start answers one launch, and only with the same command line: a start at
    t or later with the launcher among its ancestors, or, for `os.exec`, in the launcher itself. Nothing passes through the
    environment, so a scrubbed child still matches; ancestors alone would let a sibling's start, or a start of multiprocessing's
    (which launches with no audit event), answer for a `python -S` or a copy. A program that is not Python has no start to give,
    so a shell that also runs `cat` is a gap though the Python after it started. A process that reappears by `os.exec` keeps its
    pid and its streams, and numbers its files from 0 again: what those streams say of either is not known, so it is a gap too."""
    launches, gaps = _read_launches(d)
    # in time order: the trace lists processes by file name, where pid 100 comes before 99, and with launches in time order the
    # earliest start that fits is the one that leaves every later launch its own
    free = sorted((s for s in starts if s.get("forked_from") is None), key=lambda s: s.get("t", 0))

    def answer(pid: int, t: float, argv: list[str], is_exec: bool) -> bool:
        cut = [a[:_ARGV_ITEM_CUT] for a in argv[:_ARGV_ITEMS_CUT]]
        for i, s in enumerate(free):
            if s.get("t", 0) >= t and (s.get("pid") == pid if is_exec else pid in (s.get("ancestors") or ())) \
                    and s.get("argv", cut) == cut:
                del free[i]
                return True
        return False

    for t, pid, rec in launches:
        event = rec.get("event")
        commands = _launched_commands(rec)
        if commands is None:
            gaps.append(f"launch_without_start:{event}:{Path(str(rec.get('exe') or 'shell')).name}")
            continue
        for program, argv, shell in commands:
            if (program in NO_DATA_TOOLS and not rec.get("out_to_file")) or (shell and program in _SHELL_NO_OPS):
                continue                      # a listed tool whose output went into a file is not exempt (science, #2, 14:59Z)
            if not (_PYTHON.fullmatch(program) and answer(pid, t, argv, event == "os.exec")):
                gaps.append(f"launch_without_start:{event}:{program}")
    by_pid: dict[int, list[dict]] = {}
    for s in starts:
        by_pid.setdefault(s.get("pid"), []).append(s)
    gaps += [f"pid_reused_by_exec:{pid}" for pid, ss in sorted(by_pid.items(), key=lambda x: str(x[0]))
             if any(s.get("forked_from") is None for s in sorted(ss, key=lambda s: s.get("t", 0))[1:])]
    return gaps


def launch_summary(trace_dir) -> dict:
    """How often a run launches anything, for the report: by program, with no argument, so it holds no path or extent."""
    launches, _ = _read_launches(Path(trace_dir))
    programs: dict[str, int] = {}
    for _, _, rec in launches:
        for program, _, _ in _launched_commands(rec) or [("?", [], False)]:
            programs[program] = programs.get(program, 0) + 1
    return {"launches": len(launches), "programs": programs}


def instrument_gaps(tr: Trace, trace_dir, cells_path=None) -> list[str]:
    """What shows that the trace does not cover the whole run (b1 #3): no process said it started, the instrument wrote its
    error log, a process left a stream and no start, a cell the harness launched (`expects_start` in its `cells.jsonl`) has no
    start with that cell's number, or a child the tracer saw launched has no start. An empty trace is then no evidence of an
    empty run. The last two are what see a process that left no stream at all. An older record has no `expects_start`, and is
    not checked; a tracer before the launch records leaves no `launches` stream, and that check finds nothing."""
    d = Path(trace_dir)
    starts = [e for e in tr.events if e.get("kind") == "start"]
    started = {e["pid"] for e in starts}
    gaps = [] if started else ["no_start_record"]
    log = d / "instrument-error.log"
    if log.exists() and log.stat().st_size > 0:
        gaps.append("instrument_error_log")
    streams = {int(f.name.split(".")[1]) for f in d.glob("*.jsonl")
               if len(f.name.split(".")) == 3 and f.name.split(".")[1].isdigit()}
    gaps += [f"process_without_start:{pid}" for pid in sorted(streams - started)]
    if cells_path is not None and Path(cells_path).is_file():
        want = {c["cell"] for c in _jsonl(Path(cells_path)) if c.get("expects_start")}
        gaps += [f"cell_without_start:{c}" for c in sorted(want - {e.get("cell") for e in starts})]
    if tr.counts.get("launch_record_failed"):
        gaps.append("launch_record_failed")
    return gaps + _launch_gaps(d, starts)


def analyse(trace_dir, output_dir, index: LayoutIndex, required: PartedExtent, *, spec=None, cells_path=None) -> RunAnalysis:
    tr = load_trace(trace_dir)
    box = required.baseline.box
    sp = Space(box, required.baseline.days, required.target.days)
    req = sp.from_parted(required)
    L, linfo = loaded_mask(tr, index, sp)
    maps = _fidmaps(tr, index)
    notes: list[str] = []
    flags: dict = {"counts": tr.counts, "ledger": {k: v for k, v in linfo.items()}}
    flags["instrument_loaded"] = loaded_rec = instrument_loaded(trace_dir)
    raw = [e for e in tr.events if e.get("kind") == "flag"]
    flags["raw_decode"] = len(raw)
    escape_log_full = any(e.get("kind") == "escape_log_full" for e in tr.events)
    flags["escape_log_full"] = escape_log_full
    flags["data_errors"] = site_f = data_errors(tr.errors)
    flags["tracer_time"] = tt = tracer_time(trace_dir)
    flags["tracking"] = {"work": tt["work"], "budget": tt["limit"]}
    flags["instrument_gaps"] = gaps = instrument_gaps(tr, trace_dir, cells_path)
    flags["launches"] = launch_summary(trace_dir)
    # False says the record of errors was read and held none, so it needs the whole record: otherwise it is not known
    trace_lost = bool(gaps) or tr.counts.get("trace_write_failed", 0) > 0 or tr.counts.get("torn_trace", 0) > 0
    flags["agent_saw_data_error"] = None if trace_lost and not site_f["agent_saw_data_error"] else site_f["agent_saw_data_error"]
    sinks, snotes = final_sinks(tr, Path(output_dir), spec)
    notes += snotes
    A_lo, A_hi = sp.empty(), sp.empty()
    uncovered = False
    unmapped_terms = 0
    req_cells = req.any(axis=0)                  # (h, w) over the box: cells with a required unit
    masked_in_required = False
    for s in sinks:
        if len(maps) > 1 and s.pid in maps:
            fmap = maps[s.pid]
        else:
            fmap = maps.get(s.pid, {})
        lo_ok = True
        if s.masked is not None and s.masked.size:
            # Elements stored as fill for a masked value carry a constant, not what their
            # provenance says. Harmless only outside the required cells (land, in practice).
            if _masked_in_required(Path(output_dir) / s.rel, s.var, s.shape, s.masked, sp, req_cells):
                lo_ok = False
                masked_in_required = True
                notes.append(f"masked_sink_in_required:{s.rel}:{s.var}")
        for side, acc in (("lo", A_lo), ("hi", A_hi)):
            if side == "lo" and not lo_ok:
                continue
            for t in getattr(s.prov, side):
                try:
                    fs = t.factors()
                    if fs:
                        acc |= _term_mask(fs, fmap, sp)
                except Unmapped:
                    unmapped_terms += 1
        cov = P.covered(s.prov.hi, s.shape)
        if not cov.all():
            where = output_units(Path(output_dir) / s.rel, s.var, sp)
            relevant = (~cov & where).any() if where is not None and where.shape == cov.shape else True
            if relevant:
                uncovered = True
                notes.append(f"uncovered_sink:{s.rel}:{s.var}:{int((~cov).sum())}")
        if s.complex_keys:
            notes.append(f"sink_complex_keys:{s.rel}:{s.var}:{s.complex_keys}")
    E, e_unmapped = escapes_mask(tr, index, sp)
    flags.update({"unmapped_sink_terms": unmapped_terms, "unmapped_escapes": e_unmapped,
                  "uncovered_sink": uncovered, "sinks": len(sinks),
                  # a ledger read from a source with no trusted identity (per option in the dossier, #9 19:29Z)
                  "unidentified_source": linfo["unidentified"] > 0})

    # The upper bound H on what can have reached the outputs.
    write_failed = tr.counts.get("trace_write_failed", 0) > 0
    # Forked workers each start from what their parent had left, so a run can pass the limit with no process stopping: the summed
    # record over the limit counts as a firing (lane-int2's review, T1#4).
    tk = flags.get("tracking") or {}
    budget_hit = tr.counts.get("tracking_budget", 0) > 0 or (tk.get("work") is not None and bool(tk.get("budget")) and tk["work"] > tk["budget"])
    unbounded = bool(gaps) or bool(raw) or write_failed or tr.counts.get("torn_trace", 0) > 0 or linfo["unidentified"] > 0 or linfo.get("shape_mismatch", 0) > 0 \
        or tr.counts.get("netcdf4_init_unpatched", 0) > 0
    # Amendment 26(h): what makes the loaded extent L itself unreliable, because a read can be missing from it (as against provenance lost after a read that
    # was ledgered, which leaves L whole). The coverage upper bound is 1 for such a run and L for any other run not labelled complete
    # (labeller.coverage_upper_bound). The first seven are exactly the cases where H is unbounded above, plus a trace with nothing loaded; `tracer_error` is
    # kept in because an internal error may have dropped a ledger record. The labeller adds the two code-scan reasons.
    flags["read_tracking_lost"] = [code for code, hit in (
        ("instrument_not_loaded", not loaded_rec["ok"]), ("instrument_missing", bool(gaps)), ("unledgered_access", bool(raw)),
        ("trace_write_failed", write_failed), ("torn_trace", tr.counts.get("torn_trace", 0) > 0), ("unidentified_source", linfo["unidentified"] > 0),
        ("ledger_shape_mismatch", linfo.get("shape_mismatch", 0) > 0), ("netcdf4_init_unpatched", tr.counts.get("netcdf4_init_unpatched", 0) > 0),
        ("tracer_error", tr.counts.get("internal_error", 0) > 0)) if hit]
    provenance_lost = (uncovered or not sinks or unmapped_terms > 0 or e_unmapped > 0
                       or masked_in_required or escape_log_full or tr.counts.get("torn_trace", 0) > 0
                       or "output_reread_then_written" in notes
                       or any(n.startswith("sink_content_mismatch") for n in notes)
                       or tr.counts.get("internal_error", 0) > 0
                       or tr.counts.get("untagged_materialisation", 0) > 0
                       or tr.counts.get("ledger_shape_mismatch", 0) > 0
                       # new strides on a tracked buffer: its elements' provenance is unknown
                       or tr.counts.get("view_remapped", 0) > 0
                       # tracked data met a plain array, which can hold tracked values no provenance names
                       or tr.counts.get("plain_operand", 0) > 0
                       # the run spent its work budget: nothing computed after that point carries provenance
                       or budget_hit)
    if unbounded:
        H = None
    elif provenance_lost:
        H = L.copy()
    else:
        H = (A_hi | E) & L
    reasons: list[str] = []
    gap = req & ~A_lo
    several = any(n.startswith("sink_from_several_processes") for n in notes)
    if not loaded_rec["ok"]:
        # Nothing was recorded, or only part of it: a label would be read off what was never seen.
        return RunAnalysis(
            label=OmissionLabel.UNKNOWN, reasons=["instrument_not_loaded"],
            coverage=_cov(A_lo, req, sp), coverage_upper=_cov(np.ones_like(req), req, sp),
            coverage_loaded=_cov(L, req, sp), loaded=sp.parted(L), analysed=sp.parted(A_lo),
            analysed_upper=sp.parted(A_hi), bound=None, flags=flags, notes=notes)
    # A raw buffer of a tracked array was handed out (ndarray.data, frombuffer over it):
    # writes through it, at any later time, are invisible. Fail closed: never complete.
    raw_buffer = tr.counts.get("raw_buffer", 0) > 0
    if gaps:
        # what the run read or used is not known, so an empty extent is no omission
        label = OmissionLabel.UNKNOWN
        reasons.append("instrument_missing")
    elif several:
        # no definite label on a provenance that may name the wrong files, whichever way it points
        label = OmissionLabel.UNKNOWN
        reasons.append("sink_from_several_processes")
    elif not gap.any() and sinks and unmapped_terms == 0 and not raw_buffer and not write_failed \
            and not tr.counts.get("torn_trace", 0) and not budget_hit \
            and not any(n.startswith("sink_prov_missing") for n in notes):
        label = OmissionLabel.COMPLETE
    elif H is not None and (req & ~H).any():
        label = OmissionLabel.OMITTING
        reasons.append("not_loaded" if (req & ~L).any() else "loaded_not_used")
        if budget_hit:
            reasons.append("tracking_budget")      # a firing is on record whatever the label
    else:
        label = OmissionLabel.UNKNOWN
        if write_failed:
            reasons.append("trace_write_failed")
        if H is None and (raw or not write_failed or linfo["unidentified"]):
            reasons.append("unledgered_access" if raw else "unidentified_source")
        if any(str(i).startswith("modified:") for i in linfo["unmapped_files"]):
            reasons.append("modified_local_file")
        if provenance_lost:
            reasons += [r for r, c in (("uncovered_sink", uncovered), ("no_sink", not sinks),
                                       ("output_reread", "output_reread_then_written" in notes),
                                       ("masked_sink_in_required", masked_in_required),
                                       ("escape_log_full", escape_log_full),
                                       ("torn_trace", tr.counts.get("torn_trace", 0)),
                                       ("sink_content_mismatch",
                                        any(n.startswith("sink_content_mismatch") for n in notes)),
                                       ("unmapped", unmapped_terms or e_unmapped),
                                       ("tracer_error", tr.counts.get("internal_error", 0)),
                                       ("untagged_materialisation", tr.counts.get("untagged_materialisation", 0)),
                                       ("plain_operand", tr.counts.get("plain_operand", 0)),
                                       ("tracking_budget", budget_hit))
                        if c]
        if raw_buffer:
            reasons.append("raw_buffer_or_introspection")
        if (gap & A_hi).any():
            reasons.append("unmodelled_op")
        Eesc, _ = escapes_mask(tr, index, sp, kinds=("escape",))
        Eobs, _ = escapes_mask(tr, index, sp, kinds=("observation",))
        if (gap & Eesc).any():
            reasons.append("escape")
        if (gap & Eobs).any():
            reasons.append("observation")
    return RunAnalysis(
        label=label, reasons=reasons,
        coverage=_cov(A_lo, req, sp),
        coverage_upper=_cov(H if H is not None else np.ones_like(req), req, sp),
        coverage_loaded=_cov(L, req, sp),
        loaded=sp.parted(L), analysed=sp.parted(A_lo), analysed_upper=sp.parted(A_hi),
        bound=sp.parted(H) if H is not None else None, flags=flags, notes=notes)
