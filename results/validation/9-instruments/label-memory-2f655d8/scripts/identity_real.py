"""The old to_units against the new on real byte logs. The old code cannot hold a whole run, so it runs a piece at a time: a file (S1), whose
days no other file holds, or a chunk (S2), a day each; pieces add up exactly. usage: identity_real.py NAME OPTION RUN_OR_LOG INSTANCE KIND [--every N]"""
import json, sys, time, hashlib, importlib.util
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from icsa.instruments import readext as R
from icsa.instruments.crosscheck import gate_reads, file_sizes
from icsa.instruments.fullindex import load_full_index
from icsa.instruments.layout import _merge
from icsa.instances import load as L
spec = importlib.util.spec_from_file_location("tally_tests", "tests/instruments/test_units_tally.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
old_to_units = M.old_to_units
name, log, inst, kind = sys.argv[1:5]
every = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--every=")), 1))
idx = load_full_index()
m = L.load_instances(); rec = next(r for r in m["instances"] if r["instance"]["instance_id"] == inst)
req = L.required_extent(rec, L.load_sea_masks(L.DATA / m["sea_masks"]["file"], m["sea_masks"]["sha256"])[rec["instance"]["region_id"]])
box, base, tgt = req.baseline.box, req.baseline.days, req.target.days
lines = list(R.jsonl(log))
reads = gate_reads(lines, idx.ids, file_sizes(idx))[0] if kind == "gate" else R.proxy_reads(lines)
want = {int(d) for d in base} | {int(d) for d in tgt}
def piece(args):
    r = old_to_units(args, idx, box, base, tgt)
    return {"b": (r.extent.baseline.days, r.extent.baseline.mask), "t": (r.extent.target.days, r.extent.target.mask), "beyond": r.beyond, "beyond_days": r.beyond_days,
            "files": r.files, "bytes_total": r.bytes_total, "bytes_data": r.bytes_data, "unmapped": r.unmapped}
def new_piece(args):
    r = R.to_units(args, idx, box, base, tgt)
    return {"b": (r.extent.baseline.days, r.extent.baseline.mask), "t": (r.extent.target.days, r.extent.target.mask), "beyond": r.beyond, "beyond_days": r.beyond_days,
            "files": r.files, "bytes_total": r.bytes_total, "bytes_data": r.bytes_data, "unmapped": r.unmapped}
def split():
    """(piece ByteReads, compare byte totals?)"""
    out = []
    for p in sorted(set(reads.ranges) | reads.whole_files):
        fl = idx.get(p)
        if fl is None or fl.days.size == 1:
            out.append(R.ByteReads(ranges={p: list(reads.ranges[p])} if p in reads.ranges else {}, whole_files={p} if p in reads.whole_files else set()))
            continue
        rs = list(reads.ranges.get(p, ())) + ([(0, fl.size)] if p in reads.whole_files else [])
        s, e = _merge(rs)
        for t, off, size in zip(fl.chunks[:, 0].tolist(), fl.chunks[:, 3].tolist(), fl.chunks[:, 4].tolist()):
            a, b = np.maximum(s, off), np.minimum(e, off + size)
            keep = b > a
            if keep.any():
                out.append(R.ByteReads(ranges={p: list(zip(a[keep].tolist(), b[keep].tolist()))}))
    return out
def add(acc, r, whole):
    for k in ("b", "t"):
        for d, mk in zip(*r[k]):
            acc[k][int(d)] = acc[k].get(int(d), np.zeros(box.shape, bool)) | mk
    acc["beyond"] += r["beyond"]; acc["beyond_days"] |= set(r["beyond_days"]); acc["files"].add(1)
def same_ext(e, d):
    return e.days.tolist() == sorted(d) and all(np.array_equal(m, d[int(x)]) for x, m in zip(e.days, e.mask))
if __name__ == "__main__":
    t0 = time.time()
    new = R.to_units(reads, idx, box, base, tgt)
    pieces = split()
    print(name, "new whole run:", round(time.time() - t0, 1), "s; pieces", len(pieces), "files", new.files, "beyond", new.beyond, flush=True)
    res = {"name": name, "pieces": len(pieces), "new_beyond": new.beyond, "new_files": new.files}
    with ProcessPoolExecutor(16) as ex:
        # the new code a piece at a time adds up to the new code on the whole run (always all pieces)
        acc = {"b": {}, "t": {}, "beyond": 0, "beyond_days": set(), "files": set()}
        news = []
        for r in ex.map(new_piece, pieces, chunksize=32):
            add(acc, r, True); news.append({k: r[k] for k in ("beyond", "beyond_days", "unmapped")} | {"bd": (r["b"][0].tolist(), hashlib.sha256(r["b"][1].tobytes()).hexdigest()), "td": (r["t"][0].tolist(), hashlib.sha256(r["t"][1].tobytes()).hexdigest())})
        res["new_pieces_add_up"] = bool(same_ext(new.extent.baseline, acc["b"]) and same_ext(new.extent.target, acc["t"]) and acc["beyond"] == new.beyond and
                                        acc["beyond_days"] | {R.day_of_name(p) for p in new.unmapped if R.day_of_name(p) is not None} - want >= set(new.beyond_days) and acc["beyond_days"] <= set(new.beyond_days))
        # the old code on the pieces, each compared to the new code's answer for that piece
        chosen = [k for k in range(len(pieces)) if k % every == 0 or set(news[k]["bd"][0]) | set(news[k]["td"][0])]
        bad = []
        for k, r in zip(chosen, ex.map(piece, [pieces[k] for k in chosen], chunksize=8)):
            got = {"beyond": r["beyond"], "beyond_days": r["beyond_days"], "unmapped": r["unmapped"], "bd": (r["b"][0].tolist(), hashlib.sha256(r["b"][1].tobytes()).hexdigest()), "td": (r["t"][0].tolist(), hashlib.sha256(r["t"][1].tobytes()).hexdigest())}
            if got != news[k]:
                bad.append(k)
        res.update(old_pieces_compared=len(chosen), old_new_differences=len(bad), example=bad[:3], wall_s=round(time.time() - t0, 1))
    print(json.dumps(res), flush=True)
    sys.exit(0 if not bad and res["new_pieces_add_up"] else 1)
