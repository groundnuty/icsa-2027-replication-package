"""A scripted 'agent' for the instrument validation (#9, pilot criteria ii and iii).

Not imported: `validate.py` copies this file into each run's work directory
and runs it there, so its frames count as agent code, as a real agent's
cells would. It reads its scenario from the SCEN_CFG environment variable
(JSON), reaches the data through the option's path, and computes a
simplified marine-heatwave mask. Each scenario parameter makes it skip or
misuse a known part of the data. The validation derives the expected extents
from the same parameters, never from the instrument.
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

cfg = json.loads(os.environ["SCEN_CFG"])
opt, layout, style = cfg["option"], cfg["layout"], cfg["style"]
# Where the data are and how they are named: the synthetic layout (s1/, YYYYMMDD-SST-L4.nc,
# s2/sst_s2.nc) or the real one (s1z/, sst_YYYYMMDD.nc, s2z/sst_s2.nc, #3).
S1_DIR = cfg.get("s1_dir", "s1")
S1_FMT = cfg.get("s1_fmt", "%Y%m%d-SST-L4.nc")
S2_REL = cfg.get("s2_rel", "s2/sst_s2.nc")
# How the data are reached: "sim" (local Range server for T, T-unpaginated and D, local files
# for M, M+) or "sandbox" (inside icsa.sandbox: the platform's fsspec client for T,
# T-unpaginated and D, the oneclient mount for M, M+; ICSA_DATASET_LOCATION is the S1
# directory or the S2 file). Everything after the access layer is the same code.
ACCESS = cfg.get("access", "sim")
root = Path(cfg.get("root", "/"))
out = Path(cfg["out"])
out.mkdir(parents=True, exist_ok=True)
DAY0 = dt.date(1982, 1, 1)


def day_of(d):
    return (d - DAY0).days


j0, j1, i0, i1 = cfg["read_box"]          # file-local lat/lon index ranges to read
use_j0, use_j1, use_i0, use_i1 = cfg["use_box"]

# ---- access path -------------------------------------------------------------
fs = None
LOC = os.environ.get("ICSA_DATASET_LOCATION", "")
if opt in ("T", "T-unpaginated", "D"):
    if ACCESS == "sandbox":
        import fsspec
        fs = fsspec.filesystem("onedata")           # preconfigured by the sandbox (#7)
    else:
        from icsa.instruments.sim.rangefs import RangeFS
        # The platform decides how fs.ls lists: the official client (T, D) or the shim (T-unpaginated).
        # The platform's client in every REST option: T-unpaginated differs at the gate, here
        # the local server (it answers with one whole listing), as on the real path.
        fs = RangeFS(cfg["url"], listing="client", page_limit=cfg["page_limit"],
                     block_size=cfg.get("block_size", 64 * 1024))
dl = Path(cfg["download_dir"]) if opt == "D" else None


def where(rel):
    """The path of a dataset file or of the S1 directory as this access path names it
    (rel: S1_DIR, S1_DIR/name or S2_REL). In a sandbox, ICSA_DATASET_LOCATION is the S1
    directory or the S2 file itself."""
    if ACCESS == "sandbox":
        if rel in (S2_REL, S1_DIR):
            return LOC
        return LOC.rstrip("/") + "/" + rel.rsplit("/", 1)[-1]
    if fs is not None:
        return rel
    return str(root / rel)


def list_endpoint(rel):
    """(url, headers) of the REST listing of a directory, as an agent's own code would call it."""
    if hasattr(fs, "list_url"):                    # the local client, or a test's stand-in
        return fs.list_url(where(rel) if ACCESS == "sandbox" else rel), {}
    space, path = fs._split_onedata_path(fs._strip_protocol(LOC))
    dir_id = fs._get_file_id(space, path)
    return (f"https://{cfg['provider_host']}/api/v3/oneprovider/data/{dir_id}/children",
            {"X-Auth-Token": os.environ["ONEDATA_TOKEN"]})


def own_paging(rel, max_pages=None):
    """The agent's own code pages through the REST listing (T, D), or a local listing (M)."""
    if fs is None:
        names = sorted(os.listdir(LOC if ACCESS == "sandbox" else root / rel))
        return names if max_pages is None else names[: max_pages * cfg["page_limit"]]
    import requests
    url, headers = list_endpoint(rel)
    names, token, n = [], None, 0
    while True:
        params = {"limit": cfg["page_limit"]} if token is None else {"limit": cfg["page_limit"], "token": token}
        page = requests.get(url, params=params, headers=headers).json()
        names += [e["name"] for e in page["children"]]
        n += 1
        if page["isLast"] or (max_pages is not None and n >= max_pages):
            return sorted(names)
        token = page["nextPageToken"]


