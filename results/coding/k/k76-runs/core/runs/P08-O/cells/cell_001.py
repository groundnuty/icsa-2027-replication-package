import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 54.81, 56.01
LON_MIN, LON_MAX = 19.61, 20.81
T_START = dt.date(2007, 6, 1)
T_END = dt.date(2007, 8, 31)
TOL = 1e-4

import glob
ROOT = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(glob.glob(ROOT + "/sst_*.nc"))
print(len(files), "files;", os.path.basename(files[0]), "to", os.path.basename(files[-1]))
p = f"{ROOT}/sst_{T_START:%Y%m%d}.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds["analysed_sst"].dims, ds["analysed_sst"].shape, ds["analysed_sst"].dtype)
print("lat", float(ds.latitude[0]), float(ds.latitude[-1]), "lon", float(ds.longitude[0]), float(ds.longitude[-1]))
a = ds["analysed_sst"].sel(latitude=slice(LAT_MIN - TOL, LAT_MAX + TOL), longitude=slice(LON_MIN - TOL, LON_MAX + TOL))
v = a.isel(time=0).values
print("region", v.shape, "finite", int(np.isfinite(v).sum()), "of", v.size)
print("min/max K", float(np.nanmin(v)), float(np.nanmax(v)))
print(v[:3, :4])
