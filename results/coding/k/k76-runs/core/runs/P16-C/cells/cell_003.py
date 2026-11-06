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

sst = np.load("base_sst.npy")
bdates = np.load("base_dates.npy")
tgt = np.load("tgt_sst.npy")
sea = np.isfinite(tgt).all(axis=0)
yrs = np.array([int(v) // 10000 for v in bdates])
for y in range(1992, 2003):
    a = sst[yrs == y][:, sea]
    print(y, "days", a.shape[0], "mean K", round(float(a.mean()), 3), "max K", round(float(a.max()), 2))
print("overall mean K", round(float(sst[:, sea].mean()), 3))
