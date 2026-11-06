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

import glob
files = sorted(glob.glob(f"{ROOT}/s1z/sst_*.nc"))
print(len(files), "files;", os.path.basename(files[0]), "...", os.path.basename(files[-1]))
ds = xr.open_dataset(files[0], engine="h5netcdf")
print(dict(ds.sizes), list(ds.data_vars))
lat = ds["latitude"].values
lon = ds["longitude"].values
print("lat", lat.min(), lat.max(), "step", round(float(lat[1] - lat[0]), 4))
print("lon", lon.min(), lon.max(), "step", round(float(lon[1] - lon[0]), 4))
ys, xs = region_slices(lat, lon)
print("region rows", ys, "cols", xs)
a = ds["analysed_sst"].isel(time=0, latitude=ys, longitude=xs).values
print("region shape", a.shape, "dtype", a.dtype)
print("finite cells", int(np.isfinite(a).sum()), "of", a.size)
print("min/max/mean K", float(np.nanmin(a)), float(np.nanmax(a)), float(np.nanmean(a)))
print(a[:3, :5])
d = T0
with xr.open_dataset(f"{ROOT}/s1z/sst_{d:%Y%m%d}.nc", engine="h5netcdf") as dd:
    b = dd["analysed_sst"].isel(time=0, latitude=ys, longitude=xs).values
print("target first day", d, "finite", int(np.isfinite(b).sum()), "mean", round(float(np.nanmean(b)), 2))
