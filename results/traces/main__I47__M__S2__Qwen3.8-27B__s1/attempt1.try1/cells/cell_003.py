import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_mask = (ds["latitude"].values >= np.float32(64.39)) & (ds["latitude"].values <= np.float32(65.59))
lon_mask = (ds["longitude"].values >= np.float32(23.41)) & (ds["longitude"].values <= np.float32(24.61))
print("num lat:", lat_mask.sum(), "num lon:", lon_mask.sum())

# read one slice: mid-summer 2019
import pandas as pd
tidx = {np.datetime64(d): i for i, d in enumerate(ds["time"].values)}
i0 = tidx[np.datetime64("2019-07-15")]
sl = ds["analysed_sst"].isel(time=i0, latitude=np.where(lat_mask)[0], longitude=np.where(lon_mask)[0]).values
sl64 = sl.astype(np.float64)
print("2019-07-15 sample: min", np.nanmin(sl64), "max", np.nanmax(sl64), "nan count", np.isnan(sl64).sum(), "of", sl64.size)
print("a few values (K):", sl64.ravel()[:8], "-> C:", (sl64.ravel()[:8]-273.15))

# a winter slice
i1 = tidx[np.datetime64("2019-01-15")]
sl1 = ds["analysed_sst"].isel(time=i1, latitude=np.where(lat_mask)[0], longitude=np.where(lon_mask)[0]).values
sl1 = sl1.astype(np.float64)
print("2019-01-15: min", np.nanmin(sl1), "max", np.nanmax(sl1), "nan count", np.isnan(sl1).sum())
ds.close()
