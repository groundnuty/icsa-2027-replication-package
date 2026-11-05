"""Build S1 (15,340 daily files) and S2 (one time-chunked file) from the raw download.

    uv run python -m icsa.ingest.build s1 [--first YYYY-MM-DD --last YYYY-MM-DD --out DIR]
    uv run python -m icsa.ingest.build s2 [--out FILE]

S1 is written with xarray, S2 with netCDF4; icsa.ingest.verify reads both back
with h5py / netCDF4 and compares them with the raw files decoded independently.
Both builds are resumable (existing complete outputs are kept).
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import netCDF4
import numpy as np
import xarray as xr

from icsa import grid
from icsa.ingest import common as c
from icsa.paths import RAW, S1Z_DIR as S1_DIR, S2Z_FILE as S2_FILE

SST_ATTRS = {
    "long_name": "analysed sea surface temperature",
    "standard_name": "sea_surface_foundation_temperature",
    "units": "kelvin",
}
GLOBAL_ATTRS = {
    "Conventions": "CF-1.4",
    "title": "Baltic Sea/North Sea SST analysis, daily reprocessed level 4 analysis",
    "institution": "Danish Meteorological Institute, DMI",
    "source": "Copernicus Marine " + c.PRODUCT_ID + ", dataset " + c.DATASET_ID,
    "references": "doi:" + c.DOI,
    "comment": ("analysed_sst decoded from int16 scale/offset to float32; land and values outside "
                "the source valid range are NaN."),
    "license": c.ATTRIBUTION,
    "acknowledgment": c.ATTRIBUTION,
    "copernicus_marine_product_id": c.PRODUCT_ID,
    "copernicus_marine_dataset_id": c.DATASET_ID,
    "copernicus_marine_dataset_version": c.DATASET_VERSION,
    "copernicus_marine_download_date": c.DOWNLOAD_DATE,
}
TIME_ATTRS = {"long_name": "Time", "standard_name": "time", "axis": "T"}
TIME_UNIT_ATTRS = {"units": c.TIME_UNITS, "calendar": "proleptic_gregorian"}


def build_s1_day(d: dt.date, raw: np.ndarray, pk: c.Packing,
                 lat: np.ndarray, lon: np.ndarray, out: Path) -> None:
    sst = c.decode(raw, *pk)
    ds = xr.Dataset(
        {c.VAR: (("time", "latitude", "longitude"), sst[None], SST_ATTRS)},
        coords={
            "time": ("time", np.array([c.time_seconds(d)], dtype=np.int32),
                     {**TIME_ATTRS, **TIME_UNIT_ATTRS}),
            "latitude": ("latitude", lat, {"long_name": "latitude", "units": "degrees_north",
                                          "standard_name": "latitude", "axis": "Y"}),
            "longitude": ("longitude", lon, {"long_name": "longitude", "units": "degrees_east",
                                            "standard_name": "longitude", "axis": "X"}),
        },
        attrs=GLOBAL_ATTRS,
    )
    enc = {
        c.VAR: {"dtype": "float32", "_FillValue": np.float32("nan"), "zlib": True, "complevel": c.COMPLEVEL, "shuffle": False,
                "chunksizes": (1, grid.NLAT, grid.NLON), "fletcher32": False},
        "time": {"dtype": "int32", "_FillValue": None},
        "latitude": {"dtype": "float32", "_FillValue": None},
        "longitude": {"dtype": "float32", "_FillValue": None},
    }
    tmp = out.with_name(out.name + ".tmp")
    ds.to_netcdf(tmp, engine="netcdf4", format="NETCDF4", encoding=enc)
    tmp.replace(out)


def s1_complete(p: Path) -> bool:
    try:
        with netCDF4.Dataset(p) as ds:
            v = ds[c.VAR]
            v.set_auto_maskandscale(False)
            f = v.filters()
            return (v.shape == (1, grid.NLAT, grid.NLON) and v.dtype == np.float32
                    and f["zlib"] and f["complevel"] == c.COMPLEVEL and not f["shuffle"] and not f["fletcher32"]
                    and v.chunking() == [1, grid.NLAT, grid.NLON]
                    and not ({"scale_factor", "add_offset", "valid_min", "valid_max", "valid_range", "missing_value"} & set(v.ncattrs())))
    except Exception:
        return False


def build_s1(first=grid.DAY0, last=grid.LAST_DAY, out_dir: Path = S1_DIR, raw_dir: Path = RAW) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    lat, lon = c.read_coords(raw_dir)
    n = 0
    for d, raw, pk in c.iter_days(first, last, raw_dir):
        p = c.s1_path(d, out_dir)
        if p.exists() and s1_complete(p):
            continue
        build_s1_day(d, raw, pk, lat, lon, p)
        n += 1
        if n % 500 == 0:
            print(f"s1: {d} ({n} written)", flush=True)
    return n


def build_s2(out: Path = S2_FILE, raw_dir: Path = RAW, first=grid.DAY0, last=grid.LAST_DAY) -> None:
    """One NetCDF4 file, (time, lat, lon) chunked (1, NLAT, NLON), uncompressed.

    The time axis covers first..last; with the defaults, all 15,340 days.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    lat, lon = c.read_coords(raw_dir)
    ndays = (last - first).days + 1
    tmp = out.with_name(out.name + ".tmp")
    with netCDF4.Dataset(tmp, "w", format="NETCDF4") as ds:
        ds.setncatts(GLOBAL_ATTRS)
        ds.createDimension("time", ndays)
        ds.createDimension("latitude", grid.NLAT)
        ds.createDimension("longitude", grid.NLON)
        tv = ds.createVariable("time", "i4", ("time",))
        tv.setncatts({**TIME_ATTRS, **TIME_UNIT_ATTRS})
        la = ds.createVariable("latitude", "f4", ("latitude",))
        la.setncatts({"long_name": "latitude", "units": "degrees_north",
                      "standard_name": "latitude", "axis": "Y"})
        lo = ds.createVariable("longitude", "f4", ("longitude",))
        lo.setncatts({"long_name": "longitude", "units": "degrees_east",
                      "standard_name": "longitude", "axis": "X"})
        la[:], lo[:] = lat, lon
        v = ds.createVariable(c.VAR, "f4", ("time", "latitude", "longitude"),
                              chunksizes=(1, grid.NLAT, grid.NLON), zlib=True,
                              complevel=c.COMPLEVEL, shuffle=False, fletcher32=False,
                              fill_value=np.float32("nan"))
        v.setncatts(SST_ATTRS)
        k = 0
        for d, raw, pk in c.iter_days(first, last, raw_dir):
            tv[k] = c.time_seconds(d)
            v[k] = c.decode(raw, *pk)
            k += 1
            if k % 1000 == 0:
                print(f"s2: {d} ({k}/{ndays})", flush=True)
        if k != ndays:
            raise RuntimeError(f"wrote {k} days, expected {ndays}")
    tmp.replace(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["s1", "s2"])
    ap.add_argument("--first", type=dt.date.fromisoformat, default=grid.DAY0)
    ap.add_argument("--last", type=dt.date.fromisoformat, default=grid.LAST_DAY)
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    if a.which == "s1":
        n = build_s1(a.first, a.last, a.out or S1_DIR, a.raw)
        print(f"s1: {n} files written")
    else:
        build_s2(a.out or S2_FILE, a.raw, a.first, a.last)
        print("s2: done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
