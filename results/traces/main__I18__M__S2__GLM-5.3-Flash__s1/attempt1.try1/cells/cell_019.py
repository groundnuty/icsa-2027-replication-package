import os, json, warnings
import numpy as np
import h5py

print("cwd:", os.getcwd())
os.makedirs("output", exist_ok=True)

PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
EPOCH = np.datetime64("1970-01-01")

with h5py.File(PATH, "r") as f:
    times = EPOCH + f["time"][:].astype("timedelta64[s]")
    lat = f["latitude"][:].astype(np.float32)
    lon = f["longitude"][:].astype(np.float32)
    i0b = np.searchsorted(times, np.datetime64("1991-12-27"))
    i1b = np.searchsorted(times, np.datetime64("2003-01-05"), side="right")
    i0t = np.searchsorted(times, np.datetime64("2010-06-01"))
    i1t = np.searchsorted(times, np.datetime64("2010-08-31"), side="right")
    base = f["analysed_sst"][i0b:i1b, :, :][:, 180:240, 690:750].astype(np.float64)
    tgt  = f["analysed_sst"][i0t:i1t, :, :][:, 180:240, 690:750].astype(np.float64)

print("base", base.shape, "tgt", tgt.shape)
assert np.array_equal(base, np.load("/tmp/base.npy"))
assert np.array_equal(tgt, np.load("/tmp/tgt.npy"))
print("re-extraction matches intermediates exactly")

def doy366(dates):
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    doy_std = (dates - (years - 1970).astype("datetime64[Y]")).astype(int) + 1
    leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
    return np.where(leap | (doy_std < 60), doy_std, doy_std + 1)

bdates = EPOCH + np.arange(int((np.datetime64("1991-12-27") - EPOCH) / np.timedelta64(1, "D")),
                           int((np.datetime64("2003-01-05") - EPOCH) / np.timedelta64(1, "D")) + 1)
tdates = EPOCH + np.arange(int((np.datetime64("2010-06-01") - EPOCH) / np.timedelta64(1, "D")),
                           int((np.datetime64("2010-08-31") - EPOCH) / np.timedelta64(1, "D")) + 1)
assert len(bdates) == base.shape[0] and len(tdates) == tgt.shape[0]
doy_b = doy366(bdates)
doy_t = doy366(tdates)

baseline_mask = (bdates >= np.datetime64("1992-01-01")) & (bdates <= np.datetime64("2002-12-31"))
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
import time as tm
t0 = tm.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        members = bdates[baseline_mask & (doy_b == d)]
        assert len(members) == 11
        pool_days = set()
        for m in members:
            mnum = int((m - EPOCH) / np.timedelta64(1, "D"))
            pool_days.update(range(mnum - 5, mnum + 6))
        sel = np.array(sorted(pool_days)) - int((bdates[0] - EPOCH) / np.timedelta64(1, "D"))
        pool = base[sel]
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pool loop:", round(tm.time()-t0, 1), "s")
thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])
print("thr_raw matches:", np.allclose(thr_raw, np.load("/tmp/thr_raw.npy"), equal_nan=True))
print("clim_raw matches:", np.allclose(clim_raw, np.load("/tmp/clim_raw.npy"), equal_nan=True))

def circ_moving_mean(arr, window=31):
    half = window // 2
    idx = np.array([(np.arange(366) - off) % 366 for off in range(-half, half + 1)])
    acc = np.zeros_like(arr)
    for k in range(window):
        acc += arr[idx[k]]
    return acc / window

thr = circ_moving_mean(thr_raw)
clim = circ_moving_mean(clim_raw)
print("thr matches:", np.allclose(thr, np.load("/tmp/thr.npy"), equal_nan=True))
print("clim matches:", np.allclose(clim, np.load("/tmp/clim.npy"), equal_nan=True))
# spot checks
assert abs(thr[149, 30, 30] - thr_raw[134:165, 30, 30].mean()) < 1e-9
assert abs(thr[0, 30, 30] - np.concatenate([thr_raw[351:366, 30, 30], thr_raw[0:16, 30, 30]]).mean()) < 1e-9
assert abs(clim[199, 30, 30] - clim_raw[184:215, 30, 30].mean()) < 1e-9

sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", sea.sum(), "land:", (~sea).sum())
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    hot = tgt >= thr[doy_t - 1]
np.save("/tmp/hot_finalcheck.npy", hot)

T = hot.shape[0]
hot_cells = hot.reshape(T, -1)[:, sea.reshape(-1)]
nsea = hot_cells.shape[1]

def detect_A(seq):
    """runs of >=5 hot days are MHWs; then MHWs separated by 1-2 non-hot days join; gaps belong."""
    seq = list(seq); L = len(seq)
    runs = []; t = 0
    while t < L:
        if seq[t]:
            u = t
            while u + 1 < L and seq[u+1]: u += 1
            runs.append([t, u]); t = u + 1
        else:
            t += 1
    mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    merged = []
    for r in mhw_runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    out = np.zeros(L, bool)
    for s, e in merged: out[s:e+1] = True
    return out, merged

mhw_cells = np.zeros((T, nsea), bool)
n_events_cells = 0
for n in range(nsea):
    a, merged = detect_A(hot_cells[:, n])
    mhw_cells[:, n] = a
    n_events_cells += len(merged)
active = mhw_cells.any(axis=1)
print("per-cell MHW events (all cells):", n_events_cells)
print("mhw sea-cell-days:", mhw_cells.sum())
print("active days:", active.sum(), "of", T)
print("active:", "".join("1" if x else "0" for x in active))

# events
idx = np.flatnonzero(active)
tstr = tdates.astype(str)
evs = []
s = idx[0]; prev = idx[0]
for i in idx[1:]:
    if i != prev + 1:
        evs.append((s, prev)); s = i
    prev = i
evs.append((s, prev))
events = [{"onset": str(tstr[a]), "end": str(tstr[b])} for a, b in evs]
print("events:", json.dumps(events))

np.save("/tmp/mhw_cells_out.npy", mhw_cells)
np.save("/tmp/sea_out.npy", sea)

# ---- build full-region mask (92, 60, 60), land = 0 ----
mhw_full = np.zeros((T, 60, 60), np.uint8)
mhw_full.reshape(T, -1)[:, sea.reshape(-1)] = mhw_cells.astype(np.uint8)

import xarray as xr
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_full)},
    coords={"time": tdates, "lat": lat[180:240], "lon": lon[690:750]},
)
ds_out["mhw"].encoding = {"dtype": "uint8", "_FillValue": None}
ds_out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.13, "lat_max": 58.33, "lon_min": 22.79, "lon_max": 23.99},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("All 4018 baseline days (1992-01-01..2002-12-31) were used; per the +/-5-day pool windows the "
                "climatology/threshold additionally read 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. "
                "The climatology was computed as specified but is not needed for the MHW mask. 299 of 3600 region "
                "cells are land (SST NaN on every day) and are 0 in the mask; the 3301 sea cells had finite SST on "
                "every target day. Source SST is stored as float32 (0.01 K quantization); all statistics were "
                "computed in float64. Hot-day test: stored kelvin SST >= smoothed threshold. Per-cell joining "
                "follows the spec sentence order: runs of >=5 consecutive hot days are MHWs first, then MHWs "
                "separated by 1-2 non-hot days are joined (gap days included). The regional active days, and hence "
                "the reported event, are identical under the alternative join order (join hot runs first, keep "
                "those >=5 days)."),
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")
