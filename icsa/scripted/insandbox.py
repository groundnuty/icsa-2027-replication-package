"""The scripted reference pipeline, as it runs INSIDE the sandbox (#12).

One script for every option. The only option-dependent part is `open_path`: how a named file is opened
(T, T-unpaginated: remote fsspec file; D: `fs.get` to local disk, then the local copy; M, M+: the mount).
Files are chosen by name from the instance's required days, never from a listing: under T and D a listing
returns the first 1,000 entries, which hold no required day, and using it would measure that truncation
instead of the data path. The listing is a separate step that only records its entry count.

`icsa.refdet` (#4) runs here, on the arrays this script read, in computed mode (`computed_fields`, `sea_cells`,
`detect`), never through `refdet.ground_truth` or the field cache, which read local data on the host.
The source is shipped into the sandbox by `icsa.scripted.bundle`, so nothing is re-implemented.

stdlib + the image's pinned packages only. The host prepends `SPEC = {...}` and calls `main(SPEC)`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import time

RESULT_PREFIX = "ICSA_SCRIPTED_RESULT "
DAY0 = dt.date(1982, 1, 1)    # checked against icsa.grid.DAY0 by a test on the host
ACCESS = {"T": "rest-range", "T-unpaginated": "rest-range", "D": "rest-download", "M": "mount", "M+": "mount"}


def day_date(day: int) -> dt.date:
    return DAY0 + dt.timedelta(days=int(day))


def s1_name(day: int) -> str:
    return f"sst_{day_date(day):%Y%m%d}.nc"


def canonical_sha256(a) -> str:
    """Hash of a float32 array with every NaN in one bit pattern (the fill may differ between files)."""
    import numpy as np
    b = np.array(a, dtype="<f4", copy=True)
    b[np.isnan(b)] = np.nan
    return hashlib.sha256(b.tobytes()).hexdigest()


class HttpTrace:
    """Client-side time of every HTTP request (WAN anchor only: main runs carry no extra instrumentation)."""

    def __init__(self):
        self.records: list[list] = []

    def install(self) -> None:
        import requests
        orig, recs = requests.Session.send, self.records

        def send(session, request, **kw):
            t0 = time.perf_counter()
            r = orig(session, request, **kw)
            # r.elapsed = time to the response headers; total includes the body unless the caller streams
            recs.append([request.method, r.status_code, round(r.elapsed.total_seconds(), 6),
                         round(time.perf_counter() - t0, 6), bool(request.headers.get("Range")), bool(kw.get("stream"))])
            return r

        requests.Session.send = send


class Paths:
    """How a named file of the dataset is opened; everything option-specific is in this class."""

    def __init__(self, access: str, layout: str, location: str, scratch: str):
        self.access, self.layout, self.location, self.scratch = access, layout, location.rstrip("/"), scratch
        self.fs = None
        if access.startswith("rest"):
            import fsspec
            self.fs = fsspec.filesystem("onedata")   # {FS_EXPR} of the access texts: configured by the environment

    def listing_dir(self) -> str:
        return self.location if self.layout == "S1" else self.location.rsplit("/", 1)[0]

    def listing(self) -> int:
        d = self.listing_dir()
        return len(self.fs.ls(d, detail=False)) if self.fs is not None else len(os.listdir(d))

    def remote(self, name: str | None) -> str:
        return self.location if name is None else f"{self.location}/{name}"

    def open_path(self, name: str | None):
        """(dataset, file object to close afterwards or None); name None = the layout's one file (S2)."""
        import xarray
        remote = self.remote(name)
        if self.access == "rest-range":
            f = self.fs.open(remote, "rb")
            return xarray.open_dataset(f, engine="h5netcdf"), f
        if self.access == "rest-download":
            local = os.path.join(self.scratch, os.path.basename(remote))
            self.fs.get(remote, local)
            return xarray.open_dataset(local, engine="h5netcdf"), None
        if self.access == "mount":
            return xarray.open_dataset(remote, engine="h5netcdf"), None
        raise ValueError(f"unknown access {self.access!r}")

    def access_type_xattr(self, name: str | None) -> str | None:
        """oneclient's chosen I/O mode (M, M+); None for the REST paths or when the attribute is absent."""
        if self.access != "mount":
            return None
        try:
            return os.getxattr(self.remote(name), "org.onedata.access_type").decode(errors="replace")
        except OSError:
            return None


