import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
print(ds)
print("time range:", ds.time.values[0], "->", ds.time.values[-1], "n =", len(ds.time))