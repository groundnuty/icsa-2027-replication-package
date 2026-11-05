"""Pack the BALarea cells of the S1 record (202506) into one file for the whole-domain Octave run (item 9).

    python3 pack_domain.py <dataset.tar> <dataset.manifest.sha256> <out dir> [--workers K] [--days a:b]

Reads the daily S1 files straight from the master-copy tar (`s1z/sst_YYYYMMDD.nc`, deflate-lossless of S1), checks
each file's sha256 against the manifest, reads `analysed_sst` exactly as `icsa.refdet.data._read_var` does (masked
values to NaN, float32), and keeps the cells of the authors' mask (`data._full_sea_mask()`, = finite BALarea,
170,171 cells) in the authors' Step_1 order: the product's (lon, lat) layout flattened with lon fastest, i.e. lat-major
here. Output (written in place by `--workers` processes, each owning a block of days):

    packed.f32   float32, (T, N) C order = day-major: row d holds the N sea cells of day d
    cells.i32    int32 (N, 2): lat index, lon index of each packed cell
    pack.json    record: N, T, mask sha256, tar sha256 line, per-file manifest hash check, sha256 of packed.f32 (--seal)

The authors' Step_1 reshapes the N sea cells to n x m with n the largest prime factor of N (170171 = 379 x 449, so
449 x 379); `shard_input.py` cuts the packed file into whole columns of that layout.
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import tarfile
import time
from pathlib import Path

import netCDF4
import numpy as np

from icsa import grid
from icsa.extent import CellBox
from icsa.refdet import data

FULL = CellBox(0, grid.NLAT, 0, grid.NLON)


def sha256_file(p, bufsize=1 << 24):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_manifest(p):
    out = {}
    for line in Path(p).read_text().splitlines():
        h, _, name = line.partition("  ")
        out[name] = h
    return out


def work(args):
    tar_path, manifest, out_dir, d0, d1, T, N, flat = args
    mm = np.memmap(Path(out_dir) / "packed.f32", dtype=np.float32, mode="r+", shape=(T, N))
    tf = tarfile.open(tar_path, "r:")
    idx = {m.name: m for m in tf.getmembers() if m.name.startswith("s1z/")}
    bad = []
    for d in range(d0, d1):
        name = f"s1z/sst_{grid.day_date(d):%Y%m%d}.nc"
        m = idx[name]
        b = tf.extractfile(m).read()
        if hashlib.sha256(b).hexdigest() != manifest[name]:
            bad.append(name)
        ds = netCDF4.Dataset("mem.nc", mode="r", memory=b)
        a = data._read_var(ds, FULL, 0 if ds["analysed_sst"].ndim == 3 else slice(None))
        ds.close()
        mm[d] = a.reshape(-1)[flat]
    mm.flush()
    return d0, d1, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tar")
    ap.add_argument("manifest")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--days", default=None, help="a:b day-index range (a test); default all")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(a.manifest)
    sea = data._full_sea_mask()
    flat = np.flatnonzero(sea.reshape(-1))            # C order over (lat, lon): lat-major, lon fastest within a row
    N, T = int(flat.size), grid.NDAYS
    lat, lon = np.divmod(flat, grid.NLON)
    np.stack([lat, lon], 1).astype(np.int32).tofile(out / "cells.i32")
    d0, d1 = (0, T) if a.days is None else map(int, a.days.split(":"))
    with open(out / "packed.f32", "ab") as f:
        f.truncate(T * N * 4)
    step = max(1, (d1 - d0 + a.workers * 4 - 1) // (a.workers * 4))
    jobs = [(a.tar, manifest, str(out), s, min(s + step, d1), T, N, flat) for s in range(d0, d1, step)]
    t0 = time.time()
    bad_all = []
    with mp.Pool(a.workers) as pool:
        for s, e, bad in pool.imap_unordered(work, jobs):
            bad_all += bad
            print(f"days {s}:{e} done, {time.time() - t0:.0f}s, hash mismatches so far {len(bad_all)}", flush=True)
    if bad_all:
        sys.exit(f"manifest sha256 mismatch: {bad_all[:5]} ...")
    rec = {"N": N, "T": T, "days": [d0, d1], "first_day": str(grid.day_date(0)), "last_day": str(grid.day_date(T - 1)),
           "mask_cells": N, "mask_sha256_of_cell_list": hashlib.sha256((out / "cells.i32").read_bytes()).hexdigest(),
           "source_tar": a.tar, "manifest": a.manifest, "manifest_sha256": sha256_file(a.manifest),
           "files_checked_against_manifest": d1 - d0, "seconds": round(time.time() - t0)}
    (out / "pack.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