def check_coords(ds, spec: dict) -> dict:
    """The index slice must be the instance's box: centres inside the bounds, the next cell out on each side.
    Bounds lie midway between cell centres (#5), so this is exact. Returns the coordinate values of the box."""
    import numpy as np
    out = {}
    for var, lo, hi, a, b, n in (("latitude", spec["lat_min"], spec["lat_max"], spec["lat0"], spec["lat1"], 626),
                                 ("longitude", spec["lon_min"], spec["lon_max"], spec["lon0"], spec["lon1"], 1051)):
        full = np.asarray(ds[var].values, dtype=np.float64)
        if full.size != n:
            raise ValueError(f"{var} has {full.size} values, expected {n}")
        c = full[a:b]
        if not ((c >= lo).all() and (c <= hi).all()):
            raise ValueError(f"{var}[{a}:{b}] is outside [{lo}, {hi}]")
        if (a > 0 and lo <= full[a - 1] <= hi) or (b < n and lo <= full[b] <= hi):
            raise ValueError(f"{var}: the slice [{a}:{b}] misses a cell inside [{lo}, {hi}]")
        out[var] = c
    return out



def _use_package(pkg) -> None:
    """Make the unpacked sources importable. In a traced run the tracer's boot has already imported its own `icsa`, which holds only `instruments`
    (icsa.instruments.sandbox_dir), so `sys.path` alone is not enough: Python looks in that package's `__path__`, and every traced run would die here
    with `cannot import name 'refdet'`. The tracer's modules stay as they are."""
    if not pkg:
        return
    sys.path.insert(0, pkg)
    loaded = sys.modules.get("icsa")
    if loaded is not None and hasattr(loaded, "__path__"):
        loaded.__path__.insert(0, os.path.join(pkg, "icsa"))


def main(spec: dict, stream=None) -> dict:
    t0 = time.time()
    stamps: dict[str, float] = {}

    def mark(k: str) -> None:
        stamps[k] = round(time.time() - t0, 4)

    trace = None
    if spec.get("trace_http"):
        trace = HttpTrace()
        trace.install()

    import numpy as np

    _use_package(spec.get("package_dir"))
    from icsa import refdet
    from icsa.extent import CellBox
    mark("imports")

    layout, access = spec["layout"], ACCESS[spec["option"]]
    location = spec.get("location") or os.environ["ICSA_DATASET_LOCATION"]
    workdir = spec.get("workdir", ".")
    scratch = os.path.join(workdir, "data")
    os.makedirs(scratch, exist_ok=True)
    paths = Paths(access, layout, location, scratch)
    mark("client_ready")

    listing_entries = paths.listing()
    mark("listing_done")

    box = CellBox(spec["lat0"], spec["lat1"], spec["lon0"], spec["lon1"])
    base_days = np.asarray(spec["base_days"], np.int64)
    target_days = np.asarray(spec["target_days"], np.int64)
    days = np.concatenate([base_days, target_days])
    if np.any(np.diff(days) <= 0):
        raise ValueError("required days must be strictly increasing, baseline before target")
    read_days = spec.get("read_days")      # a live probe's prefix (liveprobe.py): the first n days of the cell's fixed order, read and timed as for the whole cell, nothing computed
    if read_days is not None:
        read_days = np.asarray(read_days, np.int64)
        if not 0 < read_days.size <= days.size or not np.array_equal(read_days, days[:read_days.size]):
            raise ValueError("read_days must be a non-empty prefix of the required days, in their order")
        days = read_days
    sst = np.empty((days.size, *box.shape), np.float32)
    per_day: list[float] = []
    coords = None
    first_compute = None
    time_errors = 0
    box_slices = dict(latitude=slice(box.lat0, box.lat1), longitude=slice(box.lon0, box.lon1))

    def take(ds, t_index: int, day: int, k: int) -> None:
        nonlocal coords, first_compute, time_errors
        if coords is None:
            coords = check_coords(ds, spec)
        v = ds["analysed_sst"].isel(time=t_index, **box_slices)
        when = np.datetime64(ds["time"].values[t_index], "D")
        if when != np.datetime64(day_date(day)):
            time_errors += 1
        sst[k] = np.asarray(v.values, np.float32)
        if first_compute is None:
            first_compute = int(np.isfinite(sst[k]).sum())
            mark("first_compute")

    cpu_read0 = sum(os.times()[:2])
    if layout == "S1":
        for k, d in enumerate(days):
            t1 = time.perf_counter()
            ds, f = paths.open_path(s1_name(d))
            take(ds, 0, int(d), k)
            ds.close()
            if f is not None:
                f.close()
            per_day.append(round(time.perf_counter() - t1, 5))
    elif layout == "S2":
        ds, f = paths.open_path(None)
        mark("opened")
        for k, d in enumerate(days):
            t1 = time.perf_counter()
            take(ds, int(d), int(d), k)
            per_day.append(round(time.perf_counter() - t1, 5))
        ds.close()
        if f is not None:
            f.close()
    else:
        raise ValueError(f"unknown layout {layout!r}")
    mark("read_done")
    cpu_read = sum(os.times()[:2]) - cpu_read0
    if time_errors:
        raise ValueError(f"{time_errors} of {days.size} days carry a different date in the time coordinate")

    if read_days is not None:             # a prefix read is not a run: no detection, no outputs, nothing for the comparison to score
        result = {"ok": True, "read_only": True, "instance_id": spec["instance_id"], "option": spec["option"], "layout": layout, "access": access,
                  "location": location, "listing_entries": listing_entries, "listing_dir": paths.listing_dir(), "stamps_s": stamps,
                  "first_compute_s": stamps["first_compute"], "first_compute_finite_cells": first_compute, "days_read": int(days.size),
                  "cpu_s": {"read": round(cpu_read, 3)}, "per_day_s": per_day, "sst_sha256": canonical_sha256(sst), "numpy": np.__version__}
        print(RESULT_PREFIX + json.dumps(result), file=stream or sys.stdout, flush=True)
        return result

    cpu_compute0 = sum(os.times()[:2])
    nb = base_days.size
    sst_b, sst_t = sst[:nb], sst[nb:]
    fields = refdet.computed_fields(sst_b, base_days, box)
    sea = refdet.sea_cells(sst_b, sst_t)
    det = refdet.detect(sst_t, target_days, box, fields, sea)
    mark("compute_done")
    cpu_compute = sum(os.times()[:2]) - cpu_compute0

    out_dir = os.path.join(workdir, "output")
    os.makedirs(out_dir, exist_ok=True)
    write_outputs(out_dir, spec, det, target_days, coords)
    mark("output_written")

    result = {
        "ok": True, "instance_id": spec["instance_id"], "option": spec["option"], "layout": layout, "access": access,
        "location": location, "listing_entries": listing_entries, "listing_dir": paths.listing_dir(),
        "stamps_s": stamps, "pipeline_s": stamps["output_written"], "first_compute_s": stamps["first_compute"],
        "first_compute_finite_cells": first_compute, "days_read": int(days.size),
        "cpu_s": {"read": round(cpu_read, 3), "compute": round(cpu_compute, 3)},   # user + sys of this process, per phase
        "per_day_s": per_day, "sea_cells": int(sea.sum()),
        "sst_sha256": canonical_sha256(sst), "mask_cell_days": int(det.cell_mask.sum()),
        "events": [[day_date(e.onset).isoformat(), day_date(e.end).isoformat()] for e in det.events],
        "active_mask": "".join("1" if x else "0" for x in det.active),
        "access_type": paths.access_type_xattr(s1_name(int(days[0])) if layout == "S1" else None),
        "numpy": np.__version__,
    }
    if trace is not None:
        result["http_trace"] = trace.records   # [method, status, seconds to headers, seconds in send, ranged, streamed]
    print(RESULT_PREFIX + json.dumps(result), file=stream or sys.stdout, flush=True)
    return result


