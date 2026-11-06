import os, json, datetime as dt
import numpy as np
import xarray as xr

ROOT = "/data/icsa2027_data_20261101T090944Z"
LAT0, LAT1 = 57.33, 58.53
LON0, LON1 = 9.03, 10.23
T0, T1 = dt.date(2012, 6, 1), dt.date(2012, 8, 31)

def doy(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

def region_slices(lat, lon):
    iy = np.where((lat >= LAT0 - 1e-4) & (lat <= LAT1 + 1e-4))[0]
    ix = np.where((lon >= LON0 - 1e-4) & (lon <= LON1 + 1e-4))[0]
    return slice(int(iy[0]), int(iy[-1]) + 1), slice(int(ix[0]), int(ix[-1]) + 1)

tgt = np.load("tgt_sst.npy")
sea = np.isfinite(tgt).all(axis=0)
ci, ck = [int(v) for v in np.array(np.nonzero(sea)).mean(axis=1)]
if not sea[ci, ck]:
    ci, ck = [int(v) for v in np.array(np.nonzero(sea))[:, 0]]
print("reference cell", ci, ck)

# quick reference: pooled 90th percentile for one day of year, plain Python pool vs numpy stack
target_doy = doy(dt.date(2012, 7, 15))
pool = []
stack = []
for y in range(1992, 2003):
    a = np.load(f"yr_{y}.npy")
    for n in range(a.shape[0]):
        d = dt.date(y, 5, 12) + dt.timedelta(days=n)
        if abs(doy(d) - target_doy) <= 5:
            pool.append(float(a[n, ci, ck]))
            stack.append(a[n, ci, ck])
pool.sort()
m = len(pool)
rank = 0.9 * m + 0.5
lo = int(np.floor(rank))
ref = pool[lo - 1] + (rank - lo) * (pool[lo] - pool[lo - 1])
fast = float(np.percentile(np.array(stack), 90, method="hazen"))
print("pool size", m, "reference", round(ref, 4), "numpy", round(fast, 4), "diff", abs(ref - fast))
