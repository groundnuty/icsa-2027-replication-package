import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 57.33, 58.53
LON_MIN, LON_MAX = 9.03, 10.23
T_START = dt.date(2012, 6, 1)
T_END = dt.date(2012, 8, 31)
TOL = 1e-4

thr_t = np.load("thr_t.npy")
sst = np.load("target_s.npy")
nd, nc = sst.shape
hot = (sst >= thr_t).astype(np.int8)
print("days", nd, "cells", nc, "hot cell-days", int(hot.sum()))
mask_s = np.zeros((nd, nc), dtype=np.uint8)
for c in range(nc):
    e = np.diff(np.concatenate(([0], hot[:, c], [0])))
    starts = np.flatnonzero(e == 1)
    stops = np.flatnonzero(e == -1)
    long_run = (stops - starts) >= 5
    starts, stops = starts[long_run], stops[long_run]
    ms, mt = [], []
    for a, b in zip(starts, stops):
        if ms and a - mt[-1] <= 2:
            mt[-1] = b
        else:
            ms.append(a)
            mt.append(b)
    for a, b in zip(ms, mt):
        mask_s[a:b, c] = 1
print("in-MHW cell-days", int(mask_s.sum()))
np.save("mask_s.npy", mask_s)
