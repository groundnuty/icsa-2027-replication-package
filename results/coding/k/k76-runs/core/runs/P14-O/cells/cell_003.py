import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 64.51, 65.71
LON0, LON1 = 21.97, 23.17
T0, T1 = dt.date(2019, 6, 1), dt.date(2019, 8, 31)

def doy(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

def region_slices(lat, lon):
    iy = np.where((lat >= LAT0 - 1e-4) & (lat <= LAT1 + 1e-4))[0]
    ix = np.where((lon >= LON0 - 1e-4) & (lon <= LON1 + 1e-4))[0]
    return slice(int(iy[0]), int(iy[-1]) + 1), slice(int(ix[0]), int(ix[-1]) + 1)

def smoothed_thresholds(X, doys, tdoys):
    # X: (days, cells); doys: day-of-year of each row
    raw = np.full((366, X.shape[1]), np.nan)
    for d in range(int(tdoys.min()) - 15, int(tdoys.max()) + 16):
        sel = np.abs(doys - d) <= 5
        if sel.any():
            raw[d - 1] = np.nanpercentile(X[sel], 90, axis=0, method="hazen")
    out = np.full((len(tdoys), X.shape[1]), np.nan)
    for n, t in enumerate(tdoys):
        idx = [(int(t) - 1 + k) % 366 for k in range(-15, 16)]
        out[n] = np.nanmean(raw[idx], axis=0)
    return out

sst = np.load("base_sst.npy")
bdates = np.load("base_dates.npy")
tgt = np.load("tgt_sst.npy")
tdates = np.load("tgt_dates.npy")
sea = np.isfinite(tgt).all(axis=0)
yrs = np.array([int(v) // 10000 for v in bdates])
doys = np.array([doy(dt.date(int(v) // 10000, int(v) // 100 % 100, int(v) % 100)) for v in bdates])
tdoys = np.array([doy(dt.date(int(v) // 10000, int(v) // 100 % 100, int(v) % 100)) for v in tdates])
X = sst[:, sea]
print("baseline days", len(bdates), "sea cells", X.shape[1])

# range check per cell over the whole baseline
bad_counts = []
for j in range(X.shape[1]):
    col = X[:, j]
    bad_counts.append(int(((col < 260.0) | (col > 310.0)).sum()))
bad_counts = np.array(bad_counts)
print("cells with values outside 260-310 K:", int((bad_counts > 0).sum()), "max per cell", int(bad_counts.max()))
print("baseline range K", round(float(X.min()), 2), round(float(X.max()), 2))

use = yrs <= 1997   # first six years are enough for the percentile
print("days used for thresholds", int(use.sum()))
thr = smoothed_thresholds(X[use], doys[use], tdoys)
thr_t = np.full(tgt.shape, np.nan)
thr_t[:, sea] = thr
np.save("thr_t.npy", thr_t)
print("thresholds", thr_t.shape, "mean K", round(float(np.nanmean(thr)), 2))
