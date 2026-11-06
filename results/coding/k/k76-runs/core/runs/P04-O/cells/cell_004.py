import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 57.33, 58.53
LON_MIN, LON_MAX = 9.03, 10.23
T_START = dt.date(2012, 6, 1)
T_END = dt.date(2012, 8, 31)
TOL = 1e-4

def vec_mhw(hot):
    n, m = hot.shape
    fwd = np.zeros((n, m), dtype=np.int32)
    bwd = np.zeros((n, m), dtype=np.int32)
    run = np.zeros(m, dtype=np.int32)
    for k in range(n):
        run = (run + 1) * hot[k]
        fwd[k] = run
    run = np.zeros(m, dtype=np.int32)
    for k in range(n - 1, -1, -1):
        run = (run + 1) * hot[k]
        bwd[k] = run
    inside = hot & ((fwd + bwd - 1) >= 5)
    joined = inside.copy()
    for g in (1, 2):
        for k in range(1, n - g):
            between = ~inside[k:k + g].any(axis=0)
            joined[k:k + g] |= (inside[k - 1] & inside[k + g] & between)
    return joined.astype(np.uint8)

thr_t = np.load("thr_t.npy")
sst = np.load("target_s.npy")
hot = sst >= thr_t
print("hot cell-days", int(hot.sum()), "of", hot.size)
mask_s = vec_mhw(hot)
print("in-MHW cell-days", int(mask_s.sum()))
np.save("mask_s.npy", mask_s)