def write_outputs(out_dir: str, spec: dict, det, target_days, coords) -> None:
    """The two files the prompt requires, as an agent would write them."""
    import netCDF4
    import numpy as np
    with netCDF4.Dataset(os.path.join(out_dir, "mhw_mask.nc"), "w") as nc:
        nc.createDimension("time", target_days.size)
        nc.createDimension("lat", det.cell_mask.shape[1])
        nc.createDimension("lon", det.cell_mask.shape[2])
        t = nc.createVariable("time", "i4", ("time",))
        t.units = f"days since {DAY0.isoformat()}"
        t[:] = target_days
        nc.createVariable("lat", "f8", ("lat",))[:] = coords["latitude"]
        nc.createVariable("lon", "f8", ("lon",))[:] = coords["longitude"]
        nc.createVariable("mhw", "u1", ("time", "lat", "lon"), zlib=True)[:] = det.cell_mask.astype(np.uint8)
    base, tgt = spec["base_days"], spec["target_days"]
    report = {
        "region": {k: spec[k] for k in ("lat_min", "lat_max", "lon_min", "lon_max")},
        "baseline_analysed": {"start": day_date(base[0]).isoformat(), "end": day_date(base[-1]).isoformat()},
        "target_analysed": {"start": day_date(tgt[0]).isoformat(), "end": day_date(tgt[-1]).isoformat()},
        "events": [{"onset": day_date(e.onset).isoformat(), "end": day_date(e.end).isoformat()} for e in det.events],
        "complete": True,
        "caveats": "",
    }
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=1)