# One page through a subprocess by urllib, which is not requests: the agent's listing the hook in requests cannot see, and the
# gate can. The child is started like any other, so it is traced like any other; one that skips that altogether makes the run unknown.
_SUBPROCESS_LISTING = """
import json, os, ssl, sys, urllib.request
url, headers = sys.argv[1], json.loads(sys.argv[2])
ca = "/etc/icsa/ca.pem"
ctx = ssl.create_default_context(cafile=ca) if os.path.exists(ca) else None
req = urllib.request.Request(url + "?limit=" + sys.argv[3], headers=headers)
print(json.dumps([e["name"] for e in json.load(urllib.request.urlopen(req, context=ctx))["children"]]))
"""


def subprocess_listing(rel):
    url, headers = list_endpoint(rel)
    r = subprocess.run([sys.executable, "-c", _SUBPROCESS_LISTING, url, json.dumps(headers),
                        str(cfg["page_limit"])], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return sorted(json.loads(r.stdout))


def list_dir(rel):
    mode = cfg["listing"]
    if mode == "ls":
        if fs is not None:
            names = sorted(str(e["name"]).rstrip("/").rsplit("/", 1)[-1] for e in fs.ls(where(rel) if ACCESS == "sandbox" else rel, detail=True))
        else:
            names = sorted(os.listdir(LOC if ACCESS == "sandbox" else root / rel))
    elif mode == "paged":
        names = own_paging(rel)
    elif mode == "paged_stop":
        names = own_paging(rel, max_pages=cfg["stop_after_pages"])
    elif mode == "subprocess":
        names = subprocess_listing(rel)
    else:
        raise ValueError(mode)
    # what the listing returned, compared across paths: the count and the names
    print(f"LISTED {len(names)} {hashlib.sha256(chr(10).join(names).encode()).hexdigest()}")
    return names


def constructed_names(days):
    """No listing: the file name of each wanted day, from the naming pattern."""
    return [(DAY0 + dt.timedelta(days=int(d))).strftime(S1_FMT) for d in days]


def local(rel):
    if opt == "D":
        p = dl / rel.rsplit("/", 1)[-1]
        if not p.exists():
            dl.mkdir(parents=True, exist_ok=True)
            if ACCESS == "sandbox":
                fs.get(where(rel), str(p))
            else:
                fs.get_file(rel, str(p))
        return str(p)
    return where(rel)


def nc_open(rel):
    """netCDF4 cannot open a file object: under T an agent passes the file's bytes."""
    import netCDF4
    if opt in ("T", "T-unpaginated"):
        return netCDF4.Dataset("remote.nc", memory=fs.cat_file(where(rel)))
    return netCDF4.Dataset(local(rel))


MASKED = cfg.get("masked", "")
LIST_IDIOM = cfg["method"] if cfg["method"].startswith("list_") else ""   # one array per day, in a list, never a cube


def keep(parts):
    """The masked days (netCDF4's default reads), kept the way the scenario says."""
    if MASKED == "filled":
        return np.stack([x.filled(np.nan) for x in parts])
    if MASKED == "getdata":
        return np.stack([np.ma.getdata(x) for x in parts])
    if MASKED == "stack":
        return np.stack(parts)
    if MASKED == "masked_sink":
        return np.ma.stack(parts)
    raise ValueError(MASKED)


SOURCE = cfg.get("source", "")


def h5_open(rel):
    import h5py
    import io
    remote = opt in ("T", "T-unpaginated")
    if SOURCE == "memory":                     # the whole file's bytes, decoded from memory
        if remote:
            return h5py.File(io.BytesIO(fs.cat_file(where(rel))), "r")
        with open(local(rel), "rb") as f:
            return h5py.File(io.BytesIO(f.read()), "r")
    if SOURCE == "fileobj" and not remote:     # a local file object
        return h5py.File(open(local(rel), "rb"), "r")
    if remote:
        return h5py.File(fs.open(where(rel), "rb"), "r")
    return h5py.File(local(rel), "r")


def xr_open(rel):
    import xarray as xr
    if opt in ("T", "T-unpaginated"):
        return xr.open_dataset(fs.open(where(rel), "rb"), engine="h5netcdf")
    return xr.open_dataset(local(rel), engine="h5netcdf" if style == "xarray" else "netcdf4")


def box(v, t=None):
    """The read box of a (time, y, x) DataArray, whatever its dimensions are named."""
    sel = {v.dims[1]: slice(j0, j1), v.dims[2]: slice(i0, i1)}
    if t is not None:
        sel[v.dims[0]] = t
    return v.isel(sel)


# ---- which days the script uses ---------------------------------------------
base_days = [d for d in cfg["baseline_days"] if d not in set(cfg["skip_days"])]
tgt_days = cfg["target_days"]
header_only = set(cfg["header_only_days"])
want = sorted(set(base_days) | set(tgt_days))

# ---- read ---------------------------------------------------------------------
if layout == "S1":
    names = constructed_names(want) if cfg["listing"] == "construct" else list_dir(S1_DIR)
    by_day = {}
    for n in names:
        m = re.search(r"(\d{8})", n)          # YYYYMMDD-SST-L4.nc (synthetic) or sst_YYYYMMDD.nc (real)
        if m:
            by_day[day_of(dt.datetime.strptime(m.group(1), "%Y%m%d").date())] = S1_DIR + "/" + n
    days = [d for d in want if d in by_day]
    for d in sorted(header_only & set(by_day)):          # opened, metadata only
        if style == "netCDF4":
            import netCDF4
            with netCDF4.Dataset(local(by_day[d])) as nc:
                _ = nc["analysed_sst"].shape, nc["time"][:]
        else:
            with h5_open(by_day[d]) as h:
                _ = h["analysed_sst"].shape, h["time"][()]
    days = [d for d in days if d not in header_only]
    if not days:
        # nothing wanted was found (a truncated listing that holds only early years):
        # an empty cube, so the run still writes its (empty) mask and report
        cube = np.empty((0, j1 - j0, i1 - i0), "f4")
    elif LIST_IDIOM:
        def load(d):
            if style == "netCDF4":
                with nc_open(by_day[d]) as nc:
                    return np.ma.filled(nc["analysed_sst"][0, j0:j1, i0:i1], np.nan)
            if style == "h5py":
                with h5_open(by_day[d]) as h:
                    return h["analysed_sst"][0, j0:j1, i0:i1]
            ds = xr_open(by_day[d])
            a = box(ds["analysed_sst"]).values[0]
            ds.close()
            return a
        parts = [load(d) for d in days]
    elif MASKED:
        parts = []
        for d in days:
            with nc_open(by_day[d]) as nc:
                parts.append(nc["analysed_sst"][0, j0:j1, i0:i1])   # a MaskedArray
        cube = keep(parts)
    elif style == "netCDF4":
        import netCDF4
        cube = np.empty((len(days), j1 - j0, i1 - i0), "f4")      # preallocate and fill
        for k, d in enumerate(days):
            with netCDF4.Dataset(local(by_day[d])) as nc:
                cube[k] = nc["analysed_sst"][0, j0:j1, i0:i1]
    elif style == "h5py":
        parts = []
        for d in days:
            with h5_open(by_day[d]) as h:
                parts.append(h["analysed_sst"][0, j0:j1, i0:i1])
        cube = np.stack(parts)
    else:
        parts = []
        for d in days:
            ds = xr_open(by_day[d])
            parts.append(box(ds["analysed_sst"]).values)
            ds.close()
        cube = np.concatenate(parts, axis=0)
else:
    rel = S2_REL
    if style == "h5py":
        h = h5_open(rel)
        t = h["time"][()]
        file_days = [day_of(dt.date(1981, 1, 1) + dt.timedelta(seconds=float(s))) for s in t]
        pos = {d: k for k, d in enumerate(file_days)}
        days = [d for d in want if d in pos and d not in header_only]
        if LIST_IDIOM:
            parts = [h["analysed_sst"][pos[d], j0:j1, i0:i1] for d in days]
        else:
            cube = h["analysed_sst"][[pos[d] for d in days], j0:j1, i0:i1]
    elif MASKED:
        nc = nc_open(rel)
        t = nc["time"][:]
        file_days = [day_of(dt.date(1981, 1, 1) + dt.timedelta(seconds=float(s))) for s in t]
        pos = {d: k for k, d in enumerate(file_days)}
        days = [d for d in want if d in pos and d not in header_only]
        cube = keep([nc["analysed_sst"][pos[d], j0:j1, i0:i1] for d in days])
    elif style == "netCDF4":
        import netCDF4
        nc = netCDF4.Dataset(local(rel))
        t = nc["time"][:]
        file_days = [day_of(dt.date(1981, 1, 1) + dt.timedelta(seconds=float(s))) for s in t]
        pos = {d: k for k, d in enumerate(file_days)}
        days = [d for d in want if d in pos and d not in header_only]
        if LIST_IDIOM:
            parts = [np.ma.filled(nc["analysed_sst"][pos[d], j0:j1, i0:i1], np.nan) for d in days]
        else:
            cube = np.empty((len(days), j1 - j0, i1 - i0), "f4")
            for k, d in enumerate(days):                                # one time step per read
                cube[k] = nc["analysed_sst"][pos[d], j0:j1, i0:i1]
    else:
        ds = xr_open(rel)
        file_days = [day_of(v.astype("datetime64[D]").astype(object)) for v in ds["time"].values]
        pos = {d: k for k, d in enumerate(file_days)}
        days = [d for d in want if d in pos and d not in header_only]
        if LIST_IDIOM:
            parts = [box(ds["analysed_sst"], [pos[d]]).values[0] for d in days]
        else:
            cube = box(ds["analysed_sst"], [pos[d] for d in days]).values

days = np.asarray(days)
if cfg.get("debug_print"):
    print("mean SST over everything read:", float(np.nanmean(cube)))

# ---- analyse ------------------------------------------------------------------
uj = slice(use_j0 - j0, use_j1 - j0)
ui = slice(use_i0 - i0, use_i1 - i0)
use_base = set(cfg["analysis_baseline_days"])
bsel = np.isin(days, sorted(use_base))
tsel = np.isin(days, tgt_days)
if not LIST_IDIOM:
    base = cube[bsel][:, uj, ui]
    tgt = cube[tsel][:, uj, ui]
if LIST_IDIOM:
    daily = [parts[k][uj, ui] for k in np.nonzero(bsel)[0]]        # the ordinary idioms: a list of days, then one call
    if LIST_IDIOM == "list_mean":
        thr = np.mean(daily, axis=0)
    elif LIST_IDIOM == "list_nanmean":
        thr = np.nanmean(daily, axis=0)
    elif LIST_IDIOM == "list_percentile":
        thr = np.nanpercentile(np.array(daily), 90, axis=0)
    elif LIST_IDIOM == "list_concatenate":
        thr = np.concatenate([x[None] for x in daily], axis=0).max(axis=0)
    elif LIST_IDIOM == "list_sum":
        thr = sum(daily) / len(daily)
    elif LIST_IDIOM == "list_accumulate":
        thr = np.zeros_like(daily[0])
        for x in daily:
            thr = thr + x
        thr = thr / len(daily)
    else:
        raise ValueError(LIST_IDIOM)
    mask = np.stack([(parts[k][uj, ui] > thr).astype("i1") for k in np.nonzero(tsel)[0]])
elif cfg["method"] == "doy_smoothed":
    # The seasonal climatology of the frozen method: +-5-day pooling per month/day position
    # (366 of them), then a circular 31-day mean of the raw thresholds.
    def position(d):
        x = DAY0 + dt.timedelta(days=int(d))
        return (dt.date(2000, x.month, x.day) - dt.date(2000, 1, 1)).days
    bpos = np.array([position(d) for d in days[bsel]])
    tpos = [position(d) for d in days[tsel]]
    raw = {}
    for e in sorted({(p + k) % 366 for p in tpos for k in range(-15, 16)}):
        win = np.minimum((bpos - e) % 366, (e - bpos) % 366) <= 5
        raw[e] = np.nanpercentile(base[win], 90, axis=0)
    thr = np.stack([np.nanmean(np.stack([raw[(p + k) % 366] for k in range(-15, 16)]), axis=0) for p in tpos])
    mask = (tgt > thr).astype("i1")
elif cfg["method"] == "xarray_window":
    import xarray as xr
    times = np.array([np.datetime64(DAY0 + dt.timedelta(days=int(d))) for d in days], "datetime64[ns]")
    da = xr.DataArray(cube[:, uj, ui], dims=("time", "lat", "lon"), coords={"time": times})
    clim = da.isel(time=np.nonzero(bsel)[0]).quantile(0.9, dim="time")
    mask = (da.isel(time=np.nonzero(tsel)[0]) > clim).astype("i1").values
elif cfg["method"] == "doy":
    doy = np.array([(DAY0 + dt.timedelta(days=int(d))).timetuple().tm_yday - 1 for d in days[bsel]])
    thr = np.full((366, base.shape[1], base.shape[2]), np.nan, "f4")
    for k in range(366):
        win = np.minimum((doy - k) % 366, (k - doy) % 366) <= 5
        if win.any():
            thr[k] = np.nanpercentile(base[win], 90, axis=0)
    tdoy = np.array([(DAY0 + dt.timedelta(days=int(d))).timetuple().tm_yday - 1 for d in days[tsel]])
    mask = (tgt > thr[tdoy]).astype("i1")
elif cfg["method"] == "xarray_groupby":
    import xarray as xr
    times = np.array([np.datetime64(DAY0 + dt.timedelta(days=int(d))) for d in days], "datetime64[ns]")
    da = xr.DataArray(cube[:, uj, ui], dims=("time", "lat", "lon"), coords={"time": times})
    clim = da.isel(time=np.nonzero(bsel)[0]).groupby("time.dayofyear").quantile(0.9, dim="time")
    tg = da.isel(time=np.nonzero(tsel)[0])
    mask = (tg.groupby("time.dayofyear") > clim).astype("i1").values
elif MASKED == "masked_sink":
    # masked arrays to the end: a masked mean (np.nanpercentile does not take np.ma.stack's
    # result, a numpy limitation), the masked comparison, the masked bool mask written as is
    thr = base.mean(axis=0)
    mask = (tgt > thr).astype("i1")
else:
    thr = np.nanpercentile(base, 90, axis=0)
    mask = np.asarray((tgt > thr).astype("i1"))

# ---- write outputs -------------------------------------------------------------
tdays = days[tsel]
lat = np.round(53.5 + 0.02 * (cfg["lat_origin"] + np.arange(use_j0, use_j1)), 6)
lon = np.round(9.0 + 0.02 * (cfg["lon_origin"] + np.arange(use_i0, use_i1)), 6)
secs = np.array([(dt.date(1982, 1, 1) + dt.timedelta(days=int(d)) - dt.date(1981, 1, 1)).total_seconds()
                 for d in tdays])
if cfg["writer"] == "netCDF4" or MASKED == "masked_sink":
    import netCDF4
    with netCDF4.Dataset(out / "mhw_mask.nc", "w") as nc:
        nc.createDimension("time", len(tdays))
        nc.createDimension("lat", len(lat))
        nc.createDimension("lon", len(lon))
        v = nc.createVariable("time", "f8", ("time",))
        v.units = "seconds since 1981-01-01 00:00:00"
        v.calendar = "gregorian"
        v[:] = secs
        nc.createVariable("lat", "f4", ("lat",))[:] = lat
        nc.createVariable("lon", "f4", ("lon",))[:] = lon
        # fill_value=0: masked elements (land) are stored as 0, a valid mask value
        nc.createVariable("mhw", "i1", ("time", "lat", "lon"),
                          fill_value=0 if MASKED == "masked_sink" else None)[:] = mask
else:
    import xarray as xr
    ds = xr.Dataset({"mhw": (("time", "lat", "lon"), mask)},
                    coords={"time": ("time", secs, {"units": "seconds since 1981-01-01 00:00:00",
                                                    "calendar": "gregorian"}),
                            "lat": lat.astype("f4"), "lon": lon.astype("f4")})
    ds.to_netcdf(out / "mhw_mask.nc", engine="h5netcdf")
active = np.ma.filled(mask, 0).any(axis=(1, 2))
events, start = [], None
for k, a in enumerate(active.tolist() + [False]):
    if a and start is None:
        start = k
    if not a and start is not None:
        if k - start >= 5:
            events.append([int(tdays[start]), int(tdays[k - 1])])
        start = None
(out / "report.json").write_text(json.dumps({"events": events, "complete": True, "caveats": []}))
