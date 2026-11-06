import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
T_START = dt.date(2003, 6, 1)
T_END = dt.date(2003, 8, 31)
TOL = 1e-4

P = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(P, engine="h5netcdf")
print(dict(ds.sizes))
print(ds["analysed_sst"].dtype, ds["analysed_sst"].attrs.get("units"))
print("time", str(ds.time.values[0])[:10], "to", str(ds.time.values[-1])[:10])
lat = ds.latitude.values; lon = ds.longitude.values
print("lat", lat[0], lat[-1], "lon", lon[0], lon[-1])
la = np.flatnonzero((lat >= LAT_MIN - TOL) & (lat <= LAT_MAX + TOL))
lo = np.flatnonzero((lon >= LON_MIN - TOL) & (lon <= LON_MAX + TOL))
print("region indices", la[0], la[-1], lo[0], lo[-1], "->", len(la), "x", len(lo))
k = (T_START - dt.date(1982, 1, 1)).days
v = ds["analysed_sst"].isel(time=k, latitude=slice(la[0], la[-1] + 1), longitude=slice(lo[0], lo[-1] + 1)).values
print("first target day", str(ds.time.values[k])[:10], "finite", int(np.isfinite(v).sum()), "of", v.size)
print("min/max K", float(np.nanmin(v)), float(np.nanmax(v)))
