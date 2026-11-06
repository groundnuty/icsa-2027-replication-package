import xarray as xr, numpy as np, os
path = '/work/data/sst_s2.nc'
ds = xr.open_dataset(path, engine="h5netcdf")
print("opened, time len:", len(ds.time))
arr = ds['analysed_sst']
print("arr dtype:", arr.dtype, "shape:", arr.shape, "chunks:", arr.chunks, "encoding:", arr.encoding)
import sys; sys.stdout.flush()