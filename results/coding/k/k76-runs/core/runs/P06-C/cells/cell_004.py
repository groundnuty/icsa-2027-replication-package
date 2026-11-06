import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 64.51, 65.71
LON_MIN, LON_MAX = 21.97, 23.17
T_START = dt.date(2019, 6, 1)
T_END = dt.date(2019, 8, 31)
TOL = 1e-4

def mhw_days(hot):
    n = len(hot)
    runs = []
    i = 0
    while i < n:
        if hot[i]:
            j = i
            while j + 1 < n and hot[j + 1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    out = [0] * n
    for a, b in merged:
        for k in range(a, b + 1):
            out[k] = 1
    return out

thr_t = np.load("thr_t.npy")
clim_t = np.load("clim_t.npy")
sst = np.load("target_s.npy")
anom = sst - clim_t
excess = anom - (thr_t - clim_t)
print("anomaly K mean", round(float(anom.mean()), 3), "max", round(float(anom.max()), 3))
hot = (excess >= 0).T.tolist()
ncell = len(hot)
cols = []
for c in range(ncell):
    cols.append(mhw_days(hot[c]))
mask_s = np.array(cols, dtype=np.uint8).T
print("hot cell-days", int((excess >= 0).sum()), "in-MHW cell-days", int(mask_s.sum()))
np.save("mask_s.npy", mask_s)
