import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 54.81, 56.01
LON0, LON1 = 19.61, 20.81
T0, T1 = dt.date(2007, 6, 1), dt.date(2007, 8, 31)

def doy(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

def region_slices(lat, lon):
    iy = np.where((lat >= LAT0 - 1e-4) & (lat <= LAT1 + 1e-4))[0]
    ix = np.where((lon >= LON0 - 1e-4) & (lon <= LON1 + 1e-4))[0]
    return slice(int(iy[0]), int(iy[-1]) + 1), slice(int(ix[0]), int(ix[-1]) + 1)

def mhw_days(h, min_run=5, max_gap=2):
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]:
                j += 1
            if j - i >= min_run:
                runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= max_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    out = [0] * n
    for a, b in merged:
        for k in range(a, b):
            out[k] = 1
    return out

tgt = np.load("tgt_sst.npy")
thr_t = np.load("thr_t.npy")
sea = np.isfinite(tgt).all(axis=0)
hot = tgt >= thr_t
mask = np.zeros(tgt.shape, np.uint8)
n_done = 0
for i in range(tgt.shape[1]):
    for k in range(tgt.shape[2]):
        if not sea[i, k]:
            continue
        h = [bool(v >= t) for v, t in zip(tgt[:, i, k].tolist(), thr_t[:, i, k].tolist())]
        mask[:, i, k] = mhw_days(h)
        n_done += 1
print("cells processed", n_done)

os.makedirs("output", exist_ok=True)
tdates_i = np.load("tgt_dates.npy")
tcoord = np.array([np.datetime64(f"{str(v)[:4]}-{str(v)[4:6]}-{str(v)[6:]}") for v in tdates_i])
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mask.astype(np.uint8))},
    coords={"time": tcoord, "latitude": np.load("lat.npy"), "longitude": np.load("lon.npy")},
)
ds_out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")

active = mask.any(axis=(1, 2)).astype(int)
n_events = int(active[0]) + int(((active[1:] == 1) & (active[:-1] == 0)).sum())
report = {
    "region": {"lat": [LAT0, LAT1], "lon": [LON0, LON1]},
    "baseline_analysed": "1992-2002, 12 May-20 Sep of each year",
    "target_analysed": f"{T0} to {T1}",
    "events": n_events,
    "complete": True,
    "caveats": "none",
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("mask", mask.shape, "flagged cell-days", int(mask.sum()), "regional events", n_events)
print("wrote output/mhw_mask.nc and output/report.json")
