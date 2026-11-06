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

tgt = np.load("tgt_sst.npy")
tdates = np.load("tgt_dates.npy")
sea = np.isfinite(tgt).all(axis=0)
tdoys = np.array([doy(dt.date(int(v) // 10000, int(v) // 100 % 100, int(v) % 100)) for v in tdates])
nblk = 4
step = sea.shape[0] // nblk
thr_t = np.full(tgt.shape, np.nan)
for b in range(nblk):
    sst = np.load(f"blk{b}_sst.npy")
    bd = np.load(f"blk{b}_dates.npy")
    doys = np.array([doy(dt.date(int(v) // 10000, int(v) // 100 % 100, int(v) % 100)) for v in bd])
    sea_b = sea[b * step:(b + 1) * step]
    X = sst[:, sea_b]
    thr = smoothed_thresholds(X, doys, tdoys)
    part = np.full((len(tdoys),) + sea_b.shape, np.nan)
    part[:, sea_b] = thr
    thr_t[:, b * step:(b + 1) * step] = part
    print("block", b, "days", sst.shape[0], "cells", int(sea_b.sum()))
np.save("thr_t.npy", thr_t)
print("thresholds", thr_t.shape, "mean K", round(float(np.nanmean(thr_t)), 2))
