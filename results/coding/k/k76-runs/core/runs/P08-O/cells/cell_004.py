import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 54.81, 56.01
LON_MIN, LON_MAX = 19.61, 20.81
T_START = dt.date(2007, 6, 1)
T_END = dt.date(2007, 8, 31)
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
sst = np.load("target_s.npy")
hot = (sst >= thr_t).T.tolist()
print("cells", len(hot), "days", len(hot[0]))
cols = [mhw_days(h) for h in hot]
mask_s = np.array(cols, dtype=np.uint8).T
print("in-MHW cell-days", int(mask_s.sum()))
np.save("mask_s.npy", mask_s)
