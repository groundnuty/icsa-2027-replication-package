"""Independent value checks for S1 and S2.

The builders read raw with netCDF4 and write S1 with xarray, S2 with netCDF4.
Here everything (raw, S1, S2) is read with h5py, and raw is decoded again from
first principles (float64, then float32). Nothing from icsa.ingest.build or
icsa.ingest.common is used.

    uv run python -m icsa.ingest.verify s1   # every S1 day against raw
    uv run python -m icsa.ingest.verify s2   # every S2 day against raw (S1 cross-check too, if the S1 directory exists)
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import h5py
import numpy as np

from icsa import grid
from icsa.paths import RAW, S1Z_DIR as S1_DIR, S2Z_FILE as S2_FILE

EPOCH = dt.datetime(1981, 1, 1)
ATTRIBUTION = ("Generated using E.U. Copernicus Marine Service Information; "
               "https://doi.org/10.48670/moi-00156")


def _same(a: np.ndarray, b: np.ndarray) -> bool:
    return (a.dtype == b.dtype == np.float32 and a.shape == b.shape
            and np.array_equal(a.view(np.uint32), b.view(np.uint32)))   # bitwise


BANNED_ATTRS = {"scale_factor", "add_offset", "valid_min", "valid_max", "valid_range", "missing_value"}


def _encoding_ok(v) -> bool:
    """float32, NaN fill, no packing / valid-range attrs, exactly one filter: deflate level 4, chunk (1, lat, lon)."""
    pl = v.id.get_create_plist()
    fill = v.attrs.get("_FillValue")
    return (v.dtype == np.float32 and not (BANNED_ATTRS & set(v.attrs))
            and fill is not None and np.shape(fill) in ((), (1,)) and np.ravel(fill).dtype == np.float32
            and bool(np.isnan(np.ravel(fill)[0]))
            and pl.get_nfilters() == 1 and pl.get_filter(0)[0] == 1 and tuple(pl.get_filter(0)[2])[:1] == (4,)
            and v.chunks == (1, grid.NLAT, grid.NLON))


def _attr(v, name):
    a = v.attrs[name]
    return a.decode() if isinstance(a, bytes) else str(a)


def _coords_ok(f, ref_lat, ref_lon) -> bool:
    return (all(not (BANNED_ATTRS & set(f[n].attrs)) for n in ("latitude", "longitude", "time"))
            and f["time"].dtype == np.int32 and _same(f["latitude"][:], ref_lat) and _same(f["longitude"][:], ref_lon)
            and _attr(f["time"], "units") == "seconds since 1981-01-01"
            and _attr(f["time"], "calendar") == "proleptic_gregorian"
            and _attr(f["latitude"], "units") == "degrees_north"
            and _attr(f["longitude"], "units") == "degrees_east"
            and _attr(f["analysed_sst"], "units") == "kelvin")


_INTERNAL_ATTRS = {"DIMENSION_LIST", "REFERENCE_LIST", "_Netcdf4Dimid", "_Netcdf4Coordinates", "CLASS", "NAME"}


def _norm(v):
    a = np.asarray(v)
    return (a.dtype.str, a.shape, a.tobytes())          # byte-exact, so NaN == NaN


def _var_attrs(f) -> dict:
    """User attributes of every dataset in the file (HDF5 / netCDF4 bookkeeping attributes excluded)."""
    return {name: {k: _norm(v) for k, v in ds.attrs.items() if k not in _INTERNAL_ATTRS}
            for name, ds in f.items() if isinstance(ds, h5py.Dataset)}


def _global_attrs(f) -> dict:
    return {k: _attr(f, k) for k in f.attrs}


def _days(first, last):
    d = first
    while d <= last:
        yield d
        d += dt.timedelta(days=1)


def verify_s1(raw_dir: Path = RAW, s1_dir: Path = S1_DIR, first=grid.DAY0, last=grid.LAST_DAY,
              expect_files: int | None = grid.NDAYS) -> dict:
    names = sorted(p.name for p in s1_dir.iterdir())
    want = [f"sst_{d:%Y%m%d}.nc" for d in _days(first, last)]
    if expect_files is not None and len(names) != expect_files:
        raise AssertionError(f"{len(names)} entries in {s1_dir}, expected {expect_files}")
    if names != want:
        raise AssertionError("S1 file names differ from the expected date sequence")
    n = bad = 0
    h5 = None
    cur_year = None
    ref_lat = ref_lon = ref_attrs = ref_vattrs = None
    for d in _days(first, last):
        if d.year != cur_year:
            if h5 is not None:
                h5.close()
            h5 = h5py.File(raw_dir / f"SST_BAL_{d.year}.nc", "r")
            cur_year = d.year
            v = h5["analysed_sst"]
            scale = float(np.ravel(v.attrs["scale_factor"])[0])
            offset = float(np.ravel(v.attrs["add_offset"])[0])
            fill = np.ravel(v.attrs["_FillValue"])[0]
            vmin = int(np.ravel(v.attrs["valid_min"])[0])
            vmax = int(np.ravel(v.attrs["valid_max"])[0])
            if ref_lat is None:
                ref_lat, ref_lon = h5["latitude"][:], h5["longitude"][:]
            assert _same(h5["latitude"][:], ref_lat) and _same(h5["longitude"][:], ref_lon), \
                f"raw {d.year} coordinates differ from the first year"
        k = (d - dt.date(d.year, 1, 1)).days
        raw = h5["analysed_sst"][k]
        exp = np.where((raw == fill) | (raw < vmin) | (raw > vmax), np.nan, raw.astype(np.float64) * scale + offset).astype(np.float32)
        assert int(h5["time"][k]) == int((dt.datetime(d.year, d.month, d.day) - EPOCH).total_seconds())
        with h5py.File(s1_dir / f"sst_{d:%Y%m%d}.nc", "r") as f1:
            v1 = f1["analysed_sst"]
            ok = (v1.dtype == np.float32 and v1.shape == (1, grid.NLAT, grid.NLON)
                  and _encoding_ok(v1)
                  and _same(v1[0], exp)
                  and f1["time"].shape == (1,)
                  and int(f1["time"][0]) == int((dt.datetime(d.year, d.month, d.day) - EPOCH).total_seconds())
                  and _coords_ok(f1, ref_lat, ref_lon))
            if ref_attrs is None:
                ref_attrs = _global_attrs(f1)
                assert ATTRIBUTION in ref_attrs.get("license", ""), ref_attrs
                assert ref_attrs.get("copernicus_marine_dataset_version") == "202506"
            ok = ok and _global_attrs(f1) == ref_attrs
            va = _var_attrs(f1)
            if ref_vattrs is None:
                ref_vattrs = va
            ok = ok and va == ref_vattrs
        n += 1
        if not ok:
            bad += 1
            print(f"MISMATCH {d}")
    if h5 is not None:
        h5.close()
    return {"days": n, "mismatches": bad}


def _raw_expected(raw_dir: Path, first, last):
    """Yield (date, expected float32 (lat, lon), raw time seconds, raw lat, raw lon) by decoding raw with h5py."""
    cur_year, h5, ref = None, None, None
    try:
        for d in _days(first, last):
            if d.year != cur_year:
                if h5 is not None:
                    h5.close()
                h5 = h5py.File(raw_dir / f"SST_BAL_{d.year}.nc", "r")
                cur_year = d.year
                v = h5["analysed_sst"]
                pk = (float(np.ravel(v.attrs["scale_factor"])[0]), float(np.ravel(v.attrs["add_offset"])[0]),
                      np.ravel(v.attrs["_FillValue"])[0], int(np.ravel(v.attrs["valid_min"])[0]),
                      int(np.ravel(v.attrs["valid_max"])[0]))
                if ref is None:
                    ref = (h5["latitude"][:], h5["longitude"][:])
                assert _same(h5["latitude"][:], ref[0]) and _same(h5["longitude"][:], ref[1]), \
                    f"raw {d.year} coordinates differ from the first year"
            scale, offset, fill, vmin, vmax = pk
            k = (d - dt.date(d.year, 1, 1)).days
            raw = h5["analysed_sst"][k]
            exp = np.where((raw == fill) | (raw < vmin) | (raw > vmax), np.nan,
                           raw.astype(np.float64) * scale + offset).astype(np.float32)
            yield d, exp, int(h5["time"][k]), ref[0], ref[1]
    finally:
        if h5 is not None:
            h5.close()


def verify_s2(raw_dir: Path = RAW, s2: Path = S2_FILE, first=grid.DAY0, last=grid.LAST_DAY,
              s1_dir: Path | None = None) -> dict:
    """Every S2 day bitwise equal to the raw files decoded independently (h5py).

    If s1_dir is given, also compares each day with S1 and the global attributes with S1's.
    """
    ndays = (last - first).days + 1
    n = bad = 0
    with h5py.File(s2, "r") as f:
        v = f["analysed_sst"]
        assert v.shape == (ndays, grid.NLAT, grid.NLON), v.shape
        assert v.dtype == np.float32
        assert _encoding_ok(v), "S2 encoding: need float32, NaN fill, no packing attrs, deflate 4 only, chunk (1, lat, lon)"
        t = f["time"][:]
        assert t.shape == (ndays,)
        a = f.attrs
        assert ATTRIBUTION in _attr_str(a, "license") and _attr_str(a, "copernicus_marine_dataset_version") == "202506"
        if s1_dir is not None:
            with h5py.File(s1_dir / f"sst_{first:%Y%m%d}.nc", "r") as f1:
                assert _global_attrs(f) == _global_attrs(f1), "S2 global attributes differ from S1"
                assert _var_attrs(f) == _var_attrs(f1), "S2 variable attributes differ from S1"
        coords_checked = False
        for k, (d, exp, tsec, rlat, rlon) in enumerate(_raw_expected(raw_dir, first, last)):
            if not coords_checked:
                assert _coords_ok(f, rlat, rlon), "S2 coordinates / units differ from the raw source"
                coords_checked = True
            ok = int(t[k]) == int((dt.datetime(d.year, d.month, d.day) - EPOCH).total_seconds()) == tsec
            row = v[k]
            ok = ok and _same(row, exp)
            if s1_dir is not None:
                with h5py.File(s1_dir / f"sst_{d:%Y%m%d}.nc", "r") as f1:
                    ok = ok and _same(row, f1["analysed_sst"][0])
            n += 1
            if not ok:
                bad += 1
                print(f"MISMATCH {d}")
    return {"days": n, "mismatches": bad}


def _attr_str(attrs, name) -> str:
    a = attrs[name]
    return a.decode() if isinstance(a, bytes) else str(a)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["s1", "s2"])
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--s1", type=Path, default=S1_DIR)
    ap.add_argument("--s2", type=Path, default=S2_FILE)
    ap.add_argument("--first", type=dt.date.fromisoformat, default=grid.DAY0)
    ap.add_argument("--last", type=dt.date.fromisoformat, default=grid.LAST_DAY)
    a = ap.parse_args(argv)
    full = (a.first, a.last) == (grid.DAY0, grid.LAST_DAY)
    if a.which == "s1":
        r = verify_s1(a.raw, a.s1, a.first, a.last, grid.NDAYS if full else None)
    else:
        r = verify_s2(a.raw, a.s2, a.first, a.last, s1_dir=a.s1 if a.s1.is_dir() else None)
    print(r)
    return 1 if r["mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
