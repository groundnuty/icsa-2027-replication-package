import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 60.09, 61.29
LON0, LON1 = 20.01, 21.21
T0, T1 = dt.date(2003, 6, 1), dt.date(2003, 8, 31)

def doy(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

def region_slices(lat, lon):
    iy = np.where((lat >= LAT0 - 1e-4) & (lat <= LAT1 + 1e-4))[0]
    ix = np.where((lon >= LON0 - 1e-4) & (lon <= LON1 + 1e-4))[0]
    return slice(int(iy[0]), int(iy[-1]) + 1), slice(int(ix[0]), int(ix[-1]) + 1)

def mhw_array(hot, min_run=5):
    T = hot.shape[0]
    fwd = np.zeros(hot.shape, np.int16)
    bwd = np.zeros(hot.shape, np.int16)
    for t in range(T):
        prev = fwd[t - 1] if t else 0
        fwd[t] = (prev + 1) * hot[t]
    for t in range(T - 1, -1, -1):
        nxt = bwd[t + 1] if t < T - 1 else 0
        bwd[t] = (nxt + 1) * hot[t]
    ev = hot & ((fwd + bwd - 1) >= min_run)
    pad = np.zeros((2,) + ev.shape[1:], bool)
    e = np.concatenate([pad, ev, pad])
    p1, n1, p2, n2 = e[1:T + 1], e[3:T + 3], e[0:T], e[4:T + 4]
    gap = (p1 & n1) | (p1 & n2) | (p2 & n1)
    return (ev | gap).astype(np.uint8)

tgt = np.load("tgt_sst.npy")
thr_t = np.load("thr_t.npy")
sea = np.isfinite(tgt).all(axis=0)
hot = tgt >= thr_t
mask = mhw_array(hot) * sea[None]

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
    "baseline_analysed": "1992-2002, 12 May-20 Sep of each year except 1997-07-15",
    "target_analysed": f"{T0} to {T1}",
    "events": n_events,
    "complete": True,
    "caveats": "one baseline day dropped after a quick look",
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("mask", mask.shape, "flagged cell-days", int(mask.sum()), "regional events", n_events)
print("wrote output/mhw_mask.nc and output/report.json")
