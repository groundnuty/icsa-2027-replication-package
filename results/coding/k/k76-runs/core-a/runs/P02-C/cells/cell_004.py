import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
T_START = dt.date(2003, 6, 1)
T_END = dt.date(2003, 8, 31)
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

thr = np.load("thr_t.npy").tolist()
sst = np.load("target_s.npy").tolist()
ndays = len(thr)
ncell = len(thr[0])
print("days", ndays, "cells", ncell)
cols = []
nhot = 0
for c in range(ncell):
    hot = []
    for k in range(ndays):
        h = sst[k][c] >= thr[k][c]
        hot.append(h)
        nhot += h
    cols.append(mhw_days(hot))
    if c % 500 == 0:
        print("cell", c, "of", ncell)
mask_s = np.array(cols, dtype=np.uint8).T
print("hot cell-days", nhot, "in-MHW cell-days", int(mask_s.sum()))
np.save("mask_s.npy", mask_s)
