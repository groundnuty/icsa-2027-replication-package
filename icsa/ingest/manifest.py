"""sha256 manifests (sha256sum -c format) and extent descriptions (JSON).

    uv run python -m icsa.ingest.manifest [--out data]

Writes data/manifest/s1_sha256.txt, s2_sha256.txt, totals.json and
data/extent_s1.json, data/extent_s2.json. The extent files carry no file-naming
pattern and no file list; they describe what the data is, not how it is stored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py
import numpy as np

from icsa import grid
from icsa.paths import S1Z_DIR as S1_DIR, S2Z_FILE as S2_FILE


def _all_days():
    return (grid.day_date(i) for i in range(grid.NDAYS))


def sha256_file(p: Path, bufsize: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(bufsize):
            h.update(b)
    return h.hexdigest()


def manifest_lines(files: list[Path], base: Path, workers: int = 8) -> tuple[list[str], int]:
    with ThreadPoolExecutor(workers) as ex:
        digests = list(ex.map(sha256_file, files))
    lines = [f"{d}  {p.relative_to(base).as_posix()}" for d, p in zip(digests, files)]
    return lines, sum(p.stat().st_size for p in files)


def extent(layout: str, s1_nfiles: int | None = None, chunks: tuple | None = None,
           file_s: Path | None = None) -> dict:
    """Extent description; reads lat/lon from the actual data file given by file_s."""
    with h5py.File(file_s, "r") as f:
        lat, lon = f["latitude"][:], f["longitude"][:]
    assert lat.shape == (grid.NLAT,) and lon.shape == (grid.NLON,)
    d = {
        "variable": "analysed_sst",
        "long_name": "analysed sea surface temperature",
        "units": "kelvin",
        "dtype": "float32",
        "missing_value": "NaN (land)",
        "time": {"start": grid.DAY0.isoformat(), "end": grid.LAST_DAY.isoformat(),
                 "step": "1 day", "count": grid.NDAYS},
        "grid": {
            "lon": {"min": float(round(float(lon[0]), 4)), "max": float(round(float(lon[-1]), 4)),
                    "count": grid.NLON},
            "lat": {"min": float(round(float(lat[0]), 4)), "max": float(round(float(lat[-1]), 4)),
                    "count": grid.NLAT},
            "resolution_deg": grid.RES_DEG,
            "shape_lat_lon": [grid.NLAT, grid.NLON],
        },
        "layout": layout,
        "out_of_range_values": {
            "rule": "source values outside the valid range [-300, 4500] (raw packed units, 0.01 K)are NaN",
            "cell_days": 122, "distinct_cells": 15, "days": 26,
            "period": ["1982-01-01", "1982-01-26"],
            "cell_days_in_finite_BALarea": 10, "distinct_cells_in_finite_BALarea": 1,
        },
        "attribution": "Generated using E.U. Copernicus Marine Service Information; "
                       "https://doi.org/10.48670/moi-00156",
        "source_dataset": {"id": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m", "version": "202506",
                           "download_date": "2026-10-31"},
    }
    if s1_nfiles is not None:
        d["number_of_files"] = s1_nfiles
        d["time_per_file"] = 1
    if chunks is not None:
        d["chunk_shape_time_lat_lon"] = list(chunks)
        d["compression"] = {"filter": "deflate", "level": 4, "shuffle": False}
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1", type=Path, default=S1_DIR)
    ap.add_argument("--s2", type=Path, default=S2_FILE)
    ap.add_argument("--out", type=Path, default=Path("data"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--allow-partial", action="store_true",
                    help="tests only: skip the full 15,340-day inventory check")
    a = ap.parse_args(argv)
    (a.out / "manifest").mkdir(parents=True, exist_ok=True)
    s1_files = sorted(a.s1.glob("*.nc"))
    if not a.allow_partial:
        want = [f"sst_{d:%Y%m%d}.nc" for d in _all_days()]
        if [p.name for p in s1_files] != want:
            raise SystemExit(f"S1 is not the complete {grid.NDAYS}-day sequence; refusing to write extents")
        with h5py.File(a.s2, "r") as f:
            if f["analysed_sst"].shape[0] != grid.NDAYS or f["time"].shape != (grid.NDAYS,):
                raise SystemExit("S2 time axis is not complete; refusing to write extents")
    l1, b1 = manifest_lines(s1_files, a.s1, a.workers)
    (a.out / "manifest" / "s1_sha256.txt").write_text("\n".join(l1) + "\n")
    l2, b2 = manifest_lines([a.s2], a.s2.parent, 1)
    (a.out / "manifest" / "s2_sha256.txt").write_text("\n".join(l2) + "\n")
    (a.out / "manifest" / "totals.json").write_text(json.dumps(
        {"s1": {"files": len(s1_files), "bytes": b1}, "s2": {"files": 1, "bytes": b2}}, indent=2) + "\n")
    (a.out / "extent_s1.json").write_text(json.dumps(
        extent("one NetCDF4 file per day, flat directory", s1_nfiles=len(s1_files),
               chunks=(1, grid.NLAT, grid.NLON), file_s=s1_files[0]),
        indent=2) + "\n")
    (a.out / "extent_s2.json").write_text(json.dumps(
        extent("single NetCDF4/HDF5 file, chunked in time", chunks=(1, grid.NLAT, grid.NLON), file_s=a.s2),
        indent=2) + "\n")
    rec_p = a.out / "upload_record.json"
    if rec_p.exists():       # keep the archive-location block when the extents are regenerated
        v = json.loads(rec_p.read_text())
        up = {"name": v["space_name"], "space_id": v["space_id"], "provider": v["provider"],
              "provider_id": v["provider_id"],
              "supported_only_by_provider": bool(v["verification"].get("supported_only_by_provider", False)),
              "files_uploaded": v["verification"]["files_expected"],
              "files_hash_matched_manifest": v["verification"]["files_matched"],
              "verified": bool(v["verification"]["ok"]) and v["verification"].get("manifest_sha256") == {
                  n: hashlib.sha256((a.out / "manifest" / f"{n}_sha256.txt").read_bytes()).hexdigest()
                  for n in ("s1", "s2")}}
        for n, k in (("s1", grid.NDAYS), ("s2", 1)):
            fp = a.out / f"extent_{n}.json"
            e = json.loads(fp.read_text())
            e["upload"] = {"archive_space": {**up, "files_in_layout": k}}
            fp.write_text(json.dumps(e, indent=2) + "\n")
    print(f"s1: {len(s1_files)} files, {b1} bytes; s2: {b2} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
